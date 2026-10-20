import unittest
import json
from types import SimpleNamespace
from unittest.mock import Mock,patch
from runtime.execution_preflight import observe
from runtime import mcp_client,isolation

class ExecutionPreflightTests(unittest.TestCase):
    def test_no_cache_or_partial_fallback(self):
        reader=Mock(side_effect=[SimpleNamespace(stdout=b'{"info":{}}'),SimpleNamespace(stdout=b'{"info":{"new":true}}'),OSError('failed')])
        command=lambda *args:['fixed']
        self.assertNotEqual(observe(['larpus-model'],command,reader),observe(['larpus-model'],command,reader))
        with self.assertRaises(OSError):observe(['larpus-model'],command,reader)
        self.assertEqual(reader.call_count,3)
    def test_explicit_profile_cannot_select_host(self):
        with patch.object(mcp_client,'mode',return_value='host'):
            for profile in ('verified','ultra-fast','diagnostic'):
                with self.assertRaises(ValueError):mcp_client.child_parameters({'profile':profile})
    def test_fast_context_only_changes_observation_selection(self):
        with patch.object(mcp_client,'mode',return_value='wsl-podman'),patch.object(mcp_client,'child_args',return_value=['wsl','fixed']) as args:
            mcp_client.child_parameters({'profile':'diagnostic','base':'ultra-fast'})
            args.assert_called_once_with(fast=True)
    def test_bad_observation_fails(self):
        for value in (None,[],True):
            with self.assertRaises(ValueError):observe(['larpus-model'],lambda *args:['fixed'],lambda *args,**kwargs:SimpleNamespace(stdout=json.dumps(value).encode()))
