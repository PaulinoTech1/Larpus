import importlib
from io import BytesIO
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock,patch


class PerformanceSuiteTests(unittest.TestCase):
    def module(self,name):
        try:return importlib.import_module('scripts.'+name)
        except ImportError:self.fail('Performance suite module is missing: '+name)

    def test_failure_and_warmup_accounting_never_fills_missing_with_zero(self):
        metrics=self.module('performance_metrics')
        rows=[{'case':'a','phase':'warmup','ok':True,'first_text_seconds':100,'total_seconds':110,'stage_ms':{}},
              {'case':'a','phase':'measured','ok':True,'first_text_seconds':2,'total_seconds':4,'stage_ms':{'retrieval':5}},
              {'case':'a','phase':'measured','ok':False,'first_text_seconds':None,'total_seconds':3,'stage_ms':{},'error':'stream_rejected'},
              {'case':'a','phase':'measured','ok':True,'first_text_seconds':4,'total_seconds':6,'stage_ms':{}}]
        result=metrics.summarize(rows)
        self.assertEqual(result['attempted'],3);self.assertEqual(result['succeeded'],2)
        self.assertAlmostEqual(result['success_rate'],2/3)
        self.assertEqual(result['first_text_seconds']['median'],3)
        self.assertEqual(result['first_text_seconds']['p90'],4)
        self.assertEqual(result['stages_ms']['retrieval']['n'],1)
        self.assertEqual(result['stages_ms']['preflight_validation']['n'],0)
        self.assertIsNone(result['stages_ms']['preflight_validation']['median'])
        self.assertEqual(result['first_after_idle_seconds']['n'],0)
        self.assertIsNone(result['first_after_idle_seconds']['median'])
        self.assertEqual(result['failures'],{'stream_rejected':1})

    def test_transport_rejects_truncation_but_keeps_partial_observation(self):
        transport=self.module('performance_transport')
        opener=Mock();opener.open.return_value=BytesIO(b'{"type":"text","content":"Partial sentence."}\n')
        result,answer=transport.probe(opener,{'persona':'home-assistant','messages':[{'role':'user','content':'Hello'}]})
        self.assertFalse(result['ok']);self.assertEqual(result['error'],'missing_done')
        self.assertEqual(result['characters'],17);self.assertIsNotNone(result['first_text_seconds'])
        self.assertIsNone(answer)

    def test_transport_counts_rejected_stream_as_failure_and_does_not_save_partial_text(self):
        transport=self.module('performance_transport')
        opener=Mock();opener.open.return_value=BytesIO(b'{"type":"text","content":"Partial"}\n{"type":"error","error":"private detail","error_id":"0123456789abcdef"}\n')
        result,answer=transport.probe(opener,{'persona':'home-assistant','messages':[{'role':'user','content':'Hello'}]})
        self.assertFalse(result['ok']);self.assertEqual(result['error'],'stream_rejected')
        self.assertNotIn('private detail',json.dumps(result));self.assertIsNone(answer)

    def test_schedule_is_repeatable_and_rounds_cover_all_cases(self):
        suite=self.module('performance_suite');cases=[{'id':'a'},{'id':'b'},{'id':'c'}]
        plan=suite.schedule(cases,3,1,5900)
        self.assertEqual(plan,suite.schedule(cases,3,1,5900))
        self.assertEqual(len(plan),12)
        for repeat in range(1,4):self.assertEqual({c['id'] for phase,r,c in plan if phase=='measured' and r==repeat},{'a','b','c'})

    def test_comparison_rejects_changed_workload_and_within_run_model_drift(self):
        metrics=self.module('performance_metrics')
        base={'valid':True,'protocol':{'suite_sha256':'a'},'per_case':{'a':{'first_text_seconds':{'median':2},'success_rate':1}}}
        changed={**base,'protocol':{'suite_sha256':'b'}}
        self.assertFalse(metrics.compare(base,changed)['comparable'])
        self.assertFalse(metrics.compare(base,{**base,'valid':False})['comparable'])
        result=metrics.compare(base,{**base,'per_case':{'a':{'first_text_seconds':{'median':1},'success_rate':1}}})
        self.assertTrue(result['comparable']);self.assertEqual(result['cases']['a']['median_change_percent'],-50)

    def test_incomplete_run_is_invalid_even_with_unchanged_station(self):
        suite=self.module('performance_suite')
        report={'id':'test','before':{'model':'same'},'protocol':{'case_ids':['a'],'repeats':3,'warmups':1}}
        with tempfile.TemporaryDirectory() as d,patch.object(suite.station,'snapshot',return_value={'model':'same'}):
            suite.finish(report,[],[],{},Path(d),Mock())
            self.assertFalse(report['valid'],'An empty/incomplete run must not be a valid comparison')

    def test_success_retains_answer_only_on_explicit_request_and_filters_stages(self):
        transport=self.module('performance_transport');opener=Mock()
        frames=[{'type':'text','content':'An answer.'},{'type':'done','sources':[],'timing_ms':{'retrieval':12,'input':True,'secret':'private'}}]
        def response():return BytesIO(b''.join((json.dumps(e)+'\n').encode() for e in frames))
        opener.open.side_effect=[response(),response()];case={'persona':'home-assistant','messages':[{'role':'user','content':'Hello'}]}
        row,answer=transport.probe(opener,case)
        self.assertTrue(row['ok']);self.assertIsNone(answer);self.assertEqual(row['stage_ms'],{'retrieval':12})
        row,answer=transport.probe(opener,case,retain=True)
        self.assertEqual(answer['answer'],'An answer.');self.assertNotIn('An answer',json.dumps(row))

    def test_run_writes_comparable_numeric_reports_and_separate_private_answers(self):
        suite=self.module('performance_suite');case={'id':'a','persona':'home-assistant','messages':[{'role':'user','content':'Hello'}]}
        observation={'ok':True,'first_text_seconds':2,'total_seconds':3,'characters':12,'stage_ms':{}}
        with tempfile.TemporaryDirectory() as d,patch.object(suite,'STORE',Path(d)),patch.object(suite,'catalog',return_value=({'cases':[case],'rubric':{'accuracy':'0-2'}},'hash')),patch.object(suite.station,'snapshot',return_value={'model':'same'}),patch.object(suite.station,'host_environment',return_value={}),patch.object(suite,'probe',side_effect=lambda *args:(dict(observation),{'answer':'Private fixed test answer','sources':[]})):
            report=suite.run(repeats=1,warmups=1,retain=True)
            directory=Path(d)/report['id'];self.assertTrue(report['valid'])
            self.assertEqual(report['summary']['attempted'],1);self.assertEqual(report['warmup']['attempted'],1)
            for filename in ('report.json','summary.md','observations.jsonl'):
                self.assertNotIn('Private fixed test answer',(directory/filename).read_text())
            self.assertIn('Private fixed test answer',(directory/'answers.jsonl').read_text())
            self.assertEqual(len(json.loads((directory/'review.json').read_text())['items']),1)

    def test_interrupted_request_stays_in_denominator(self):
        suite=self.module('performance_suite');cases=[{'id':str(i)} for i in range(4)]
        observation={'ok':True,'first_text_seconds':2,'total_seconds':3,'characters':12,'stage_ms':{}}
        responses=[(dict(observation),None) for _ in range(3)]+[KeyboardInterrupt()]
        with tempfile.TemporaryDirectory() as d,patch.object(suite,'STORE',Path(d)),patch.object(suite,'catalog',return_value=({'cases':cases,'rubric':{}},'hash')),patch.object(suite.station,'snapshot',return_value={'model':'same'}),patch.object(suite.station,'host_environment',return_value={}),patch.object(suite,'probe',side_effect=responses):
            report=suite.run(repeats=1,warmups=0)
            self.assertFalse(report['valid']);self.assertEqual(report['summary']['attempted'],4)
            self.assertEqual(report['summary']['succeeded'],3);self.assertEqual(report['summary']['failures'],{'interrupted':1})

    def test_comparison_explicitly_reports_model_and_corpus_changes(self):
        metrics=self.module('performance_metrics')
        base={'valid':True,'protocol':{},'per_case':{},'before':{'model_id':'3.5','database_sha256':'a'}}
        changed={**base,'before':{'model_id':'3.8','database_sha256':'b'}}
        result=metrics.compare(base,changed)
        self.assertIn('identity_changes',result)
        self.assertEqual(result['identity_changes']['model_id'],{'before':'3.5','after':'3.8'})

    def test_transport_close_failure_never_reports_success(self):
        transport=self.module('performance_transport')
        class BrokenClose(BytesIO):
            def __exit__(self,*args):raise OSError('close failed')
        opener=Mock();opener.open.return_value=BrokenClose(b'{"type":"text","content":"Answer"}\n{"type":"done"}\n')
        row,answer=transport.probe(opener,{'persona':'home-assistant','messages':[]},retain=True)
        self.assertFalse(row['ok']);self.assertEqual(row['error'],'transport_error');self.assertIsNone(answer)


if __name__=='__main__':unittest.main()
