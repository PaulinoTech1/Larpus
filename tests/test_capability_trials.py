import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from runtime import capability_trials as trials
from runtime.agents import load_personas

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('capability_cli', ROOT/'scripts/capability-trials.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class CapabilityTrialTests(unittest.TestCase):
    def setUp(self):
        self.bank = trials.bank(trials.read(ROOT/'evals/capability-linear-algebra.json'), load_personas())
        self.plan = trials.prepare(self.bank, {}, 'v0', 'method:worked-example')
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'trial.json'
        trials.save(self.path, self.plan)

    def test_preparation_is_deferred_and_pinned(self):
        self.assertEqual(self.plan['state'], 'deferred')
        self.assertEqual(self.plan['results'], [])
        self.assertIsNone(self.plan['environment'])
        trials.validate(self.plan)
        changed = copy.deepcopy(self.plan); changed['bank']['cases'][0]['prompt'] = 'Different question'
        with self.assertRaises(ValueError): trials.validate(changed)
        with self.assertRaises(ValueError): trials.prepare(self.bank, {}, 'v0', 'v0')
        self.assertEqual(trials.compare(self.plan)['splits']['held-out']['scored_pairs'], 0)

    def test_bank_and_profile_reject_invalid_inputs(self):
        for mutate in (lambda b:b['cases'].clear(), lambda b:b['cases'][0].update(split='training'),
                       lambda b:b['cases'][0]['rubric'].pop('correctness'),
                       lambda b:b['cases'][0].update(id=b['cases'][1]['id'])):
            b=copy.deepcopy(self.bank); mutate(b)
            with self.assertRaises(ValueError): trials.bank(b, load_personas())
        for selector in ('v-1','v1','trial:3','method:invented'):
            with self.assertRaises(ValueError): trials.profile({}, 'mathematician|', selector)
        exported={'version':1,'profiles':[{'scope':'mathematician|','versions':[{'settings':self.plan['profiles']['candidate']}]}], 'experiments':[]}
        self.assertEqual(trials.profile(exported,'mathematician|','v1')['method'],'worked-example')

    def test_no_inference_without_both_attestations_or_when_busy(self):
        with patch('runtime.mcp_client.chat') as chat, patch.object(cli,'note_gate',side_effect=ValueError('busy')):
            for flags in ((False,False),(True,False),(False,True),(True,True)):
                with self.assertRaises(ValueError): cli.execute(self.path,*flags)
            chat.assert_not_called()
        self.assertEqual(trials.read(self.path)['state'],'deferred')

    def test_worker_probe_refuses_night_busy_and_unknown(self):
        for value in ({'night':True,'busy':False},{'night':False,'busy':True},{'night':False},{}):
            response=type('Result',(),{'stdout':json.dumps(value)})()
            with patch.object(cli.os,'name','nt'), patch.object(cli.subprocess,'run',return_value=response):
                with self.assertRaises(ValueError): cli.note_gate()
        response=type('Result',(),{'stdout':'{"night":false,"busy":false}'})()
        with patch.object(cli.os,'name','nt'),patch.object(cli.subprocess,'run',return_value=response):cli.note_gate()

    def test_runner_resume_pins_and_no_rubric_leak(self):
        calls=[]; env={'release':'test','pins':{'notes':'same'}}
        def chat(persona,messages,skill):
            payload=json.loads(messages[0]['content'][len(trials.PREFIX):]);calls.append(payload)
            self.assertEqual(set(payload),{'question','profile','mode'})
            self.assertEqual(persona,'mathematician');self.assertIsNone(skill)
            return {'status':200,'content':'Model answer','sources':[]}
        # Stop before the third response. The first pair is atomically retained.
        gates=[None,None,None,ValueError('Notes resumed')]
        with patch.object(cli,'environment',return_value=env),patch.object(cli,'note_gate',side_effect=gates),patch('runtime.mcp_client.chat',side_effect=chat):
            with self.assertRaises(ValueError):cli.execute(self.path,True,True)
        saved=trials.read(self.path);self.assertEqual(len(saved['results']),2)
        self.assertEqual(saved['state'],'running')
        with patch.object(cli,'environment',return_value={'release':'different'}),patch.object(cli,'note_gate'),patch('runtime.mcp_client.chat') as model:
            with self.assertRaises(ValueError):cli.execute(self.path,True,True)
            model.assert_not_called()
        with patch.object(cli,'environment',return_value=env),patch.object(cli,'note_gate'),patch('runtime.mcp_client.chat',side_effect=chat):
            result=cli.execute(self.path,True,True)
        self.assertEqual(result['state'],'complete');self.assertEqual(len(calls),16)
        self.assertEqual([r['arm'] for r in result['results'][:4]],['baseline','candidate','candidate','baseline'])
        self.assertTrue(all('rubric' not in c and 'reference' not in c for c in calls))

    def test_manual_scoring_pairing_and_failures(self):
        ident=self.bank['cases'][0]['id']
        for arm,n in [('baseline',1),('candidate',2)]:
            self.plan['results'].append({'case':ident,'arm':arm,'status':200,'answer':'Answer','sources':[],'seconds':1,
              'review':{'scores':dict.fromkeys(('correctness','reasoning','teaching','grounding'),n),'reviewer':'owner','note':'Checked steps','at':trials.now()}})
        summary=trials.compare(self.plan)
        self.assertEqual(summary['splits']['practice']['scored_pairs'],1)
        self.assertEqual(summary['splits']['practice']['mean_candidate_minus_baseline']['correctness'],1)
        self.assertIsNone(summary['splits']['held-out']['mean_candidate_minus_baseline'])
        self.plan['results'][1]['status']=422
        with self.assertRaises(ValueError):trials.validate(self.plan)
        self.plan['results'][1]['review']=None
        self.assertEqual(trials.compare(self.plan)['splits']['practice']['failed_or_held_responses'],1)
        self.assertEqual(trials.compare(self.plan)['splits']['practice']['scored_pairs'],0)
        self.plan['results'][0]['review']['scores']['teaching']=True
        with self.assertRaises(ValueError):trials.validate(self.plan)

    def test_authored_arithmetic(self):
        def mul(a,b):return [[sum(x*y for x,y in zip(row,col)) for col in zip(*b)] for row in a]
        a=[[1,1],[0,1]]; b=[[1,0],[1,1]]
        self.assertEqual(mul(a,b),[[2,1],[1,1]]);self.assertEqual(mul(b,a),[[1,1],[1,2]])
        a=[[1,2,0,1],[0,0,1,3]]
        for v in ((-2,1,0,0),(-1,0,-3,1)):
            self.assertEqual([sum(x*y for x,y in zip(row,v)) for row in a],[0,0])
        self.assertEqual(tuple(x+y for x,y in zip((1,0,1),(0,1,1))),(1,1,2))
        # The Jordan example has only one independent eigenvector.
        self.assertEqual(mul([[2,1],[0,2]],[[1],[0]]),[[2],[0]])

    def test_invalid_complete_duplicate_and_unscored(self):
        self.plan['state']='complete'
        with self.assertRaises(ValueError):trials.validate(self.plan)
        self.plan['state']='running'
        row={'case':self.bank['cases'][0]['id'],'arm':'baseline','status':200,'answer':'A','sources':[],'seconds':1,'review':None}
        self.plan['results']=[row,row]
        with self.assertRaises(ValueError):trials.validate(self.plan)
