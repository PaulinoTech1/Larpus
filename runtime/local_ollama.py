"""The only inference network adapter: fixed numeric loopback, no redirects."""
import json
import http.client
import os
from pathlib import Path
import socket
import stat
from contextlib import contextmanager
import time
import urllib.error
import urllib.request

OLLAMA = 'http://127.0.0.1:11434'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.URLError('Inference redirects are disabled')

HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

BROKER_SOCKET='/run/larpus-broker/inference.sock'

@contextmanager
def local_response(request,timeout):
    if os.environ.get('LARPUS_ISOLATION')=='host':
        with HTTP.open(request,timeout=timeout) as response:yield response
        return
    policy=Path(__file__).resolve().parents[1]/'config/inference-broker.json'
    configured=json.loads(policy.read_text(encoding='utf-8'))
    if configured.get('version')!=1 or configured.get('enabled') is not True:
        raise ValueError('Inference broker is required')
    info=os.lstat(BROKER_SOCKET)
    if not stat.S_ISSOCK(info.st_mode) or info.st_mode & 0o077 or info.st_uid!=1000:
        raise ValueError('Invalid private inference socket')
    connection=http.client.HTTPConnection('localhost',timeout=timeout)
    sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);sock.settimeout(timeout)
    try:
        sock.connect(BROKER_SOCKET);connection.sock=sock
        path=request.full_url.removeprefix(OLLAMA)
        connection.request(request.get_method(),path,body=request.data,headers={'Content-Type':'application/json'})
        response=connection.getresponse()
        if response.status!=200:raise OSError('Inference broker rejected request')
        yield response
    finally:connection.close();sock.close()

def ollama(path, payload=None, timeout=120):
    if path not in ('/api/chat','/api/tags','/api/ps'):
        raise ValueError('Inference route is not allowed')
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA + path, data=data, headers={'Content-Type':'application/json'})
    with local_response(req, timeout) as response:
        raw = response.read(2_000_001)
        if len(raw)>2_000_000:
            raise ValueError('Model response too large')
        return json.loads(raw)

def chat_stream(payload, timeout=120):
    """Bounded NDJSON from the same fixed, proxy-free loopback service."""
    req=urllib.request.Request(OLLAMA+'/api/chat',data=json.dumps(dict(payload,stream=True)).encode(),headers={'Content-Type':'application/json'})
    deadline=time.monotonic()+timeout
    total=0
    with local_response(req,timeout) as response:
        for _ in range(8192):
            raw=response.readline(65537)
            total+=len(raw)
            if len(raw)>65536 or total>2_000_000 or time.monotonic()>deadline:
                raise ValueError('Model stream exceeded limits')
            if not raw:
                raise ValueError('Model stream ended without completion')
            frame=json.loads(raw)
            if not isinstance(frame,dict) or frame.get('error'):
                raise ValueError('Invalid model stream')
            yield frame
            if frame.get('done') is True:
                return
        raise ValueError('Too many model frames')
