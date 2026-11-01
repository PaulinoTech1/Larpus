import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('owner_broker_status',Path(__file__).resolve().parents[1]/'scripts/broker-status.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)

class BrokerStatusTests(unittest.TestCase):
    def fixture(self,root,identifier='a'*32):
        store=root/'data/releases';store.mkdir(parents=True)
        (store/'active.json').write_text(json.dumps({'id':identifier}),encoding='utf-8')
        if identifier=='a'*32:
            release=store/identifier;release.mkdir()
            (release/'deployment.json').write_text(json.dumps({'agent_name':'larpus-agent-'+identifier,'broker':{'protocol':2}}),encoding='utf-8')

    def test_reads_selected_broker_without_generation_and_filters_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            metadata={'scope':'broker-admission','active':None,'faulted':True,'waiting_chat':0,'unexpected':'must not propagate'}
            with patch.object(probe,'wsl_command',side_effect=lambda *args:list(args)),patch.object(probe.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps(metadata).encode())) as run:
                value=probe.status(root)
            self.assertTrue(value['broker']['faulted']);self.assertNotIn('unexpected',value['broker'])
            args=run.call_args.args[0]
            self.assertEqual(args[:3],['podman','exec','larpus-agent-'+'a'*32])
            self.assertEqual(args[-1],probe.CLIENT);self.assertNotIn('/api/chat',probe.CLIENT)
            self.assertTrue(run.call_args.kwargs['check']);self.assertEqual(run.call_args.kwargs['timeout'],15)

    def test_invalid_release_stops_before_process(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root,'../outside')
            with patch.object(probe.subprocess,'run') as run,self.assertRaises(ValueError):probe.status(root)
            run.assert_not_called()

    def test_malformed_or_oversized_status_is_rejected(self):
        for raw in (b'{}',b'[]',b'x'*8193):
            with self.subTest(raw=raw[:10]),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);self.fixture(root)
                with patch.object(probe,'wsl_command',return_value=['owner-status']),patch.object(probe.subprocess,'run',return_value=SimpleNamespace(stdout=raw)),self.assertRaises(ValueError):probe.status(root)

    def test_process_failure_remains_a_failure(self):
        with patch.object(probe,'status',side_effect=subprocess.TimeoutExpired('status',15)),patch('sys.stderr'):
            self.assertEqual(probe.main(),1)
