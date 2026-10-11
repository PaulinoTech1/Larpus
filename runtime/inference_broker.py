"""Private Unix HTTP boundary for approved local inference operations."""
import http.client
from http.server import BaseHTTPRequestHandler
import json
import math
import os
from pathlib import Path
import socketserver
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
SOCKET=Path('/run/larpus-broker/inference.sock')
MAX_BODY=524288
MAX_RESPONSE=2_000_000

def policy():
    value=json.loads((ROOT/'config/inference-broker.json').read_text(encoding='utf-8'))
    if set(value)!={'version','enabled','model','context','max_output'} or value['version']!=1 or value['enabled'] is not True:
        raise ValueError('Invalid broker policy')
    if value['model']!='qwen3.5:27b-q4_K_M' or value['context']!=131072 or value['max_output']!=6000:
        raise ValueError('Unreviewed broker policy')
    return value

def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate field')
        result[key]=value
    return result

def decode(raw):
    def invalid(value):raise ValueError('Nonfinite JSON')
    return json.loads(raw.decode('utf-8'),object_pairs_hook=unique,parse_constant=invalid)

def validate_chat(value,approved):
    required={'model','messages','stream','think','keep_alive','options'}
    if not isinstance(value,dict) or set(value)-{'format'}!=required or set(value)-required-{'format'}:
        raise ValueError('Unexpected chat fields')
    if value['model']!=approved['model'] or type(value['stream']) is not bool or value['think'] is not False or type(value['keep_alive']) is not int or value['keep_alive']!=-1:
        raise ValueError('Unapproved model controls')
    if 'format' in value and value['format']!='json':raise ValueError('Unapproved output format')
    options=value['options']
    if not isinstance(options,dict) or set(options)!={'temperature','num_ctx','num_predict','num_gpu'}:
        raise ValueError('Unexpected inference options')
    if type(options['num_ctx']) is not int or options['num_ctx']!=approved['context'] or type(options['num_gpu']) is not int or options['num_gpu']!=99:
        raise ValueError('Unapproved context or GPU controls')
    if type(options['num_predict']) is not int or not 1<=options['num_predict']<=approved['max_output']:
        raise ValueError('Unapproved output limit')
    temperature=options['temperature']
    if type(temperature) not in (int,float) or not math.isfinite(temperature) or not 0<=temperature<=1:
        raise ValueError('Unapproved temperature')
    messages=value['messages']
    if not isinstance(messages,list) or not 1<=len(messages)<=405:raise ValueError('Invalid messages')
    for index,message in enumerate(messages):
        if not isinstance(message,dict) or set(message)!={'role','content'} or message['role'] not in ('system','user','assistant'):
            raise ValueError('Unapproved message fields')
        if message['role']=='system' and index!=0:raise ValueError('Misplaced system message')
        content=message['content']
        if not isinstance(content,str) or not content or len(content.encode('utf-8'))>64000:
            raise ValueError('Invalid message content')
    if messages[-1]['role']!='user':raise ValueError('Expected user question')
    return value

def upstream_connection(timeout):
    return http.client.HTTPConnection('127.0.0.1',11434,timeout=timeout)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def setup(self):
        super().setup();self.connection.settimeout(10)
    def reply(self,status,value):
        body=json.dumps(value,separators=(',',':')).encode()
        self.send_response(status);self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)));self.send_header('Connection','close');self.end_headers()
        self.close_connection=True;self.wfile.write(body)
    def do_GET(self):self.route()
    def do_POST(self):self.route()
    def route(self):
        allowed={('GET','/api/tags'),('GET','/api/ps'),('POST','/api/chat')}
        if (self.command,self.path) not in allowed:return self.reply(403,{'error':'Operation not approved'})
        lengths=self.headers.get_all('Content-Length',[])
        if self.headers.get('Transfer-Encoding') is not None or len(lengths)>1:
            return self.reply(400,{'error':'Invalid framing'})
        try:
            body=None
            if self.command=='POST':
                if len(lengths)!=1 or not lengths[0].isascii() or not lengths[0].isdigit():raise ValueError('Missing length')
                size=int(lengths[0])
                if not 1<=size<=MAX_BODY:return self.reply(413,{'error':'Request too large'})
                raw=self.rfile.read(size)
                if len(raw)!=size:raise ValueError('Truncated request')
                body=validate_chat(decode(raw),self.server.approved)
            elif lengths and lengths!=['0']:raise ValueError('Unexpected body')
        except (ValueError,TypeError,KeyError,UnicodeError):return self.reply(400,{'error':'Request not approved'})
        self.connection.settimeout(930)
        upstream=upstream_connection(900 if body else 2)
        started=False
        try:
            upstream.request(self.command,self.path,body=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
            response=upstream.getresponse()
            if response.status!=200:return self.reply(502,{'error':'Local inference unavailable'})
            if body and body['stream']:
                self.send_response(200);self.send_header('Content-Type','application/x-ndjson');self.send_header('Connection','close');self.end_headers()
                self.close_connection=True;started=True;total=0;deadline=time.monotonic()+900
                for _ in range(8192):
                    line=response.readline(65537);total+=len(line)
                    if not line or len(line)>65536 or total>MAX_RESPONSE or time.monotonic()>deadline:raise ValueError('Invalid stream bounds')
                    frame=decode(line)
                    if not isinstance(frame,dict) or frame.get('error'):raise ValueError('Invalid frame')
                    self.wfile.write(json.dumps(frame,separators=(',',':')).encode()+b'\n');self.wfile.flush()
                    if frame.get('done') is True:return
                raise ValueError('Too many frames')
            raw=response.read(MAX_RESPONSE+1)
            if len(raw)>MAX_RESPONSE:raise ValueError('Response too large')
            value=decode(raw)
            if not isinstance(value,dict) or value.get('error'):raise ValueError('Invalid response')
            if body is None:
                if not isinstance(value.get('models'),list):raise ValueError('Invalid model status')
                value={'models':[item for item in value['models'] if isinstance(item,dict) and item.get('name')==self.server.approved['model']]}
            self.reply(200,value)
        except (OSError,ValueError,TypeError,http.client.HTTPException):
            if not started:
                try:self.reply(502,{'error':'Local inference unavailable'})
                except OSError:pass
        finally:upstream.close()

Server=None
if hasattr(socketserver,'UnixStreamServer'):
    class Server(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):
        daemon_threads=True
        def __init__(self,path,approved):
            self.approved=approved;self.slots=threading.BoundedSemaphore(16)
            super().__init__(str(path),Handler)
        def process_request(self,request,address):
            if not self.slots.acquire(blocking=False):request.close();return
            try:super().process_request(request,address)
            except BaseException:self.slots.release();raise
        def process_request_thread(self,request,address):
            try:super().process_request_thread(request,address)
            finally:self.slots.release()

if __name__=='__main__':
    if Server is None:raise SystemExit('Broker requires Unix sockets on Linux')
    approved=policy();os.umask(0o077)
    if SOCKET.parent.is_symlink() or SOCKET.is_symlink():raise SystemExit('Redirected broker socket')
    SOCKET.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if SOCKET.exists():SOCKET.unlink()
    with Server(SOCKET,approved) as server:
        os.chmod(SOCKET,0o600);server.serve_forever()
