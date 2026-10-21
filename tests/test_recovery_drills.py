from dataclasses import replace
from pathlib import Path
import os
import secrets
import tempfile
import unittest
from unittest.mock import Mock, patch
from scripts import recovery_drills as drills
from scripts.recovery_policy import decide, Policy
from tests.test_recovery_policy import IDENTITY, observation, history

class DrillTests(unittest.TestCase):
    def test_stream_contract_uses_discovered_node_executable(self):
        from types import SimpleNamespace
        with patch('shutil.which',return_value='portable-node'),patch.object(drills.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
            self.assertEqual(drills.contract_drill('truncated-stream')['state'],'passed')
        self.assertEqual(run.call_args.args[0][0],'portable-node')
    def test_refuse_production_or_reused_targets_before_signal(self):
        with self.assertRaises(ValueError):drills.owned(drills.SCRIPT.parents[1],'a'*32)
        with tempfile.TemporaryDirectory(prefix='larpus-recovery-drill-') as directory:
            path=Path(directory)
            with self.assertRaises(OSError):drills.owned(path,'a'*32)
            drills.save(path/'owner.json',{'nonce':'a'*32,'version':1})
            with self.assertRaises(ValueError):drills.owned(path,'b'*32)
        child=Mock()
        with patch.object(drills,'process_identity',return_value=replace(IDENTITY,creation='reused')):
            with self.assertRaises(ValueError):drills.terminate_owned(child,IDENTITY,IDENTITY.release_id)
        child.terminate.assert_not_called()

    def test_cancellation_and_evidence_are_measured(self):
        with tempfile.TemporaryDirectory() as directory:
            cancelled=drills.cancellation_drill(directory)
            evidenced=drills.evidence_drill(directory)
        self.assertEqual(cancelled['state'],'passed');self.assertEqual(cancelled['generation_count'],0)
        self.assertEqual(evidenced['state'],'passed');self.assertEqual(evidenced['generation_count'],0)
        self.assertEqual(evidenced['evidence_ids'],['game-a','game-b'])

    def test_five_injected_contracts(self):
        for name in drills.CASES:
            with self.subTest(name=name):self.assertEqual(drills.contract_drill(name)['state'],'passed')

    def test_clock_discontinuity_cannot_expire_budget(self):
        h=history(last_wall_time=1000,last_monotonic_time=100,attempts=(990.,995.))
        for wall,mono in ((2000,101),(1001,1)):
            self.assertEqual(decide(observation(wall_time=wall,monotonic_time=mono),h,Policy()).reason,'clock')

    @unittest.skipUnless(os.name=='nt','Exact gateway identity uses Windows CIM; Windows CI covers this drill')
    def test_real_disposable_gateway_and_independent_supervisor(self):
        with tempfile.TemporaryDirectory(prefix='larpus-recovery-drill-') as directory:
            path=Path(directory);nonce=secrets.token_hex(16)
            drills.save(path/'owner.json',{'nonce':nonce,'version':1})
            result=drills.gateway_drill(path,nonce)
            self.assertEqual(result['state'],'passed');self.assertEqual(result['attempts'],1)
            self.assertIsNone(result['generation_count'])
            self.assertIn('recovered',[item[1] for item in result['transitions']])

