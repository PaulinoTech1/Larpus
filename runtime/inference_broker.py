"""Private Unix HTTP boundary for approved local inference operations."""
import http.client
import hashlib
from http.server import BaseHTTPRequestHandler
import json
import math
import os
from pathlib import Path
import socketserver
import threading
import time
from runtime.broker_scheduler import Scheduler,Refused,LIMITS

ROOT=Path(__file__).resolve().parents[1]
SOCKET=Path('/run/larpus-broker/inference.sock')
NOTES_SOCKET=Path('/run/larpus-notes/inference.sock')
MAX_BODY=524288
MAX_RESPONSE=2_000_000

def generation_body(body,lane):
    options=dict(body['options'])
    # Only approved ordinary-chat system templates carry this marker. Summary
    # and notes templates retain their existing sampling. Clients cannot add
    # these options through the strict request schema.
    if lane=='chat' and 'CONVERSATION PROGRESS:' in body['messages'][0]['content']:
        options.update(repeat_last_n=4096,repeat_penalty=1.1)
    return dict(body,options=options,stream=True)

def policy():
    value=json.loads((ROOT/'config/inference-broker.json').read_text(encoding='utf-8'))
    if set(value)-{'selection_enabled'}!={'version','enabled','model','context','max_output'} or value['version']!=2 or value['enabled'] is not True:
        raise ValueError('Invalid broker policy')
    if value['model']!='larpus3.8:27b-q4' or value['context']!=131072 or value['max_output']!=6000:
        raise ValueError('Unreviewed broker policy')
    return value

def selected_policy(approved):
    if not approved.get('selection_enabled'):return dict(approved,switching=False)
    from runtime import model_selection as selection
    state=selection.read_selection()
    return dict(approved,model=selection.model(state['active_id'])['tag'],switching=selection.is_switching(state))

def selected_body(value,policy):
    approved=selected_policy(policy)
    if approved['switching']:raise Refused(503,'model_switching')
    return validate_chat(value,approved)
def ensure_selected(policy,body):
    approved=selected_policy(policy)
    if approved['switching'] or approved['model']!=body['model']:raise Refused(503,'model_switching')
def selected_status(value,policy):
    if not isinstance(value.get('models'),list):raise ValueError('Invalid model status')
    approved=selected_policy(policy)
    result={'models':[m for m in value['models'] if isinstance(m,dict) and m.get('name')==approved['model']]}
    if policy.get('selection_enabled'):result.update(active_model=approved['model'],switching=approved['switching'])
    return result

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

def prompt_manifest():
    value=decode((ROOT/'config/broker-prompts.json').read_bytes())
    if set(value)!={'version','chat','notes'} or value['version']!=1:raise ValueError('Invalid prompt manifest')
    for lane in ('chat','notes'):
        if not isinstance(value[lane],list) or not 1<=len(value[lane])<=1000:raise ValueError('Invalid prompt hashes')
        if any(not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h) for h in value[lane]):raise ValueError('Invalid hash')
    return value

def validate_lane(body,lane,prompts):
    messages=body['messages']
    if messages[0]['role']!='system' or hashlib.sha256(messages[0]['content'].encode()).hexdigest() not in prompts[lane]:
        raise Refused(403,'system_template_denied')
    if body['options']['num_predict']>LIMITS[lane]['output']:raise Refused(403,'lane_output_denied')
    if lane=='notes' and (len(messages)!=2 or body.get('format')!='json' or body['stream']):raise Refused(403,'notes_scope_denied')
    if any(m['role']!=('user' if n%2 else 'assistant') for n,m in enumerate(messages[1:],1)):
        raise Refused(403,'message_order_denied')

def idle_fence(approved):
    """A completed one-token request fences the pinned parallel=1 runner after abort."""
    connection=upstream_connection(2);timer=None
    try:
        connection.connect();sock=connection.sock
        def abort():
            try:sock.shutdown(2)
            except OSError:pass
        timer=threading.Timer(8,abort);timer.daemon=True;timer.start();sock.settimeout(8)
        payload={'model':approved['model'],'messages':[{'role':'user','content':'Ready.'}],
                 'stream':False,'think':False,'keep_alive':-1,
                 'options':{'temperature':0,'num_ctx':approved['context'],'num_predict':1,'num_gpu':99}}
        connection.request('POST','/api/chat',json.dumps(payload),{'Content-Type':'application/json'})
        response=connection.getresponse();raw=response.read(8193)
        if response.status!=200 or len(raw)>8192:return False
        value=decode(raw)
        return isinstance(value,dict) and value.get('done') is True and type(value.get('eval_count')) is int and 0<=value['eval_count']<=1
    except (OSError,ValueError,TypeError,http.client.HTTPException):return False
    finally:
        if timer:timer.cancel()
        connection.close()

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
        if self.server.approved['version']==2 and (self.command,self.path)==('GET','/broker/state'):
            if self.headers.get('Transfer-Encoding') is not None or self.headers.get_all('Content-Length',[]) not in ([],['0']):return self.reply(400,{'error':'Invalid framing'})
            try:self.server.scheduler.status_budget()
            except Refused as exc:return self.reply(exc.status,{'error':'Status held','code':exc.code})
            return self.reply(200,self.server.scheduler.snapshot())
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
                body=selected_body(decode(raw),self.server.approved)
            elif lengths and lengths!=['0']:raise ValueError('Unexpected body')
        except Refused as exc:return self.reply(exc.status,{'error':'Model switch in progress','code':exc.code})
        except (ValueError,TypeError,KeyError,UnicodeError):return self.reply(400,{'error':'Request not approved'})
        if self.server.approved['version']==2:
            try:
                if body is None:self.server.scheduler.status_budget()
                else:
                    validate_lane(body,self.server.lane,self.server.prompts)
                    return self.managed_chat(body)
            except Refused as exc:return self.reply(exc.status,{'error':'Inference request held','code':exc.code})
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
            if body is None:value=selected_status(value,self.server.approved)
            self.reply(200,value)
        except (OSError,ValueError,TypeError,http.client.HTTPException):
            if not started:
                try:self.reply(502,{'error':'Local inference unavailable'})
                except OSError:pass
        finally:upstream.close()

    def managed_chat(self,body):
        started=False;scheduler=self.server.scheduler
        try:
            with scheduler.slot(self.server.lane,body['options']['num_predict'],admit=lambda:ensure_selected(self.server.approved,body)) as job:
                upstream=upstream_connection(5)
                try:
                    upstream.connect();job.bind(upstream.sock);upstream.sock.settimeout(LIMITS[job.lane]['seconds'])
                    upstream.request('POST','/api/chat',json.dumps(generation_body(body,self.server.lane)),{'Content-Type':'application/json'})
                    response=upstream.getresponse()
                    if response.status!=200:raise OSError('Upstream unavailable')
                    self.connection.settimeout(5)
                    if body['stream']:
                        self.send_response(200);self.send_header('Content-Type','application/x-ndjson');self.send_header('Connection','close');self.end_headers()
                        started=True;self.close_connection=True
                    total=0;content='';final=None
                    for _ in range(8192):
                        line=response.readline(65537);total+=len(line)
                        if job.reason:raise Refused(409,job.reason)
                        if not line or len(line)>65536 or total>MAX_RESPONSE:raise ValueError('Invalid stream bounds')
                        frame=decode(line)
                        if not isinstance(frame,dict) or frame.get('error'):raise ValueError('Invalid upstream frame')
                        job.received=True
                        delta=frame.get('message',{}).get('content','')
                        if not isinstance(delta,str):raise ValueError('Invalid content')
                        if body['stream']:
                            self.wfile.write(json.dumps(frame,separators=(',',':')).encode()+b'\n');self.wfile.flush()
                        else:content+=delta
                        if frame.get('done') is True:final=frame;break
                    if final is None:raise ValueError('Incomplete upstream response')
                    if job.reason:raise Refused(409,job.reason)
                    if not body['stream']:
                        final=dict(final,message={'role':'assistant','content':content})
                except (OSError,ValueError,TypeError,http.client.HTTPException) as exc:
                    if job.reason:raise Refused(409 if job.reason=='background_preempted' else 503,job.reason) from exc
                    raise
                finally:upstream.close()
            if not body['stream']:self.reply(200,final)
        except Refused as exc:
            if not started:self.reply(exc.status,{'error':'Inference request held','code':exc.code})
        except (OSError,ValueError,TypeError,http.client.HTTPException):
            if not started:self.reply(502,{'error':'Local inference unavailable','code':'inference_interrupted'})

Server=None
if hasattr(socketserver,'UnixStreamServer'):
    class Server(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):
        daemon_threads=True
        def __init__(self,path,approved,lane,prompts,scheduler):
            self.approved=approved;self.slots=threading.BoundedSemaphore(16)
            self.lane=lane;self.prompts=prompts;self.scheduler=scheduler
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
    approved=policy();prompts=prompt_manifest();os.umask(0o077)
    scheduler=Scheduler(lambda:idle_fence(selected_policy(approved)))
    servers=[]
    for lane,path in (('chat',SOCKET),('notes',NOTES_SOCKET)):
        if path.parent.is_symlink() or path.is_symlink():raise SystemExit('Redirected broker socket')
        path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        if path.exists():path.unlink()
        server=Server(path,approved,lane,prompts,scheduler);os.chmod(path,0o600);servers.append(server)
    threading.Thread(target=servers[1].serve_forever,daemon=True).start()
    with servers[0]:servers[0].serve_forever()
