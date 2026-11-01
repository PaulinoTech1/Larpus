import unittest
import importlib.util
import json
import sqlite3
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from runtime import inference


class CpuBenchmarkTests(unittest.TestCase):
    def test_stream_reports_numeric_stages_without_recording_content(self):
        frames=iter([{'message':{'content':'A useful answer. '}},{'done':True}])
        with patch.object(inference,'messages_for',return_value=[{'role':'system','content':'Rules'},{'role':'user','content':'Hello'}]),patch.object(inference,'validate_record'),patch.object(inference,'compression_envelope',return_value=None),patch.object(inference,'augment',side_effect=lambda prepared,persona,timings=None:(prepared,[])),patch.object(inference,'active_model',return_value='larpus3.8:27b-q4'),patch.object(inference,'gpu_placement',return_value='GPU'),patch.object(inference,'chat_stream',return_value=frames),patch.object(inference,'gate',side_effect=lambda text,*args:{'status':200,'content':text}),patch.object(inference,'stream_pending',return_value=False):
            result=inference.chat('home-assistant',[{'role':'user','content':'Hello'}],on_chunk=lambda text:None)
        self.assertEqual(result['status'],200)
        self.assertIn('timing_ms',result,'Stage timings are missing')
        timing=result['timing_ms']
        for key in ('input','retrieval','model_selection','model_first_frame','first_checked_text','inference_total'):
            self.assertIsInstance(timing[key],(int,float));self.assertGreaterEqual(timing[key],0)
        self.assertLessEqual(timing['first_checked_text'],timing['inference_total'])
        self.assertTrue(all(type(v) in (int,float) for v in timing.values()))

    def test_sweep_rejects_more_than_twenty_threads_and_ranking_ignores_unscored(self):
        from scripts import cpu_benchmark as bench
        with self.assertRaises(ValueError):bench.settings([8,24],[4],1)
        self.assertEqual(bench.ranked([10,20,30],[None,0.5,0.1]),[20,30])
        self.assertEqual(bench.overlap([10,20],[20]),0.5)
        self.assertEqual(bench.settings([4,8,20],[2,4],2),[(t,b) for t in (4,8,20) for b in (2,4)])

    def test_requested_threads_are_clamped_and_reported_separately(self):
        from scripts import cpu_benchmark as bench
        self.assertTrue(hasattr(bench,'effective_threads'),'Effective CPU thread reporting is missing')
        self.assertEqual(bench.effective_threads(20,8),8)
        self.assertEqual(bench.effective_threads(20,24),20)
        self.assertEqual(bench.effective_threads(8,None),1)
        with self.assertRaises(ValueError):bench.effective_threads(24,24)

    def test_probe_preserves_stage_counts_and_filters_non_numeric_metadata(self):
        spec=importlib.util.spec_from_file_location('chat_benchmark',Path(__file__).resolve().parents[1]/'scripts/benchmark-chat-latency.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        events=[{'type':'text','content':'Public answer.'},{'type':'done','timing_ms':{'retrieval':12,'preflight':True,'input':float('nan'),'secret':'private text','mcp_connect':-1}}]
        opener=unittest.mock.Mock();opener.open.return_value=BytesIO(b''.join((json.dumps(e)+'\n').encode() for e in events))
        result=module.probe(opener,'home-assistant','Hello')
        self.assertEqual(result['stage_ms'],{'retrieval':12})
        self.assertNotIn('Public answer',json.dumps(result))

    def test_partial_reranking_keeps_missing_scores_out_of_quality_proxy(self):
        from scripts import cpu_benchmark as bench
        class Engine:
            def neighbors(self,question,limit):return [1,2,3]
            def rerank(self,question,passages,deadline):
                self.deadline=deadline
                return [0.1,None,0.9]
        connection=sqlite3.connect(':memory:');connection.execute('CREATE TABLE chunks(text)')
        connection.executemany('INSERT INTO chunks VALUES (?)',[(str(i),) for i in range(3)])
        try:
            engine=Engine();result=bench.sample(engine,connection,'Question',0.9)
            self.assertEqual(result['top'],[3,1]);self.assertEqual(result['scored'],2)
            self.assertIsNotNone(engine.deadline)
        finally:connection.close()


if __name__=='__main__':unittest.main()
