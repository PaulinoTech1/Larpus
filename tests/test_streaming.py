import asyncio
import base64
import json
import tempfile
import threading
import http.client
from types import SimpleNamespace
from http.server import ThreadingHTTPServer
import unittest
from pathlib import Path
from unittest.mock import patch
from mcp import Client
from runtime import dlp,inference,mcp_server,gateway
from runtime.local_ollama import chat_stream


class StreamingTests(unittest.TestCase):
    def run_stream(self,deltas,private=None,placement='GPU'):
        released=[]
        settings=dlp.policy()
        if private:settings['private_values']=[private]
        frames=[{'message':{'content':x},'done':False} for x in deltas]+[{'done':True}]
        with tempfile.TemporaryDirectory() as temp,patch.object(dlp,'QUARANTINE',Path(temp)/'quarantine'),patch.object(dlp,'policy',return_value=settings),patch.object(inference,'active_model',return_value='qwen3.5:27b-q4_K_M'),patch.object(inference,'gpu_placement',return_value=placement),patch.object(inference,'chat_stream',return_value=iter(frames)):
            result=inference.chat('home-assistant',[{'role':'user','content':'Hello'}],on_chunk=released.append)
            held=[json.loads(p.read_text()) for p in dlp.QUARANTINE.glob('*.json')] if dlp.QUARANTINE.exists() else []
        return result,released,held

    def test_sentences_released_before_generation_finishes(self):
        result,chunks,_=self.run_stream(['Good morning. ','Here is a useful reply. ','All done.'])
        self.assertEqual(result['status'],200)
        self.assertEqual(''.join(chunks),result['content'])
        self.assertGreaterEqual(len(chunks),2)

    def test_private_phrase_across_sentence_boundary_is_not_partially_released(self):
        for secret in ('Private phrase. More private text', 'Private phrase. More private text'.encode().hex(),base64.b64encode(b'private-code-value').decode()):
            cut=secret.index('. ')+2 if '. ' in secret else len(secret)//2
            result,chunks,held=self.run_stream([secret[:cut],secret[cut:]],private='Private phrase. More private text' if '. ' in secret or secret.startswith('5072') else 'private-code-value')
            self.assertEqual(result['status'],422)
            self.assertEqual(chunks,[])
            self.assertTrue(held)

    def test_fragmented_credentials_addresses_and_paths_held(self):
        for deltas in (['password=abc','defgh. '],['Address 192.','168.1.2. '],['Path C',':/private/file. '],['Token ghp_','A'*25+'. ']):
            result,chunks,held=self.run_stream(deltas)
            self.assertEqual(result['status'],422)
            self.assertEqual(chunks,[])
            self.assertTrue(held)

    def test_later_hold_stops_future_release_and_quarantines_prefix(self):
        result,chunks,held=self.run_stream(['Useful advice. ','Secret address 192.168.1.2. '])
        self.assertEqual(chunks,['Useful advice. '])
        self.assertEqual(result['status'],422)
        self.assertIn('Useful advice.',held[0]['output'])

    def test_gpu_required_before_first_release(self):
        result,chunks,_=self.run_stream(['A useful reply. '],placement='CPU')
        self.assertEqual(result['status'],503)
        self.assertEqual(chunks,[])

    def test_mcp_progress_is_checked_content_and_tool_schema_unchanged(self):
        async def check():
            chunks=[]
            async def progress(p,total,message):chunks.append(message)
            def chat(persona,messages,skill,on_chunk=None,execution=None):
                self.assertIsNotNone(on_chunk)
                self.assertEqual(execution,{'profile':'verified','interaction':'conversation'})
                on_chunk('Checked sentence. ')
                return {'status':200,'content':'Checked sentence. '}
            with patch.object(inference,'chat',side_effect=chat):
                async with Client(mcp_server.server) as client:
                    tools=sorted([t.model_dump(mode='json',exclude_none=True) for t in (await client.list_tools()).tools],key=lambda t:t['name'])
                    from runtime.security_scan import APPROVED
                    self.assertEqual(tools,json.loads(APPROVED.read_text())['tools'])
                    result=await client.call_tool('chat_local',{'persona':'home-assistant','messages':[{'role':'user','content':'Hello'}]},progress_callback=progress,meta={'larpus_stream':True})
                    self.assertFalse(result.is_error,str(result))
                    self.assertEqual(chunks,['Checked sentence. '])
        asyncio.run(check())

    def test_ndjson_transport_requires_done_and_caps_frames(self):
        from io import BytesIO
        with patch.dict('os.environ',{'LARPUS_ISOLATION':'host'}):
            for raw in (b'{"message":{"content":"Hello"}}\n',b'x'*65537):
                with patch('runtime.local_ollama.HTTP.open',return_value=BytesIO(raw)):
                    with self.assertRaises(ValueError):list(chat_stream({'model':'local'}))
            with patch('runtime.local_ollama.HTTP.open',return_value=BytesIO(b'{"message":{"content":"Hello"}}\n{"done":true}\n')):
                self.assertEqual(len(list(chat_stream({'model':'local'}))),2)
        with patch.dict('os.environ',{'LARPUS_ISOLATION':'sealed'}):
            with self.assertRaises(ValueError):list(chat_stream({'model':'local'}))

    def test_gateway_flushes_before_completion_and_reports_later_hold(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),gateway.Handler)
        server.local_auth_bypass=True
        server.auth=SimpleNamespace(allowed=lambda *args:True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        release=threading.Event()
        def stream(persona,messages,skill,callback):
            callback('Checked first sentence. ')
            if not release.wait(3):raise OSError('Test timed out')
            return {'status':422,'error':'Output held by local DLP.'}
        connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
        try:
            with patch.object(gateway,'mcp_stream',side_effect=stream):
                connection.request('POST','/api/chat/stream',json.dumps({'persona':'home-assistant','messages':[{'role':'user','content':'Hello'}]}),{'Content-Type':'application/json'})
                response=connection.getresponse()
                self.assertEqual(response.status,200)
                self.assertEqual(json.loads(response.readline()),{'type':'text','content':'Checked first sentence. '})
                self.assertFalse(release.is_set(),'first line must arrive while inference is still waiting')
                release.set()
                self.assertEqual(json.loads(response.readline())['type'],'error')
                self.assertEqual(response.read(),b'')
        finally:
            release.set();connection.close();server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
