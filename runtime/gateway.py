"""Local UI gateway with optional explicitly scoped LAN access."""
import ipaddress
import json
import os
import socket
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from runtime.agents import ROOT, load_personas, messages_for
from runtime.auth import Auth, PASSWORD_FILE, FAILURE

WEB = ROOT / 'web'
PERSONAS = load_personas()
LOCK = threading.Lock()
# Disable proxy inheritance: inference must go directly to host loopback.
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.URLError('Inference redirects are disabled')

HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
OLLAMA = 'http://127.0.0.1:11434'

def ollama(path, payload=None, timeout=120):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA + path, data=data, headers={'Content-Type': 'application/json'})
    with HTTP.open(req, timeout=timeout) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('Model response too large')
        return json.loads(raw)

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
        self.send_header('Content-Length', str(size))
        self.send_header('Cache-Control', 'no-store')
        for key,value in (extra or {}).items():
            self.send_header(key,value)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
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
        if origin and origin not in {f'http://{h}' for h in hosts}:
            self.reply(403, {'error': 'Same origin required'})
            return False
        return True

    def do_GET(self):
        if not self.trusted():
            return
        path = urlsplit(self.path).path
        if path not in ('/login','/login.js','/style.css') and not self.authorized():
            if path.startswith('/api/'):
                return self.reply(401, {'error':'Password required'})
            self.headers_out(302,'text/plain',0,{'Location':'/login'})
            return
        if path == '/login':
            path = '/login.html'
        if path == '/api/personas':
            return self.reply(200, {'personas': [{k:p[k] for k in ('id','name','description','model')} for p in PERSONAS.values()]})
        if path == '/api/health':
            try:
                tags = ollama('/api/tags', timeout=2)
                self.reply(200, {'ollama': 'online', 'models': [m['name'] for m in tags['models']], 'voice': 'stub'})
            except (OSError, ValueError, KeyError, TypeError):
                self.reply(200, {'ollama': 'offline', 'models': [], 'voice': 'stub'})
            return
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
                return self.reply(200,{'ok':True},{'Set-Cookie':f'larpus_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'})
            return self.reply(status,{'error':FAILURE}, {'Retry-After':'60'} if status==429 else None)
        if not self.authorized():
            return self.reply(401,{'error':'Password required'})
        if self.path == '/api/logout':
            self.server.auth.logout(self.session_key)
            return self.reply(200,{'ok':True},{'Set-Cookie':'larpus_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
        if not self.server.auth.allowed(('api',self.client_address[0]),30,60):
            return self.reply(429,{'error':'Too many requests. Try again shortly.'},{'Retry-After':'60'})
        if self.path not in ('/api/chat', '/api/voice'):
            return self.reply(404, {'error': 'Not found'})
        if self.path == '/api/voice':
            return self.reply(501, {'error': 'Voice pipeline is a stub. Microphone capture is not enabled yet.'})
        try:
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('JSON required')
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 65536:
                raise ValueError('Request must be 1–65536 bytes')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict) or set(data) != {'persona', 'messages'}:
                raise ValueError('Expected persona and messages')
            persona = PERSONAS.get(data['persona']) if isinstance(data['persona'], str) else None
            if persona is None:
                raise ValueError('Unknown persona')
            messages = messages_for(persona, data['messages'])
        except (ValueError, TypeError):
            return self.reply(400, {'error': 'Invalid chat request. Use a known persona and alternating messages, up to 8000 characters each.'})
        if not LOCK.acquire(blocking=False):
            return self.reply(409, {'error': 'Inference busy. Try again shortly.'})
        try:
            result = ollama('/api/chat', {'model': persona['model'], 'messages': messages, 'stream': False, 'options': {'temperature': persona['temperature'], 'num_ctx': 4096, 'num_predict': 1024}})
            content = result['message']['content']
            if not isinstance(content, str) or not content.strip():
                raise ValueError('Empty response')
            self.reply(200, {'content': content, 'model': persona['model']})
        except (OSError, ValueError, KeyError, TypeError):
            self.reply(502, {'error': 'Local Ollama unavailable or model missing. Start Ollama and install the persona model; no cloud fallback is used.'})
        finally:
            LOCK.release()

    def authorized(self):
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
    server = ThreadingHTTPServer((host, port), Handler)
    server.lan_network = lan
    server.auth = auth
    server.timeout = 5
    print(f'larpus: http://{host}:{port} (local development runtime)', flush=True)
    server.serve_forever()

if __name__ == '__main__':
    main()
