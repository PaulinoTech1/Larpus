import unittest
from unittest.mock import patch
import importlib

class SkillsMetricsTests(unittest.TestCase):
    def test_warmups_failures_and_missing_values(self):
        api=importlib.import_module('scripts.benchmark_mcp_skills')
        rows=[{'phase':'warmup','ok':True,'first_text_seconds':999},
              {'phase':'measured','ok':True,'first_text_seconds':1},
              {'phase':'measured','ok':False,'error':'held'},
              {'phase':'measured','ok':True}]
        result=api.summarize_rows(rows)
        self.assertEqual(result['attempted'],3)
        self.assertEqual(result['success_rate'],2/3)
        self.assertEqual(result['first_text_seconds']['n'],1)
        self.assertEqual(api.percentiles(range(1,21))['p95'],19)

    def test_dry_run_executes_nothing(self):
        api=importlib.import_module('scripts.benchmark_mcp_skills')
        with patch.object(api.subprocess,'run',side_effect=AssertionError('Child executed')):
            result=api.main(['--baseline','a'*32,'--candidate','b'*32])
        self.assertEqual(result,0)
        with self.assertRaises(ValueError):api.release_id('../escape')

    def test_incomplete_or_changed_identity_is_invalid(self):
        api=importlib.import_module('scripts.benchmark_mcp_skills')
        self.assertFalse(api.valid_run([{'ok':True}],2,{'a':1},{'a':1}))
        self.assertFalse(api.valid_run([{'ok':True}],1,{'a':1},{'a':2}))
        self.assertTrue(api.valid_run([{'ok':False}],1,{'a':1},{'a':1}))

    def test_comparison_rejects_stable_but_different_workloads(self):
        api=importlib.import_module('scripts.benchmark_mcp_skills')
        with self.assertRaises(ValueError):api.require_matched({'A':{'workload':{'model':'one'}},'B':{'workload':{'model':'two'}}})
        api.require_matched({'A':{'workload':{'model':'one'}},'B':{'workload':{'model':'one'}}})

    def test_timeout_and_final_identity_failure_retain_receipts(self):
        api=importlib.import_module('scripts.benchmark_mcp_skills')
        with patch.object(api.subprocess,'run',side_effect=api.subprocess.TimeoutExpired('fixed',960)):
            self.assertEqual(api.probe(api.ROOT,{'id':'test'})['error'],'worker_timeout')
        with patch.object(api,'identity',side_effect=ValueError('changed')):
            self.assertIsNone(api.after_identities({'A':api.ROOT},[]))

    def test_worker_counts_partial_text_and_unknown_citations(self):
        import contextlib,io,json,sys
        from runtime import mcp_client
        api=importlib.import_module('scripts.benchmark_mcp_skills')
        def partial(persona,messages,skill,chunk):
            chunk('hello');raise OSError('failed')
        def unknown(persona,messages,skill,chunk):
            chunk('answer');return {'status':200,'citation_check':{'unknown':['unknown-id']}}
        for operation in (partial,unknown):
            output=io.StringIO()
            with patch.object(mcp_client,'stream_chat',side_effect=operation),patch.object(sys,'argv',['worker',str(api.ROOT),'{}']),contextlib.redirect_stdout(output):
                # Supply the fixed case fields without launching inference.
                sys.argv[2]=json.dumps({'persona':'home-assistant','messages':[]})
                exec(api.WORKER,{})
            row=json.loads(output.getvalue());row['phase']='measured'
            report=api.summarize_rows([row])
            if operation is partial:self.assertEqual(report['partial_failures'],1)
            else:self.assertEqual(report['unknown_citation_samples'],1)

    def test_after_failure_still_writes_invalid_report(self):
        import tempfile,json
        from pathlib import Path
        from types import SimpleNamespace
        api=importlib.import_module('scripts.benchmark_mcp_skills')
        args=SimpleNamespace(baseline='a'*32,candidate='b'*32,repeats=1,warmups=1)
        with tempfile.TemporaryDirectory() as temp,patch.object(api,'ROOT',Path(temp)),patch.object(api,'identity',return_value={'workload':{}}),patch.object(api,'after_identities',return_value=None),patch.object(api,'probe',return_value={'ok':False,'error':'timeout'}):
            self.assertEqual(api.run(args,[{'id':'case'}]),1)
            report=next(Path(temp).rglob('manifest.json'))
            self.assertFalse(json.loads(report.read_text())['valid'])
            self.assertEqual(len(report.with_name('raw.jsonl').read_text().splitlines()),4)
