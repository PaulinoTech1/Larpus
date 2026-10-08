"""Local UI gateway with optional explicitly scoped LAN access."""
import ipaddress
import json
import os
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from runtime.agents import ROOT, load_personas, messages_for
from runtime.auth import Auth, PASSWORD_FILE, FAILURE
from runtime.text_filter import TextHeld
from runtime.mcp_client import chat as mcp_chat, health as mcp_health
from runtime.skills import summaries

WEB = ROOT / 'web'
PERSONAS = load_personas()
LOCK = threading.Lock()
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
        scheme = 'https' if getattr(self.server, 'tls', False) else 'http'
        if origin and origin not in {f'{scheme}://{h}' for h in hosts}:
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
            return self.reply(200, {'personas': [{k:p.get(k,[]) for k in ('id','name','description','model','skills')} for p in PERSONAS.values()],'skills':summaries()})
        if path == '/api/health':
            try:
                self.reply(200, mcp_health())
            except OSError:
                self.reply(503, {'error':'Local MCP unavailable. No direct inference fallback.'})
            return
        if path == '/api/station-health':
            from runtime.health import read_latest
            return self.reply(200,read_latest())
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
            if not isinstance(data, dict) or not {'persona','messages'}.issubset(data) or set(data)-{'persona','messages','skill'}:
                raise ValueError('Expected persona and messages')
            persona = PERSONAS.get(data['persona']) if isinstance(data['persona'], str) else None
            if persona is None:
                raise ValueError('Unknown persona')
            messages = messages_for(persona, data['messages'],data.get('skill'))
        except TextHeld as exc:
            return self.reply(503 if exc.unavailable else 422, {
                'error':'Text held by the local input filter. Remove hidden controls or instruction overrides and try again.',
                'reason':exc.reason, 'message_index':exc.index,
            })
        except (ValueError, TypeError):
            return self.reply(400, {'error': 'Invalid chat request. Use a known persona and alternating messages, up to 8000 characters each.'})
        if not LOCK.acquire(blocking=False):
            return self.reply(409, {'error': 'Inference busy. Try again shortly.'})
        try:
            result = mcp_chat(data['persona'], data['messages'],data.get('skill'))
            status = result.pop('status', 502)
            self.reply(status, result)
        except (OSError, ValueError, KeyError, TypeError):
            self.reply(502, {'error':'Local MCP unavailable or invalid response. No direct inference fallback.'})
        finally:
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
        stop_monitor = start_monitor()
        try:
            server.serve_forever()
        finally:
            stop_monitor.set()
            if lan is not None:
                local.shutdown()
    finally:
        for listener in servers:
            listener.server_close()

if __name__ == '__main__':
    main()
