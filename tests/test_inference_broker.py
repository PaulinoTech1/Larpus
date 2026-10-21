import copy
import http.client
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from runtime import inference_broker as broker,isolation,local_ollama

POLICY={'version':1,'enabled':True,'model':'qwen3.5:27b-q4_K_M','context':131072,'max_output':6000}
def request():
    return {'model':POLICY['model'],'messages':[{'role':'user','content':'Hello'}],'stream':False,'think':False,'keep_alive':-1,'options':{'temperature':.3,'num_ctx':131072,'num_predict':1024,'num_gpu':99}}

class PolicyTests(unittest.TestCase):
    def test_chat_and_notes_accepted_but_extra_authority_rejected(self):
        broker.validate_chat(request(),POLICY)
        notes=request();notes['format']='json';notes['options']['num_predict']=6000
        broker.validate_chat(notes,POLICY)
        for key,value in [('model','other'),('keep_alive',0),('think',True),('tools',[]),('images',[])]:
            bad=request();bad[key]=value
            with self.assertRaises(ValueError):broker.validate_chat(bad,POLICY)
        for key,value in [('num_ctx',262144),('num_predict',6001),('num_gpu',0),('temperature',float('nan')),('seed',1)]:
            bad=request();bad['options'][key]=value
            with self.assertRaises(ValueError):broker.validate_chat(bad,POLICY)
        for messages in ([],[{'role':'user','content':'x','images':[]}],[{'role':'tool','content':'x'}],[{'role':'user','content':'x'*64001}]):
            bad=request();bad['messages']=messages
            with self.assertRaises(ValueError):broker.validate_chat(bad,POLICY)

    def test_duplicate_fields_and_nonfinite_json_rejected(self):
        for raw in (b'{"model":"a","model":"b"}',b'{"temperature":NaN}',b'bad',b'\xff'):
            with self.assertRaises((ValueError,UnicodeError)):broker.decode(raw)

    def test_isolated_client_never_uses_tcp_when_socket_missing(self):
        with patch.dict('os.environ',{'LARPUS_ISOLATION':'wsl-podman'}),patch.object(local_ollama.os,'lstat',side_effect=FileNotFoundError),patch.object(local_ollama.HTTP,'open') as tcp:
            with self.assertRaises(ValueError):local_ollama.ollama('/api/tags')
            tcp.assert_not_called()

class TransportTests(unittest.TestCase):
    def test_routes_streams_and_framing_with_fake_upstream(self):
        calls=[]
        class Upstream(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                calls.append(self.path);body=json.dumps({'models':[{'name':POLICY['model']},{'name':'not-approved'}]}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            def do_POST(self):
                value=json.loads(self.rfile.read(int(self.headers['Content-Length'])));calls.append(value)
                body=(b'{"message":{"content":"Hi."},"done":false}\n{"done":true}\n' if value['stream'] else b'{"message":{"content":"Hi."},"done":true}')
                self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        upstream=ThreadingHTTPServer(('127.0.0.1',0),Upstream)
        server=ThreadingHTTPServer(('127.0.0.1',0),broker.Handler);server.approved=POLICY
        threads=[threading.Thread(target=s.serve_forever,daemon=True) for s in (upstream,server)]
        for thread in threads:thread.start()
        try:
            with patch.object(broker,'upstream_connection',side_effect=lambda timeout:http.client.HTTPConnection('127.0.0.1',upstream.server_port,timeout=timeout)):
                def send(method,path,body=None,headers=None):
                    conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                    conn.request(method,path,body,headers or {});response=conn.getresponse();result=(response.status,response.read());conn.close();return result
                for route in ('/api/pull','/api/create','/api/delete','/api/chat?override=1','http://example.org/api/chat'):
                    self.assertEqual(send('POST',route,'{}')[0],403)
                self.assertEqual(calls,[])
                status,raw=send('GET','/api/tags');self.assertEqual(status,200)
                self.assertEqual(json.loads(raw)['models'],[{'name':POLICY['model']}])
                status,raw=send('POST','/api/chat',json.dumps(request()));self.assertEqual(status,200)
                self.assertTrue(json.loads(raw)['done'])
                value=request();value['stream']=True
                status,raw=send('POST','/api/chat',json.dumps(value));self.assertEqual(status,200)
                self.assertEqual(len(raw.splitlines()),2)
                before=len(calls)
                self.assertEqual(send('POST','/api/chat','{}',{'Transfer-Encoding':'chunked'})[0],400)
                self.assertEqual(send('POST','/api/chat',None,{'Content-Length':str(broker.MAX_BODY+1)})[0],413)
                self.assertEqual(len(calls),before)
        finally:
            for s in (server,upstream):s.shutdown();s.server_close()
            for thread in threads:thread.join()

if __name__=='__main__':unittest.main()
