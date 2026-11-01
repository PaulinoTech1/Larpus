"""Local UI gateway with optional explicitly scoped LAN access."""
from runtime.diagnostics import catalog_failure, report
import ipaddress
import json
import os
import secrets
import ssl
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from runtime.agents import ROOT, CatalogRejected, load_personas, prepare_conversation, persona_rejections, require_persona, skill_rejections, summaries
from runtime.auth import Auth, PASSWORD_FILE, FAILURE
from runtime.text_filter import TextHeld
from runtime.execution_profiles import resolve, to_wire
from runtime.mcp_client import chat as mcp_chat, health as mcp_health, stream_chat as mcp_stream
from runtime.inference_admission import Admission, Busy

WEB = ROOT / 'web'
PERSONAS = load_personas()
LOCK = threading.Lock()
ADMISSION=Admission(ROOT/'data/inference-admission')
DRAIN=ROOT/'release-state/drain'
def execution_kwargs(data):
    context=to_wire(resolve(data.get('execution')))
    return {'execution':context} if 'execution' in data else {}

def validate_chat_request(data):
    if not isinstance(data, dict) or not {'persona','messages'}.issubset(data) or set(data)-{'persona','messages','skill','speak','execution'}:
        raise ValueError('Expected persona and messages')
    if 'speak' in data and type(data['speak']) is not bool:
        raise ValueError('Invalid speech flag')
    execution=execution_kwargs(data)
    persona = require_persona(data['persona'])
    kept,info=prepare_conversation(persona, data['messages'],data.get('skill'))
    data['messages']=kept
    data['_horizon']=info
    return execution

def add_queue_timing(result,execution,elapsed):
    if execution.get('execution',{}).get('profile')=='diagnostic':
        result.setdefault('timing_ms',{})['gateway_queue']=round(elapsed*1000,3)
    return result

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Do not log prompts or request URLs.

    def reply(self, status, obj, extra=None):
        body = json.dumps(obj).encode()
        self.headers_out(status, 'application/json', len(body), extra)
        self.wfile.write(body)

    def headers_out(self, status, mime, size, extra=None):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        if size is not None:
            self.send_header('Content-Length', str(size))
        else:
            self.send_header('Connection','close')
            self.close_connection=True
        self.send_header('Cache-Control', 'no-store')
        for key,value in (extra or {}).items():
            self.send_header(key,value)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; media-src 'self' blob:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()

    def trusted(self):
        port = self.server.server_port
        hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        lan = getattr(self.server, 'lan_network', None)
        if lan is not None:
            hosts.add(f'{self.server.server_address[0]}:{port}')
            peer = ipaddress.ip_address(self.client_address[0])
            if not peer.is_loopback and peer not in lan:
                self.reply(403, {'error': 'Home LAN clients only'})
                return False
        if self.headers.get('Host') not in hosts:
            self.reply(403, {'error': 'Configured local host required'})
            return False
        origin = self.headers.get('Origin')
        scheme = 'https' if getattr(self.server, 'tls', False) else 'http'
        if origin and origin not in {f'{scheme}://{h}' for h in hosts}:
            self.reply(403, {'error': 'Same origin required'})
            return False
        return True

    def startup_ready(self):
        gate=os.environ.get('LARPUS_STARTUP_GATE')
        if not gate:return True
        path=Path(gate)
        return not path.is_symlink() and path.is_file()

    def authorize_get(self,path):
        if path in ('/login','/login.js','/style.css'):return True
        if not self.authorized():
            if path.startswith('/api/'):self.reply(401,{'error':'Password required'})
            else:self.headers_out(302,'text/plain',0,{'Location':'/login'})
            return False
        if path.startswith('/api/') and path!='/api/station-health' and not self.startup_ready():
            self.reply(503,{'error':'Station startup checks are still running.'},{'Retry-After':'5'})
            return False
        return True

    def do_GET(self):
        if not self.trusted():
            return
        path = urlsplit(self.path).path
        if not self.authorize_get(path):return
        if path == '/login':
            path = '/login.html'
        if path == '/api/personas':
            try:current=load_personas();listed=summaries()
            except CatalogRejected as exc:body=catalog_failure(exc);return self.reply(body.pop('status'),body)
            return self.reply(200, {'personas': [{k:p.get(k,[]) for k in ('id','name','description','model','skills')} for p in current.values()],'skills':listed,'rejected':{'personas':persona_rejections(),'skills':skill_rejections()}})
        if path == '/api/health':
            try:
                self.reply(200, mcp_health())
            except OSError:
                self.reply(503, {'error':'Local MCP unavailable. No direct inference fallback.'})
            return
        from runtime.model_routes import extra_get
        if extra_get(self,path):return
        if path == '/assets/torus.gif' and (ROOT / 'assets/torus.gif').is_file():
            body = (ROOT / 'assets/torus.gif').read_bytes()
            self.headers_out(200, 'image/gif', len(body))
            self.wfile.write(body)
            return
        file = (WEB / ('index.html' if path == '/' else path.lstrip('/'))).resolve()
        if not file.is_relative_to(WEB.resolve()) or not file.is_file():
            return self.reply(404, {'error': 'Not found'})
        import mimetypes
        body = file.read_bytes()
        self.headers_out(200, mimetypes.guess_type(file.name)[0] or 'application/octet-stream', len(body))
        self.wfile.write(body)

    def do_POST(self):
        if not self.trusted():
            return
        if self.path == '/api/login':
            try:
                data = self.read_json(2048)
                password = data.get('password') if isinstance(data,dict) else None
            except (ValueError,TypeError):
                password = None
            status,token = self.server.auth.login(self.client_address[0],password)
            if token:
                return self.reply(200,{'ok':True},{'Set-Cookie':f'larpus_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800' + ('; Secure' if getattr(self.server, 'tls', False) else '')})
            return self.reply(status,{'error':FAILURE}, {'Retry-After':'60'} if status==429 else None)
        if not self.authorized():
            return self.reply(401,{'error':'Password required'})
        if self.path == '/api/logout':
            self.server.auth.logout(self.session_key)
            return self.reply(200,{'ok':True},{'Set-Cookie':'larpus_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0' + ('; Secure' if getattr(self.server, 'tls', False) else '')})
        if not self.server.auth.allowed(('api',self.client_address[0]),30,60):
            return self.reply(429,{'error':'Too many requests. Try again shortly.'},{'Retry-After':'60'})
        if self.path not in ('/api/chat', '/api/chat/stream', '/api/voice', '/api/context/compress', '/api/model-selection', '/api/retrieval-pipeline'):
            return self.reply(404, {'error': 'Not found'})
        from runtime.model_routes import before_post
        if before_post(self,DRAIN):return
        if self.path == '/api/context/compress':
            from runtime.context import compression_messages
            try:
                data=self.read_json(262144)
                if not isinstance(data,dict) or set(data)!={'persona','prior','fragments'} or require_persona(data['persona']) is None:raise ValueError('Invalid compression request')
                messages=compression_messages(data['prior'],data['fragments'])
            except TextHeld:
                return self.reply(422,{'error':'Compression input held by local filtering. Original chat retained.'})
            except CatalogRejected as exc:body=catalog_failure(exc);return self.reply(body.pop('status'),body)
            except (ValueError,TypeError,KeyError):
                return self.reply(400,{'error':'Invalid or oversized compression batch.'})
            if not LOCK.acquire(blocking=False):return self.reply(409,{'error':'Inference busy. Try again shortly.'})
            ticket=ADMISSION.interactive()
            try:ticket.__enter__()
            except (Busy,OSError):
                LOCK.release()
                return self.reply(503,{'error':'Waiting for local background inference. Retry shortly.'},{'Retry-After':'5'})
            try:
                result=mcp_chat(data['persona'],messages)
                status=result.pop('status',502)
                return self.reply(status,result)
            except (OSError,ValueError,KeyError,TypeError):
                return self.reply(502,{'error':'Local compression unavailable. Original chat retained.'})
            finally:
                ticket.__exit__(None,None,None)
                LOCK.release()
        if self.path == '/api/voice':
            try:
                from runtime.voice import call
                data = self.read_json(1400000)
                if isinstance(data,dict) and set(data)=={'action','text'} and data['action']=='synthesize':
                    from runtime.text_filter import inspect_message
                    from runtime.dlp import inspect_output
                    text=data['text']
                    if not isinstance(text,str) or not text.strip() or len(text)>2200:
                        raise ValueError('Invalid speech text')
                    inspect_message(text)
                    # Replays are client-supplied text, not trusted agent output.
                    # Fail closed before TTS; generated replies still use isolated DLP.
                    if inspect_output(text,system_prompt='\n'.join(p['system_prompt'] for p in load_personas().values())):
                        return self.reply(422,{'error':'Speech held by local output DLP.'})
                    return self.reply(200,call({'action':'synthesize','text':text}))
                if not isinstance(data,dict) or set(data)!={'action','audio'} or data['action']!='transcribe' or not isinstance(data['audio'],str):
                    raise ValueError('Expected a bounded audio request')
                result=call(data)
                phrase=result['transcript'].lower().rstrip('.!?').strip()
                confirmation=None
                if phrase in ('larpus mute','mute voice'):
                    confirmation='Microphone muted. Even I know when to stop talking.'
                elif phrase=='larpus reset chat':
                    confirmation='Fresh conversation. A clean slate, without the chalk dust.'
                elif phrase.startswith('larpus switch to '):
                    selected=next((p for p in load_personas().values() if p['name'].lower()==phrase[17:]),None)
                    if selected:
                        confirmation='Switching to '+selected['name']+'. Let us get into character.'
                if confirmation:
                    try:
                        result.update(call({'action':'synthesize','text':confirmation}))
                    except OSError:
                        result['voice_error']='Local speech unavailable.'
                return self.reply(200,result)
            except TextHeld:
                return self.reply(422,{'error':'Speech held by local text filter.'})
            except CatalogRejected as exc:body=catalog_failure(exc);return self.reply(body.pop('status'),body)
            except (ValueError,TypeError):
                return self.reply(400,{'error':'Invalid voice request. Use mono 16 kHz PCM WAV, at most 30 seconds.'})
            except OSError:
                return self.reply(503,{'error':'Local voice worker unavailable. No cloud fallback.'})
        try:
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('JSON required')
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 524288:
                raise ValueError('Request must be 1-524288 bytes')
            data = json.loads(self.rfile.read(size))
            execution=validate_chat_request(data)
            horizon=data.pop('_horizon',{'classified':[],'removed':[],'local':False})
        except TextHeld as exc:
            return self.reply(503 if exc.unavailable else 422, {
                'error':'Text held by the local input filter. Remove hidden controls, instruction overrides, or blocked prompt text and try again.',
                'reason':exc.reason, 'message_index':exc.index,
            })
        except CatalogRejected as exc:body=catalog_failure(exc);return self.reply(body.pop('status'),body)
        except (ValueError, TypeError):
            return self.reply(400, {'error': 'Invalid chat request. Use a known persona and alternating messages, up to 8000 characters each.'})
        if horizon['local']:
            notice={'removed':horizon['removed'],'incidents':[item['incident'] for item in horizon['classified']]}
            if self.path=='/api/chat/stream':
                self.headers_out(200,'application/x-ndjson',None,{'X-Accel-Buffering':'no'})
                for event in ({'type':'quarantine',**notice},{'type':'done','local':True,'sources':[]}):
                    self.wfile.write((json.dumps(event)+'\n').encode())
                self.wfile.flush()
                return
            return self.reply(200,{'content':'That message was set aside and was not sent onward.','quarantine':notice})
        if not LOCK.acquire(blocking=False):
            return self.reply(409, {'error': 'Inference busy. Try again shortly.'})
        ticket=ADMISSION.interactive()
        admission_started=time.perf_counter()
        try:ticket.__enter__()
        except (Busy,OSError):
            LOCK.release()
            return self.reply(503,{'error':'Waiting for local background inference. Retry shortly.'},{'Retry-After':'5'})
        admission_ms=time.perf_counter()-admission_started
        try:
            if self.path=='/api/chat/stream':
                self.headers_out(200,'application/x-ndjson',None,{'X-Accel-Buffering':'no'})
                def event(value):
                    self.wfile.write((json.dumps(value)+'\n').encode());self.wfile.flush()
                try:
                    if horizon['removed']:
                        event({'type':'quarantine','removed':horizon['removed'],'incidents':[item['incident'] for item in horizon['classified']]})
                    result=mcp_stream(data['persona'],data['messages'],data.get('skill'),lambda text:event({'type':'text','content':text}),**execution)
                    add_queue_timing(result,execution,admission_ms)
                    if result.get('status')==200:
                        event({'type':'done','sources':result.get('sources',[]),**{key:result[key] for key in ('context','citation_check','timing_ms','execution_trace_ms','execution_stages_ms','mcp_parent_stages_ms','execution') if key in result}})
                    else:
                        event({'type':'error','error':result.get('error','Response withheld.'),'code':result.get('code'),'error_id':result.get('error_id')})
                except (OSError,ValueError,KeyError,TypeError) as exc:
                    error_id=getattr(exc,'error_id',None) or report('LARP-MCP-STREAM',exc)
                    try:
                        event({'type':'error','error':'Local stream interrupted. The partial reply is incomplete.','error_id':error_id})
                    except OSError:
                        pass  # Browser disconnected; never start another HTTP response.
                return
            result = mcp_chat(data['persona'], data['messages'],data.get('skill'),**execution)
            if horizon['removed']:
                result['quarantine']={'removed':horizon['removed'],'incidents':[item['incident'] for item in horizon['classified']]}
            add_queue_timing(result,execution,admission_ms)
            status = result.pop('status', 502)
            if status == 200 and data.get('speak'):
                # MCP only returns generated content after isolated output DLP approves it.
                from runtime.voice import call
                try:
                    text = result['content']
                    if len(text)>2000:
                        text=text[:2000]+' The rest is displayed in the conversation.'
                    result.update(call({'action':'synthesize','text':text}))
                except OSError:
                    result['voice_error']='Reply is shown; local speech is unavailable.'
            self.reply(status, result)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            error_id=getattr(exc,'error_id',None) or report('LARP-MCP-UNAVAILABLE',exc)
            self.reply(502, {'error':'Local MCP unavailable or invalid response. No direct inference fallback.','error_id':error_id})
        finally:
            ticket.__exit__(None,None,None)
            LOCK.release()

    def authorized(self):
        if getattr(self.server, 'local_auth_bypass', False) and not getattr(self.server, 'tls', False) and ipaddress.ip_address(self.server.server_address[0]).is_loopback and ipaddress.ip_address(self.client_address[0]).is_loopback:
            self.session_key = None
            return True
        self.session_key=self.server.auth.session(self.headers.get('Cookie'))
        return self.session_key is not None

    def read_json(self, maximum):
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':
            raise ValueError('JSON required')
        size=int(self.headers.get('Content-Length','0'))
        if not 0<size<=maximum:
            raise ValueError('Invalid body size')
        return json.loads(self.rfile.read(size))

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

def main():
    try:
        auth = Auth(json.loads(PASSWORD_FILE.read_text(encoding='utf-8')))
    except (OSError, ValueError, KeyError, TypeError):
        raise SystemExit('Password required. Run: python -m runtime.auth')
    port = int(os.environ.get('LARPUS_PORT', '8080'))
    host = os.environ.get('LARPUS_HOST', '127.0.0.1')
    address = ipaddress.IPv4Address(host)
    lan = None
    if not address.is_loopback:
        private_ranges = [ipaddress.ip_network(c) for c in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')]
        lan = ipaddress.IPv4Network(os.environ.get('LARPUS_LAN_CIDR', ''), strict=True)
        if not any(address in n and lan.subnet_of(n) for n in private_ranges) or address not in lan:
            raise ValueError('LAN bind and subnet must be matching RFC1918 private addresses')
    servers = []
    try:
        if lan is not None:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(str(ROOT/'data/tls/server.crt'), str(ROOT/'data/tls/server.key'))
            local = ThreadingHTTPServer(('127.0.0.1', port), Handler)
            local.lan_network = None
            local.tls = False
            local.local_auth_bypass = True
            local.auth = auth
            servers.append(local)
            server = ThreadingHTTPServer((host, port), Handler)
            servers.append(server)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            server.tls = True
            server.lan_network = lan
            server.auth = auth
            threading.Thread(target=local.serve_forever, daemon=True).start()
            print(f'larpus local: http://127.0.0.1:{port}', flush=True)
        else:
            server = ThreadingHTTPServer((host, port), Handler)
            servers.append(server)
            server.lan_network = None
            server.tls = False
            server.local_auth_bypass = True
            server.auth = auth
        scheme = 'https' if server.tls else 'http'
        print(f'larpus: {scheme}://{host}:{port}', flush=True)
        from runtime.health import start_monitor
        stop_monitor = start_monitor(generation={'release_id':ROOT.name,'pid':os.getpid(),'token':secrets.token_hex(16)})
        def drain_when_requested():
            while not stop_monitor.wait(.25):
                if DRAIN.exists():
                    server.shutdown()
                    return
        threading.Thread(target=drain_when_requested,daemon=True,name='larpus-release-drain').start()
        from runtime.horizon_guard import install, shutdown
        install()
        try:
            server.serve_forever()
        finally:
            shutdown()
            stop_monitor.set()
            if lan is not None:
                local.shutdown()
    finally:
        for listener in servers:
            listener.server_close()

if __name__ == '__main__':
    main()
