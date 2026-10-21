import asyncio
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from mcp import Client
from runtime import mcp_server,mcp_client,inference
from runtime import gateway

class ExecutionTransportTests(unittest.TestCase):
    def test_parent_clock_stages_are_disjoint_and_invalid_values_are_unknown(self):
        self.assertEqual(mcp_client.parent_stages(20.,30.,100.),{'preflight':20.,'connect':30.,'call_and_metadata':50.})
        self.assertEqual(mcp_client.parent_stages(20.,30.,40.),{})
        self.assertEqual(mcp_client.parent_stages(float('nan'),30.,100.),{})

    def test_host_attests_source_after_isolated_child_response(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'deployment.json').write_text(json.dumps({'source_fingerprint':'a'*64}))
            result={'execution':{'profile':'verified','model':'local','source_fingerprint':None}}
            with patch.object(mcp_client,'ROOT',root):mcp_client.attach_source_receipt(result)
            self.assertEqual(result['execution']['source_fingerprint'],'a'*64)
            self.assertEqual(result['execution']['model'],'local')
    def test_diagnostic_queue_timing_is_separate(self):
        result={'status':200}
        gateway.add_queue_timing(result,{'execution':{'profile':'diagnostic'}},.25)
        self.assertEqual(result['timing_ms']['gateway_queue'],250.)
        plain={'status':200}
        gateway.add_queue_timing(plain,{},.25)
        self.assertNotIn('timing_ms',plain)
    def request(self,metadata):
        async def run():
            async with Client(mcp_server.server) as client:
                return await client.call_tool('chat_local',{'persona':'home-assistant','messages':[{'role':'user','content':'Hello'}]},meta=metadata)
        with patch.object(mcp_server,'allowed',return_value=True):return asyncio.run(run())
    def test_metadata_roundtrip_and_request_isolation(self):
        with patch.object(inference,'chat',return_value={'status':200,'content':'Fine.'}) as chat:
            self.request({'larpus_execution':{'profile':'diagnostic','base':'ultra-fast','interaction':'coding'}})
            self.assertEqual(chat.call_args.kwargs['execution']['base'],'ultra-fast')
            self.request(None)
            self.assertEqual(chat.call_args.kwargs['execution']['profile'],'verified')
    def test_forged_metadata_rejected_before_inference(self):
        with patch.object(inference,'chat') as chat:
            result=self.request({'larpus_execution':{'profile':'ultra-fast','security':False}})
            self.assertTrue(result.is_error or result.structured_content.get('status')==400)
            chat.assert_not_called()
    def test_client_rejects_before_preflight(self):
        with patch.object(mcp_client,'child_parameters') as child:
            with self.assertRaises(ValueError):asyncio.run(mcp_client.call_async('chat_local',{},execution={'profile':'raw'}))
            child.assert_not_called()
    def test_inference_rejects_before_model(self):
        with patch.object(inference,'ollama') as model:
            result=inference.chat('home-assistant',[],execution={'profile':'host'})
            self.assertEqual(result['status'],400);model.assert_not_called()
