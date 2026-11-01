import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('public_ci',Path(__file__).resolve().parents[1]/'scripts/ci.py')
ci=importlib.util.module_from_spec(spec);spec.loader.exec_module(ci)

class PublicCITests(unittest.TestCase):
    def test_private_inventory_boundaries(self):
        for name in ('data/tls/server.key','vendor/package.py','knowledge/approved.sqlite',
                     'knowledge/notes.build.sqlite-wal','knowledge/provenance.json','.env','models/model.gguf'):
            self.assertTrue(ci.forbidden(name),name)
        for name in ('README.md','knowledge/authors.json','knowledge/sources.json','evals/stegdetect.json'):
            self.assertFalse(ci.forbidden(name),name)

    def test_first_check_failure_stops_pipeline(self):
        with patch.object(ci,'inventory'),patch.object(ci,'execute',side_effect=subprocess.CalledProcessError(1,['test'])) as run:
            with patch('sys.argv',['ci.py']),self.assertRaises(subprocess.CalledProcessError):ci.main()
        self.assertEqual(run.call_count,1)

    def test_pipeline_contains_no_deployment_command(self):
        with patch.object(ci,'inventory'),patch.object(ci,'execute') as run,patch('sys.argv',['ci.py']):ci.main()
        commands=[c.args[0] for c in run.call_args_list]
        self.assertEqual(len(commands),3)
        self.assertTrue(any('scripts/verify.py' in command for command in commands))
        self.assertFalse(any('releases.py' in ' '.join(c) or 'verify-broker-live.py' in ' '.join(c) for c in commands))
