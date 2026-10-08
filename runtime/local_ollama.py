"""The only inference network adapter: fixed numeric loopback, no redirects."""
import json
import urllib.error
import urllib.request

OLLAMA = 'http://127.0.0.1:11434'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.URLError('Inference redirects are disabled')

HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

def ollama(path, payload=None, timeout=120):
    if path not in ('/api/chat','/api/tags'):
        raise ValueError('Inference route is not allowed')
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA + path, data=data, headers={'Content-Type':'application/json'})
    with HTTP.open(req, timeout=timeout) as response:
        raw = response.read(2_000_001)
        if len(raw)>2_000_000:
            raise ValueError('Model response too large')
        return json.loads(raw)
