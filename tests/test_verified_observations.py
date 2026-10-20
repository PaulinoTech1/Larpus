import subprocess
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from runtime import isolation


class VerifiedObservationTests(unittest.TestCase):
    def fixture(self):
        containers=[{'Name':'larpus-model','Pod':'pod'}]
        return {'info':{'fresh':True},'containers':containers,'oci':[{'value':{}}],
                'pod':{'InfraContainerID':'infra'},'infra':{'Id':'infra'}}

    def test_independent_reads_overlap_and_dependencies_stay_ordered(self):
        value=self.fixture();wave=threading.Barrier(3)
        oci_started=threading.Event();infra_started=threading.Event()
        def policy(*args,**kwargs):
            wave.wait(timeout=2)
            return SimpleNamespace(stdout=b'')
        def query(*args):
            if args[0]=='info':wave.wait(timeout=2);return value['info']
            if args==('inspect','larpus-model'):
                wave.wait(timeout=2);return value['containers']
            if args==('pod','inspect','pod'):
                self.assertTrue(oci_started.wait(2))
                return value['pod']
            self.assertEqual(args,('inspect','infra'));infra_started.set()
            return [value['infra']]
        def oci(items):
            self.assertIs(items,value['containers']);oci_started.set()
            self.assertTrue(infra_started.wait(2))
            return [v['value'] for v in value['oci']]
        with patch.object(isolation,'wsl_command',return_value=['fixed']),patch.object(isolation.subprocess,'run',side_effect=policy),patch.object(isolation,'query',side_effect=query),patch.object(isolation,'read_oci_batch',side_effect=oci):
            self.assertEqual(isolation.collect_observations(['larpus-model'],False),value)

    def test_every_failed_read_rejects_without_fast_or_cached_fallback(self):
        value=self.fixture()
        for failed in ('policy','info','containers','oci','pod','infra'):
            def query(*args):
                key='info' if args[0]=='info' else 'pod' if args[0]=='pod' else 'infra' if args[-1]=='infra' else 'containers'
                if key==failed:raise subprocess.TimeoutExpired(['fixed'],15)
                return [value[key]] if key=='infra' else value[key]
            with self.subTest(failed=failed),patch.object(isolation,'wsl_command',return_value=['fixed']),patch.object(isolation.subprocess,'run',side_effect=OSError('policy') if failed=='policy' else None),patch.object(isolation,'query',side_effect=query),patch.object(isolation,'read_oci_batch',side_effect=ValueError('oci') if failed=='oci' else None,return_value=[v['value'] for v in value['oci']]),patch.object(isolation,'read_snapshot') as fast:
                with self.assertRaises((OSError,ValueError,subprocess.TimeoutExpired)):
                    isolation.collect_observations(['larpus-model'],False)
                fast.assert_not_called()

    def test_fresh_reads_and_bounded_numeric_phase_timings(self):
        value=self.fixture()
        def query(*args):
            if args[0]=='info':return value['info']
            if args[0]=='pod':return value['pod']
            return [value['infra']] if args[-1]=='infra' else value['containers']
        with patch.object(isolation,'wsl_command',return_value=['fixed']),patch.object(isolation.subprocess,'run') as policy,patch.object(isolation,'query',side_effect=query) as reads,patch.object(isolation,'read_oci_batch',return_value=[v['value'] for v in value['oci']]) as oci:
            for _ in range(2):
                timings={}
                self.assertEqual(isolation.collect_observations(['larpus-model'],False,timings=timings),value)
                self.assertEqual(set(timings),{'preflight_initial_reads','preflight_namespace_reads'})
                self.assertTrue(all(type(v) in (int,float) and 0<=v<=90000 for v in timings.values()))
        self.assertEqual(policy.call_count,2);self.assertEqual(reads.call_count,8);self.assertEqual(oci.call_count,2)


if __name__=='__main__':unittest.main()
