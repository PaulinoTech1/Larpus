from copy import deepcopy
import io
import unittest
from unittest.mock import patch
from scripts import mtrageval_local as m
from runtime import rag_eval


class MtragevalLocalTests(unittest.TestCase):
    def setUp(self):
        self.catalog=m.catalog()
        self.run=m.prepare(self.catalog)

    def test_catalog_has_conversational_answerability_classes(self):
        self.assertEqual({c['class'] for c in self.catalog['cases']},m.CLASSES)
        self.assertTrue(all(len(c['messages'])>=3 for c in self.catalog['cases']))
        bad=deepcopy(self.catalog);bad['cases'][0]['messages']=[bad['cases'][0]['messages'][-1]]
        with self.assertRaises(ValueError):m.catalog_from_value(bad)
        bad=deepcopy(self.catalog);bad['cases'][0]['fixed_evidence']=[{'id':'unrelated','locator':'document'}]
        with self.assertRaises(ValueError):m.catalog_from_value(bad)

    def test_a_and_b_worker_keep_retrieval_and_generation_separate(self):
        case=self.catalog['cases'][0]
        request={'task':'A','persona':case['persona'],'messages':case['messages'],'fixed_selectors':None}
        with patch.object(rag_eval,'messages_for',return_value=[{'role':'system','content':'persona'},{'role':'user','content':'question'}]),\
             patch.object(rag_eval,'require_persona',return_value={'id':case['persona']}),\
             patch.object(rag_eval,'augment',return_value=([],[{'id':'qubes-requirements','locator':'document offset 0'}])) as augment,\
             patch.object(rag_eval,'chat',side_effect=AssertionError('model ran')):
            result=rag_eval.evaluate(request)
            self.assertEqual(result['passages'][0]['id'],'qubes-requirements')
            augment.assert_called_once_with([{'role':'system','content':'persona'},{'role':'user','content':'question'}],case['persona'])
        request={**request,'task':'B','fixed_selectors':case['fixed_evidence']}
        with patch.object(rag_eval,'messages_for'),patch.object(rag_eval,'require_persona',return_value={'id':case['persona']}),\
             patch.object(rag_eval,'augment',side_effect=AssertionError('retrieval ran')),\
             patch.object(rag_eval,'chat',return_value={'status':200,'content':'Grounded.','sources':[], 'context':None}) as chat:
            result=rag_eval.evaluate(request)
            self.assertEqual(result['answer'],'Grounded.')
            chat.assert_called_once_with(case['persona'],case['messages'],fixed_selectors=case['fixed_evidence'])

    def test_pending_report_is_not_a_result(self):
        summary=m.summarize(self.run,self.catalog)
        self.assertFalse(summary['comparison_ready'])
        self.assertIsNone(summary['baseline']['C']['prompt_tokens'])
        self.assertEqual(summary['baseline']['A']['attempts'],0)

    def test_fixed_evidence_receipt_requires_retrieval_disabled_and_full_coverage(self):
        records=[self.record(c['id'],'B') for c in self.catalog['cases']]
        receipt={'task':'B','arm':'baseline','method':'local sealed fixed-evidence evaluator',
                 'source_fingerprint':'a'*64,'model_weight_sha256':'b'*64,
                 'fixed_evidence_sha256':'c'*64,'retrieval_disabled':True,'records':records}
        bad=deepcopy(receipt);bad['retrieval_disabled']=False
        with self.assertRaises(ValueError):m.import_task(self.run,self.catalog,bad)
        bad=deepcopy(receipt);bad['records'].pop()
        with self.assertRaises(ValueError):m.import_task(self.run,self.catalog,bad)
        m.import_task(self.run,self.catalog,receipt)
        with self.assertRaises(ValueError):m.import_task(self.run,self.catalog,receipt)

    def test_recorded_source_ids_allow_underscores_and_one_copy(self):
        row=self.record(self.catalog['cases'][0]['id'],'C')
        row['sources']=['github-lock_down','qubes-requirements']
        m.checked_record(row,set(self.run['cases']))
        row['sources']=['github-lock_down','github-lock_down']
        with self.assertRaises(ValueError):m.checked_record(row,set(self.run['cases']))

    def test_failure_stays_in_denominator_and_review_requires_completion(self):
        row=self.record(self.catalog['cases'][0]['id'],'A');row['status']='failed'
        self.run['records'].append(row)
        report=m.summarize(self.run,self.catalog)['baseline']['A']
        self.assertEqual((report['attempts'],report['completed'],report['failed_or_held']),(1,0,1))
        row['review']={'reviewer':'owner','answer_correct':False,'evidence_supported':False,'note':'Failed'}
        with self.assertRaises(ValueError):m.validate_run(self.run,self.catalog)

    def test_completed_review_cannot_be_replaced(self):
        case=self.catalog['cases'][0]['id'];self.run['records'].append(self.record(case,'A'))
        m.review_record(self.run,self.catalog,'baseline','A',case,1,'owner','Source checked',True,True)
        with self.assertRaises(ValueError):m.review_record(self.run,self.catalog,'baseline','A',case,1,'owner','Changed',False,False)

    def test_checked_stream_captures_context_and_completed_answer(self):
        class Reply(io.BytesIO):
            status=200
            def __enter__(self):return self
            def __exit__(self,*_args):self.close()
        class Opener:
            def open(self,*_args,**_kwargs):
                return Reply(b'{"type":"text","content":"Hello."}\n{"type":"done","sources":[],"context":{"prompt_tokens":123,"output_tokens":19}}\n')
        row,answer=m.probe_case(Opener(),self.catalog['cases'][0])
        self.assertTrue(row['ok']);self.assertEqual(row['context'],{'prompt_tokens':123,'output_tokens':19})
        self.assertEqual(answer['answer'],'Hello.')

    def test_quarantine_without_text_is_a_hold_and_text_after_it_completes(self):
        class Reply(io.BytesIO):
            status=200
            def __enter__(self):return self
            def __exit__(self,*_args):self.close()
        class Opener:
            def __init__(self,payload):self.payload=payload
            def open(self,*_args,**_kwargs):return Reply(self.payload)
        held,answer=m.probe_case(Opener(b'{"type":"quarantine","removed":[0],"incidents":["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]}\n{"type":"done","local":true,"sources":[]}\n'),self.catalog['cases'][0])
        self.assertFalse(held['ok']);self.assertEqual(held['error'],'quarantined');self.assertIsNone(answer)
        done,answer=m.probe_case(Opener(b'{"type":"quarantine","removed":[0,1],"incidents":["bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"]}\n{"type":"text","content":"4 GB."}\n{"type":"done","sources":[],"context":{"prompt_tokens":10,"output_tokens":2}}\n'),self.catalog['cases'][0])
        self.assertTrue(done['ok']);self.assertEqual(answer['answer'],'4 GB.')

    def test_generation_interval_is_finite_and_budget_conservative(self):
        self.assertEqual(m.interval_seconds('6'),6)
        for value in (0,5.9,61,float('nan'),float('inf')):
            with self.subTest(value=value),self.assertRaises(ValueError):m.interval_seconds(value)

    def test_pacing_waits_only_for_remaining_start_interval(self):
        with patch.object(m.time,'monotonic',side_effect=[12,16]),patch.object(m.time,'sleep') as sleep:
            self.assertEqual(m.paced_start(10,6),16)
            sleep.assert_called_once_with(4)
        with patch.object(m.time,'monotonic',side_effect=[20,20]),patch.object(m.time,'sleep') as sleep:
            self.assertEqual(m.paced_start(10,6),20);sleep.assert_not_called()

    def test_stream_refusal_retains_only_bounded_metadata(self):
        class Reply(io.BytesIO):
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
        class Opener:
            def open(self,*args,**kwargs):
                return Reply(b'{"type":"text","content":"Partial."}\n{"type":"error","code":"cancellation_unconfirmed","error_id":"aaaaaaaaaaaaaaaa","error":"private reply must not be retained"}\n')
        row,answer=m.probe_case(Opener(),self.catalog['cases'][0])
        self.assertFalse(row['ok']);self.assertIsNone(answer)
        self.assertEqual(row['refusal_code'],'cancellation_unconfirmed');self.assertEqual(row['error_id'],'a'*16)
        self.assertNotIn('private reply',str(row));self.assertNotIn('Partial.',str(row))
        self.assertEqual(m.refusal_metadata({'code':'../private','error_id':'C:/private'}),{})

    def test_http_refusal_retains_status_and_code(self):
        class Opener:
            def open(self,*args,**kwargs):
                raise m.urllib.error.HTTPError('local',429,'Too many',{},io.BytesIO(b'{"code":"inference_budget","error":"must not be retained"}'))
        row,answer=m.probe_case(Opener(),self.catalog['cases'][0])
        self.assertFalse(row['ok']);self.assertIsNone(answer)
        self.assertEqual(row['http_status'],429);self.assertEqual(row['refusal_code'],'inference_budget')
        self.assertNotIn('must not',str(row))

    def test_c_paces_and_saves_failed_attempt_metadata_without_retry(self):
        error={'ok':False,'first_text_seconds':None,'total_seconds':1,'context':None,'error':'stream_rejected','refusal_code':'queue_full'}
        with patch.object(m.station,'snapshot',return_value={'release':'f'*32}),patch.object(m,'paced_start',return_value=10) as pace,patch.object(m,'probe_case',return_value=(error,None)) as probe,patch.object(m,'save') as save:
            m.record_c(self.run,self.catalog,'baseline',1,None)
        self.assertEqual(pace.call_count,5);self.assertEqual(probe.call_count,5)
        self.assertEqual(self.run['arms']['baseline']['generation_start_interval_seconds'],6)
        failures=[call.args[1] for call in save.call_args_list if 'failure' in call.args[1]]
        self.assertEqual(len(failures),5);self.assertTrue(all(f['failure']['refusal_code']=='queue_full' for f in failures))
        self.assertTrue(all(row['status']=='failed' for row in self.run['records']))

    def test_b_rejects_different_generation_pacing_before_execution(self):
        self.run['arms']['baseline']={'stable':True,'generation_start_interval_seconds':6}
        with patch.object(m.station,'snapshot') as snapshot,self.assertRaisesRegex(ValueError,'pacing differs'):
            m.record_ab(self.run,self.catalog,'baseline','B',1,None,interval=7)
        snapshot.assert_not_called()

    def record(self,case,task):
        return {'task':task,'case':case,'arm':'baseline','repeat':1,'status':'complete','sources':[],
                'first_text_seconds':None,'total_seconds':1.0,'prompt_tokens':None,'output_tokens':None,'review':None}


if __name__=='__main__':unittest.main()
