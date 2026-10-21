import subprocess
import unittest
from unittest.mock import patch
from scripts import verify

class VerificationTests(unittest.TestCase):
    def test_canonical_pipeline_covers_all_gates_without_deployment(self):
        commands=verify.commands('python-test','node-test')
        joined=[' '.join(command) for command in commands]
        self.assertIn('complexity.py check',joined[0])
        self.assertEqual(sum('test-local.py' in c for c in joined),1)
        self.assertTrue(all(any('tests/'+test in c for c in joined) for test in verify.UI_TESTS))
        self.assertTrue(any('broker-prompts.py --check' in c for c in joined))
        self.assertTrue(any('quality_evaluation.py --check' in c for c in joined))
        self.assertFalse(any('releases.py' in c or 'supervise.py' in c for c in joined))

    def test_first_failed_gate_stops_and_returns_failure(self):
        with patch.object(verify,'commands',return_value=[['first'],['second']]),patch.object(verify.subprocess,'run') as run:
            run.side_effect=subprocess.CalledProcessError(3,['first'])
            self.assertEqual(verify.main(),3)
        self.assertEqual(run.call_count,1)

