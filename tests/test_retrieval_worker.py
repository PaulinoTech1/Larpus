import os
from pathlib import Path
import unittest
from unittest.mock import patch
from runtime import retrieval,retrieval_worker,knowledge

ROOT=Path(__file__).resolve().parents[1]

class FakeEngine:
    rowids=[1,2,3]
    def neighbors(self,question,limit):return [3,1][:limit]
    def rerank(self,question,passages,deadline=None):return [float(len(p)) for p in passages]

class RetrievalWorkerTests(unittest.TestCase):
    def setUp(self):retrieval.reset()
    def tearDown(self):retrieval.reset()

    def test_protocol_is_bounded_and_strict(self):
        engine=FakeEngine()
        self.assertEqual(retrieval_worker.handle(engine,{'action':'neighbors','question':'q','limit':2},5),{'rowids':[3,1]})
        self.assertEqual(retrieval_worker.handle(engine,{'action':'rerank','question':'q','passages':['ab','a'],'budget_ms':500},5),{'scores':[2.0,1.0]})
        self.assertTrue(retrieval_worker.handle(engine,{'action':'status'},5)['ready'])
        for bad in ({'action':'neighbors','question':'q','limit':999},{'action':'neighbors','question':'','limit':2},
                    {'action':'rerank','question':'q','passages':['x']*33,'budget_ms':5},{'action':'rerank','question':'q','passages':['x'*4001],'budget_ms':5},
                    {'action':'rerank','question':'q','passages':['x'],'budget_ms':99999},{'action':'neighbors','question':'q','limit':2,'path':'/etc'},
                    {'action':'load','question':'q'},['status']):
            with self.assertRaises(ValueError):retrieval_worker.validate(bad)

    def test_remote_mode_never_loads_models_in_chat_process(self):
        with patch.dict(os.environ,{'LARPUS_RETRIEVAL_WORKER':'remote'}),patch.object(retrieval_worker,'call',side_effect=OSError('no socket')),patch.object(retrieval,'Engine',side_effect=AssertionError('local load')):
            self.assertIsNone(retrieval.engine(knowledge.DIRECTORY))
            shown=retrieval.status(knowledge.DIRECTORY)
            self.assertEqual(shown['reason'],'OSError')
            self.assertNotIn('no socket',shown['reason'])
            self.assertTrue(shown['failure_cached'])

    def test_remote_engine_relays_and_validates(self):
        replies={'status':{'ready':True},'neighbors':{'rowids':[7,8]},'rerank':{'scores':[0.5,None]}}
        with patch.object(retrieval_worker,'call',side_effect=lambda request,timeout:replies[request['action']]) as call:
            engine=retrieval.RemoteEngine()
            self.assertEqual(engine.neighbors('q',4),[7,8])
            self.assertEqual(engine.rerank('q',['a','b']),[0.5,None])
            self.assertLessEqual(call.call_args.args[1],engine.deadline+1.0+0.01)
        replies['rerank']={'scores':['bad',1]}
        with patch.object(retrieval_worker,'call',side_effect=lambda request,timeout:replies[request['action']]):
            with self.assertRaises(ValueError):retrieval.RemoteEngine().rerank('q',['a','b'])

    def test_worker_failure_mid_chat_keeps_bm25_order(self):
        rows=[('a','t','u','s','l1','one'),('b','t','u','s','l2','two')]
        with patch.object(retrieval_worker,'call',side_effect=lambda request,timeout:{'ready':True} if request['action']=='status' else (_ for _ in ()).throw(TimeoutError())):
            engine=retrieval.RemoteEngine()
        with patch.object(knowledge,'_engine',return_value=engine),patch.object(retrieval_worker,'call',side_effect=TimeoutError()):
            self.assertEqual(knowledge._hybrid('q',rows,False),rows)

    def test_open_retries_io_and_waits_for_a_file_change_after_rejection(self):
        previous=os.environ.get('LARPUS_RETRIEVAL_WORKER')
        self.addCleanup(lambda: os.environ.pop('LARPUS_RETRIEVAL_WORKER',None) if previous is None else os.environ.__setitem__('LARPUS_RETRIEVAL_WORKER',previous))
        calls=[]
        def reject(directory):
            calls.append(1)
            raise ValueError('hash mismatch SECRET')
        def sleep(seconds):
            self.assertEqual(seconds,retrieval._ENGINE_RETRY_SECONDS)
            raise RuntimeError('stop')
        with patch.object(retrieval_worker,'_marker',return_value='same'),patch.object(retrieval,'Engine',reject),patch.object(retrieval_worker.time,'sleep',sleep):
            with self.assertRaises(RuntimeError):retrieval_worker._load_engine(knowledge.DIRECTORY)
        self.assertEqual(calls,[1])
        calls.clear()
        def retry(directory):
            calls.append(1)
            if len(calls)==1:raise OSError('busy SECRET')
            return 'ready'
        with patch.object(retrieval_worker,'_marker',return_value='same'),patch.object(retrieval,'Engine',retry),patch.object(retrieval_worker.time,'sleep',lambda _seconds:None):
            self.assertEqual(retrieval_worker._load_engine(knowledge.DIRECTORY),'ready')
        self.assertEqual(len(calls),2)

    def test_image_runs_worker_and_remote_mode(self):
        containerfile=(ROOT/'deploy/windows-home/Containerfile').read_text(encoding='utf-8')
        self.assertIn('CMD ["python", "-m", "runtime.retrieval_worker", "--serve"]',containerfile)
        self.assertIn('LARPUS_RETRIEVAL_WORKER=remote',containerfile)
        source=(ROOT/'runtime/retrieval_worker.py').read_text(encoding='utf-8')
        self.assertIn('AF_UNIX',source);self.assertNotIn('AF_INET',source);self.assertIn('0o600',source)

if __name__=='__main__':unittest.main()