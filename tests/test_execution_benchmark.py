import unittest
from scripts.benchmark_execution_profiles import summarize, schedule, validate_url, validated_rows, combine_sessions
import json
import tempfile
from pathlib import Path
from unittest.mock import patch


class ExecutionBenchmarkTests(unittest.TestCase):
    def test_clock_groups_are_separate_and_accept_only_allowlisted_numbers(self):
        from scripts.benchmark_execution_profiles import clock_stages
        value=clock_stages({'execution_stages_ms':{'input':1.,'private':'secret'},
                            'mcp_parent_stages_ms':{'preflight':2.,'connect':float('nan')}})
        self.assertEqual(value,{'inference':{'input':1.},'mcp_parent':{'preflight':2.}})

    def test_candidate_measurement_does_not_change_active_selection(self):
        from scripts import benchmark_execution_profiles as benchmark
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);store=root/'data/releases';store.mkdir(parents=True)
            active='a'*32;candidate='b'*32
            (store/'active.json').write_text(json.dumps({'id':active}))
            for identifier in (active,candidate):
                release=store/identifier;release.mkdir()
                (release/'deployment.json').write_text(json.dumps({'source_fingerprint':identifier*2}))
            with patch.object(benchmark,'ROOT',root):
                pins=benchmark.pinned_inputs(candidate)
                self.assertEqual(pins['measured_release'],candidate)
                self.assertEqual(pins['selected_release'],active)
                self.assertEqual(pins['source_fingerprint'],candidate*2)
            self.assertEqual(json.loads((store/'active.json').read_text())['id'],active)
    def test_balanced_reproducible_schedule(self):
        cases=[{'id':str(i)} for i in range(20)]
        rows=schedule(cases,5,11)
        self.assertEqual(rows,schedule(cases,5,11))
        self.assertEqual(len(rows),300)
        self.assertEqual({sum(r['profile']==p for r in rows) for p in ('verified','ultra-fast','diagnostic')},{100})
        for start in range(0,len(rows),3):self.assertEqual(len({r['profile'] for r in rows[start:start+3]}),3)

    def test_failures_not_zero_filled_and_quantiles(self):
        report=summarize([{'ok':True,'first_seconds':1.,'total_seconds':2.},
                          {'ok':True,'first_seconds':3.,'total_seconds':4.},{'ok':False}])
        self.assertEqual(report['attempts'],3)
        self.assertEqual(report['successes'],2)
        self.assertEqual(report['first_seconds']['mean'],2.)
        self.assertAlmostEqual(report['first_seconds']['p95'],2.9)
        self.assertEqual(report['quality'],'unreviewed')
        self.assertIsNone(report['task_success'])

    def test_owner_loopback_only(self):
        self.assertEqual(validate_url('http://127.0.0.1:8080'),'http://127.0.0.1:8080')
        for url in ('https://example.com','http://user@127.0.0.1:8080','http://127.0.0.1:8080/other','http://127.0.0.1:11434'):
            with self.assertRaises(ValueError):validate_url(url)

    def test_nonfinite_and_private_fields_rejected(self):
        for value in ({'ok':True,'first_seconds':float('nan')},{'ok':True,'content':'private answer'}):
            with self.assertRaises(ValueError):validated_rows([value])

    def test_combining_requires_matching_pins_and_distinct_sessions(self):
        with tempfile.TemporaryDirectory() as temporary:
            directories=[Path(temporary)/str(i) for i in (1,2)]
            for session,directory in enumerate(directories,1):
                directory.mkdir()
                planned=schedule([{'id':str(i)} for i in range(50)],2,1)
                manifest={'session':session,'pins':{'model':'same'},'workload_sha256':'same','schedule':planned,'seed':1,'diagnostic_base':'verified','run':True,'served_model':'same','controls':{'model':'same','pipeline':['numpy','numpy',4]}}
                (directory/'manifest.json').write_text(json.dumps(manifest))
                rows=[{'ok':True,'case':str(i),'round':session-1,'profile':profile,'session':session,'first_seconds':1.,'total_seconds':2.} for i in range(50) for profile in ('verified','ultra-fast','diagnostic')]
                (directory/'rows.jsonl').write_text('\n'.join(map(json.dumps,rows)))
            manifest,rows=combine_sessions(directories)
            self.assertEqual(len(rows),300)
            self.assertEqual(manifest['sessions'],[1,2])
            with self.assertRaises(ValueError):combine_sessions([directories[0],directories[0]])
            manifest=json.loads((directories[1]/'manifest.json').read_text())
            manifest['pins']={'model':'different'}
            (directories[1]/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):combine_sessions(directories)

    def test_empty_or_unmatched_schedule_rejects(self):
        from scripts.benchmark_execution_profiles import check_complete_samples
        rows=[{'ok':False,'case':str(i),'round':0,'profile':p,'session':1} for i in range(100) for p in ('verified','ultra-fast','diagnostic')]
        with self.assertRaises(ValueError):check_complete_samples(rows,[])

    def test_served_identity_mismatch_aborts(self):
        from scripts.benchmark_execution_profiles import check_receipt, ComparisonChanged
        expected={'source_fingerprint':'a'*64,'model':'model'}
        with self.assertRaises(ComparisonChanged):check_receipt({'profile':'verified','model':'other','source_fingerprint':'a'*64},'verified',expected)

    def test_pipeline_identity_is_bounded_and_compared(self):
        from scripts.benchmark_execution_profiles import pipeline_identity
        self.assertEqual(pipeline_identity({'active_id':'assembly-optimized','requested_id':'assembly-optimized','workers':4}),('assembly-optimized','assembly-optimized',4))
        with self.assertRaises(ValueError):pipeline_identity({'active_id':'remote','requested_id':'numpy','workers':4})
