"""Owner-only Serve bridge; never proxy the password-free localhost gateway."""
import argparse
from contextlib import closing
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
from pathlib import Path
import re
import ssl

ROOT=Path(__file__).resolve().parents[1]
MAX_BODY=4_000_000
HOP={'connection','keep-alive','proxy-authenticate','proxy-authorization',
     'te','trailer','transfer-encoding','upgrade'}


def settings(path, root=ROOT):
    cfg=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(cfg,dict) or set(cfg)!={'hostname','owner_login','port'}:
        raise ValueError('Expected hostname, owner_login and port')
    host=cfg['hostname']
    if not isinstance(host,str) or not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.ts\.net',host):
        raise ValueError('Use the exact lowercase PC DNS name from tailscale status')
    if not isinstance(cfg['owner_login'],str) or not cfg['owner_login'].strip() or any(ord(c)<33 or ord(c)>126 for c in cfg['owner_login']):
        raise ValueError('Use the exact ASCII owner login reported by Tailscale')
    if type(cfg['port']) is not int or not 1024<=cfg['port']<=65535:
        raise ValueError('Invalid loopback bridge port')
    active=json.loads((root/'data/releases/active.json').read_text(encoding='utf-8'))
    ip=ipaddress.IPv4Address(active['host'])
    private=[ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')]
    if not any(ip in n for n in private) or type(active['port']) is not int or not 1<=active['port']<=65535:
        raise ValueError('Active upstream must be the RFC1918 authenticated HTTPS listener')
    if cfg['port']==active['port']:
        raise ValueError('Bridge must use a separate port')
    context=ssl.create_default_context(cafile=str(root/'data/tls/ca.crt'))
    context.minimum_version=ssl.TLSVersion.TLSv1_2
    return {**cfg,'upstream':str(ip),'upstream_port':active['port'],'context':context}


def upstream(cfg):
    return http.client.HTTPSConnection(cfg['upstream'],cfg['upstream_port'],context=cfg['context'],timeout=900)


def preflight(cfg):
    with closing(upstream(cfg)) as conn:
        conn.request('GET','/api/personas')
        reply=conn.getresponse();reply.read()
        if reply.status!=401:
            raise ValueError('Upstream must require login (expected HTTP 401)')


class Bridge(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass  # No URLs, prompts, identity headers, passwords or cookies in logs.

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def deny(self,status):
        self.send_response(status)
        self.send_header('Content-Length','0')
        self.send_header('Cache-Control','no-store')
        self.send_header('Connection','close')
        self.end_headers();self.close_connection=True

    def relay(self):
        cfg=self.server.config
        if (self.headers.get_all('Host',[]) not in ([cfg['hostname']],[cfg['hostname']+':443'])
                or self.headers.get_all('Tailscale-User-Login',[])!=[cfg['owner_login']]):
            return self.deny(403)
        origins=self.headers.get_all('Origin',[])
        if origins and origins not in ([f"https://{cfg['hostname']}"],[f"https://{cfg['hostname']}:443"]):
            return self.deny(403)
        if self.command=='POST' and not origins:
            return self.deny(403)
        if not self.path.startswith('/') or self.path.startswith('//') or '\\' in self.path or any(ord(c)<32 for c in self.path):
            return self.deny(400)
        lengths=self.headers.get_all('Content-Length',[])
        if self.headers.get('Transfer-Encoding') or len(lengths)>1:
            return self.deny(400)
        try:
            size=int(lengths[0]) if lengths else 0
            if not 0<=size<=MAX_BODY or (self.command=='GET' and size):
                return self.deny(413)
        except ValueError:
            return self.deny(400)
        # Explicit allowlist: never forward client routing/identity/proxy headers.
        headers={k:self.headers[k] for k in ('Cookie','Content-Type','Accept') if k in self.headers}
        headers['Host']=f"{cfg['upstream']}:{cfg['upstream_port']}"
        if origins:headers['Origin']='https://'+headers['Host']
        body=self.rfile.read(size) if size else None
        if body is not None and len(body)!=size:
            return self.deny(400)
        sent=False
        try:
            with closing(upstream(cfg)) as conn:
                conn.request(self.command,self.path,body=body,headers=headers)
                reply=conn.getresponse()
                self.send_response(reply.status)
                connection_tokens={s.strip().lower() for s in (reply.getheader('Connection') or '').split(',')}
                for name,value in reply.getheaders():
                    if name.lower() not in HOP|connection_tokens|{'server','date'}:
                        self.send_header(name,value)
                self.send_header('Connection','close')
                self.end_headers();sent=True;self.close_connection=True
                while True:
                    chunk=reply.read1(65536)
                    if not chunk:break
                    self.wfile.write(chunk);self.wfile.flush()
        except (OSError,http.client.HTTPException):
            if not sent:self.deny(502)
            self.close_connection=True

    do_GET=relay
    do_POST=relay


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'data/tailscale/bridge.json')
    parser.add_argument('--check',action='store_true',help='Verify config, CA and required upstream login only')
    args=parser.parse_args()
    try:
        cfg=settings(args.config);preflight(cfg)
        if args.check:
            print('Ready locally: verified HTTPS upstream requires login. Remote access not tested.');return
        with ThreadingHTTPServer(('127.0.0.1',cfg['port']),Bridge) as server:
            server.config=cfg
            print(f"Bridge on 127.0.0.1:{cfg['port']}; Serve hostname {cfg['hostname']}. Ctrl+C stops bridge.",flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except (OSError,ValueError,KeyError,TypeError,http.client.HTTPException) as exc:
        parser.exit(1,'Tailscale bridge: '+str(exc)+'\n')


if __name__=='__main__':main()
