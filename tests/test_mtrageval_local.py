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

    def record(self,case,task):
        return {'task':task,'case':case,'arm':'baseline','repeat':1,'status':'complete','sources':[],
                'first_text_seconds':None,'total_seconds':1.0,'prompt_tokens':None,'output_tokens':None,'review':None}


if __name__=='__main__':unittest.main()
