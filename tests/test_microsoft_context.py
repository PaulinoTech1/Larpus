import unittest
from unittest.mock import patch
from runtime import inference
from runtime.context import CAPACITY
from runtime.agents import load_personas,messages_for
from runtime.skills import load_skills

class MicrosoftContextTests(unittest.TestCase):
    def test_microsoft_skills_are_shared_only_by_approved_roles(self):
        personas=load_personas();skills=load_skills()
        identifiers={s for s in skills if s.startswith('ms-')}
        self.assertEqual(len(identifiers),5)
        history=[{'role':'user','content':'Explain a pilot.'},{'role':'assistant','content':'Use a lab cohort.'},{'role':'user','content':'Continue that plan.'}]
        for identifier in identifiers:
            for role in ('system-administrator','it-larp-coach'):
                prepared=messages_for(personas[role],history,identifier)
                self.assertEqual(prepared[1:],history)
                self.assertIn(skills[identifier]['text'],prepared[0]['content'])
            with self.assertRaises(ValueError):messages_for(personas['home-assistant'],history,identifier)

    def test_context_counts_are_measured_bounded_and_prompt_free(self):
        usage=inference.context_usage({'prompt_eval_count':1200,'eval_count':140},2)
        self.assertEqual(usage,{'capacity':CAPACITY,'prompt_tokens':1200,'output_tokens':140,'output_limit':1024,'omitted_messages':2,'measurement':'ollama-final'})
        for frame in ({},{'prompt_eval_count':True,'eval_count':1},{'prompt_eval_count':CAPACITY+1,'eval_count':1},{'prompt_eval_count':1,'eval_count':-1}):
            self.assertIsNone(inference.context_usage(frame))

    def test_both_inference_paths_attach_counts_after_dlp(self):
        frame={'message':{'content':'A useful reply.'},'done':True,'prompt_eval_count':700,'eval_count':12}
        with patch.object(inference,'augment',side_effect=lambda p,r:(p,[])),patch.object(inference,'gpu_placement',return_value='GPU'),patch.object(inference,'gate',side_effect=lambda t,p:{'status':200,'content':t}),patch.object(inference,'ollama',return_value=frame),patch.object(inference,'chat_stream',return_value=iter([frame])):
            for callback in (None,lambda t:None):
                result=inference.chat('home-assistant',[{'role':'user','content':'Hello'}],on_chunk=callback)
                self.assertEqual(result['context']['prompt_tokens'],700)
                self.assertEqual(result['context']['output_tokens'],12)

    def test_personality_keeps_helpfulness_and_role_boundaries(self):
        for persona in load_personas().values():
            self.assertIn('Challenge flawed assumptions',persona['system_prompt'])
            self.assertIn('never the person',persona['system_prompt'])
            self.assertIn('useful answer comes first',persona['system_prompt'])

class MicrosoftSourceTests(unittest.TestCase):
    def test_exact_microsoft_urls_only_and_query_exception_is_narrow(self):
        import importlib.util
        from pathlib import Path
        spec=importlib.util.spec_from_file_location('microsoft_prep',Path(__file__).resolve().parents[1]/'scripts/prepare-knowledge.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(len(module.MICROSOFT_DOCUMENTS),11)
        for url in module.MICROSOFT_DOCUMENTS:self.assertEqual(module.vetted_url(url),url)
        for url in ('https://learn.microsoft.com/en-us/unknown','https://learn.microsoft.com/en-us/intune/fundamentals/planning-guide?extra=1','http://learn.microsoft.com/en-us/intune/fundamentals/planning-guide'):
            with self.assertRaises(ValueError):module.vetted_url(url)

    def test_scan_requires_exact_registered_targets(self):
        import importlib.util
        from pathlib import Path
        spec=importlib.util.spec_from_file_location('microsoft_release',Path(__file__).resolve().parents[1]/'scripts/releases.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        targets=list(load_skills())+['mcp']
        summary={'status':'pass','results':[{'target':t,'complete':True,'status':'pass'} for t in targets]}
        module.scan_gate(summary,{'issues':[]},{'issues':[]},targets)
        for change in ('missing','duplicate','wrong'):
            altered=[dict(r) for r in summary['results']]
            if change=='missing':altered.pop()
            elif change=='duplicate':altered[-1]=dict(altered[0])
            else:altered[-1]['target']='unexpected'
            with self.assertRaises(ValueError):module.scan_gate({'status':'pass','results':altered},{'issues':[]},{'issues':[]},targets)
