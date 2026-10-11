import http.client
from contextlib import closing
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from runtime import gateway
from runtime.auth import Auth, password_record
from scripts import tailscale_bridge as bridge


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.backend=ThreadingHTTPServer(('127.0.0.1',0),gateway.Handler)
        cls.backend.tls=True  # HTTPS semantics, with transport replaced only in tests.
        cls.backend.auth=Auth(password_record('test-password-only'))
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),bridge.Bridge)
        cls.server.config={'hostname':'station.example.ts.net','owner_login':'owner@example.com',
                           'upstream':'127.0.0.1','upstream_port':cls.backend.server_port}
        cls.threads=[]
        for server in (cls.backend,cls.server):
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();cls.threads.append(thread)

    @classmethod
    def tearDownClass(cls):
        for server in (cls.server,cls.backend):server.shutdown();server.server_close()
        for thread in cls.threads:thread.join()

    def request(self,method,path,body=None,extra=None):
        headers={'Host':'station.example.ts.net','Tailscale-User-Login':'owner@example.com'}
        if method=='POST':headers.update({'Origin':'https://station.example.ts.net','Content-Type':'application/json'})
        headers.update(extra or {})
        with patch.object(bridge,'upstream',side_effect=lambda cfg:http.client.HTTPConnection('127.0.0.1',self.backend.server_port,timeout=3)):
            with closing(http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)) as conn:
                conn.request(method,path,json.dumps(body) if body is not None else None,headers)
                response=conn.getresponse();return response.status,dict(response.getheaders()),response.read()

    def login(self):
        status,headers,_=self.request('POST','/api/login',{'password':'test-password-only'})
        self.assertEqual(status,200);self.assertIn('Secure',headers['Set-Cookie'])
        return {'Cookie':headers['Set-Cookie'].split(';')[0]}

    def test_password_required_and_hud_keeps_security_headers(self):
        self.assertEqual(self.request('GET','/api/personas')[0],401)
        self.assertEqual(self.request('GET','/login')[0],200)
        status,headers,body=self.request('GET','/',extra=self.login())
        self.assertEqual(status,200);self.assertIn(b'<!',body)
        self.assertIn('Content-Security-Policy',headers)

    def test_owner_host_origin_and_framing_are_checked(self):
        for extra in ({'Host':'evil.example'}, {'Tailscale-User-Login':'friend@example.com'},
                      {'Tailscale-User-Login':''}, {'Origin':'https://evil.example'}):
            self.assertEqual(self.request('GET','/login',extra=extra)[0],403)
        self.assertEqual(self.request('POST','/api/login',{},extra={'Origin':''})[0],403)
        self.assertEqual(self.request('GET','/login',extra={'Transfer-Encoding':'chunked'})[0],400)
        self.assertEqual(self.request('GET','/login',extra={'Content-Length':'4000001'})[0],413)

    def test_voice_roundtrip_and_streaming_use_existing_gateway(self):
        cookie=self.login()
        with patch('runtime.voice.call',return_value={'audio':'mock-wav','format':'wav'}) as voice:
            status,_,body=self.request('POST','/api/voice',{'action':'synthesize','text':'Hello from your tutor.'},cookie)
            self.assertEqual(status,200);self.assertEqual(json.loads(body)['audio'],'mock-wav');voice.assert_called_once()
        def stream(persona,messages,skill,on_chunk):
            on_chunk('Hello');return {'status':200,'sources':[]}
        with patch.object(gateway,'mcp_stream',side_effect=stream):
            status,headers,body=self.request('POST','/api/chat/stream',{'persona':'home-assistant','messages':[{'role':'user','content':'Hello'}]},cookie)
            self.assertEqual(status,200);self.assertEqual(headers['Content-Type'],'application/x-ndjson')
            self.assertEqual([json.loads(line)['type'] for line in body.splitlines()],['text','done'])

    def test_upstream_errors_fail_closed(self):
        with patch.object(bridge,'upstream',side_effect=OSError('unavailable')):
            conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
            conn.request('GET','/login',headers={'Host':'station.example.ts.net','Tailscale-User-Login':'owner@example.com'})
            reply=conn.getresponse();self.assertEqual(reply.status,502);reply.read();conn.close()

    def test_settings_cannot_target_password_free_or_public_endpoint(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'data/releases').mkdir(parents=True)
            config=root/'bridge.json';config.write_text(json.dumps({'hostname':'station.example.ts.net','owner_login':'owner@example.com','port':8088}))
            active=root/'data/releases/active.json'
            for ip in ('127.0.0.1','8.8.8.8','100.64.0.1'):
                active.write_text(json.dumps({'host':ip,'port':8080}))
                with self.assertRaises(ValueError):bridge.settings(config,root)
            active.write_text('{"host":"192.168.1.2","port":8080}')
            with patch.object(bridge.ssl,'create_default_context') as tls:
                cfg=bridge.settings(config,root)
                self.assertEqual(cfg['upstream'],'192.168.1.2')
                tls.assert_called_once_with(cafile=str(root/'data/tls/ca.crt'))


if __name__=='__main__':unittest.main()
