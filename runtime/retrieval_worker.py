"""Persistent CPU retrieval worker inside the sealed agent container.

Models and the embedding index are hash-verified once at start and stay loaded.
IPC is one owner-only Unix socket on the agent's private /tmp: no TCP listener,
no new mount, no network (the pod has none). Clients fail closed to BM25 when
the socket is absent, slow or returns anything invalid.
"""
import json
import os
from pathlib import Path
import socket
import struct
import sys
import time

SOCKET=os.environ.get('LARPUS_RETRIEVAL_SOCKET','/tmp/larpus-retrieval.sock')
REQUEST_LIMIT=512*1024
RESPONSE_LIMIT=64*1024
MAX_PASSAGES=32
MAX_TEXT=4000

def _exact(stream,count):
    parts=[]
    while count:
        block=stream.recv(count)
        if not block:raise ValueError('Truncated retrieval frame')
        parts.append(block);count-=len(block)
    return b''.join(parts)

def receive(stream,limit):
    size=struct.unpack('!I',_exact(stream,4))[0]
    if not 0<size<=limit:raise ValueError('Retrieval frame exceeds limit')
    return json.loads(_exact(stream,size))

def send_frame(stream,value,limit):
    raw=json.dumps(value).encode()
    if len(raw)>limit:raise ValueError('Retrieval result exceeds limit')
    stream.sendall(struct.pack('!I',len(raw))+raw)

def _pipeline_request(request):
    if set(request)=={'action'}:return request
    if set(request)=={'action','pipeline_id'} and request['pipeline_id'] in ('numpy','assembly'):return request
    raise ValueError('Invalid pipeline selection')

def _rerank_request(request):
    passages=request['passages']
    if not isinstance(passages,list) or not 1<=len(passages)<=MAX_PASSAGES or any(not isinstance(p,str) or len(p)>MAX_TEXT for p in passages):
        raise ValueError('Invalid passages')
    if type(request['budget_ms']) is not int or not 1<=request['budget_ms']<=5000:raise ValueError('Invalid budget')
    return request

def validate(request):
    if not isinstance(request,dict):raise ValueError('Invalid retrieval request')
    action=request.get('action')
    if action=='status' and set(request)=={'action'}:return request
    if action=='pipeline':return _pipeline_request(request)
    question=request.get('question')
    if not isinstance(question,str) or not 0<len(question)<=MAX_TEXT:raise ValueError('Invalid question')
    if action=='neighbors' and set(request)=={'action','question','limit'}:
        if type(request['limit']) is not int or not 1<=request['limit']<=64:raise ValueError('Invalid limit')
        return request
    if action=='rerank' and set(request)=={'action','question','passages','budget_ms'}:
        return _rerank_request(request)
    raise ValueError('Unsupported retrieval operation')

def handle(engine,request,loaded_ms):
    request=validate(request)
    if request['action']=='pipeline':
        if 'pipeline_id' in request:return engine.pipeline.select(request['pipeline_id'])
        return engine.pipeline.status()
    if request['action']=='status':
        return {'ready':True,'load_ms':loaded_ms,'rows':int(len(engine.rowids)),'pid':os.getpid()}
    if request['action']=='neighbors':
        return {'rowids':engine.neighbors(request['question'],request['limit'])}
    return {'scores':engine.rerank(request['question'],request['passages'],time.monotonic()+request['budget_ms']/1000)}

def serve():
    import signal
    signal.signal(signal.SIGTERM,lambda *_:sys.exit(0))  # PID 1: honour podman stop
    from runtime import retrieval
    from runtime.knowledge import DIRECTORY
    os.environ['LARPUS_RETRIEVAL_WORKER']='local'  # this process loads models itself
    started=time.monotonic()
    try:engine=retrieval.Engine(DIRECTORY)  # full hash verification, once
    except Exception as exc:
        # Stay alive (the container must not exit) but never listen: clients use BM25.
        print('retrieval worker disabled: '+type(exc).__name__,file=sys.stderr,flush=True)
        while True:time.sleep(3600)
    loaded_ms=round((time.monotonic()-started)*1000)
    path=Path(SOCKET);path.unlink(missing_ok=True)
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
        old=os.umask(0o177)
        try:server.bind(SOCKET)
        finally:os.umask(old)
        os.chmod(SOCKET,0o600);server.listen(8)
        while True:
            connection,_=server.accept()
            with connection:
                connection.settimeout(10)
                try:
                    if struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,struct.calcsize('3i')))[1]!=os.getuid():
                        continue  # same-UID peers only
                    result=handle(engine,receive(connection,REQUEST_LIMIT),loaded_ms)
                    send_frame(connection,result,RESPONSE_LIMIT)
                except Exception:
                    try:send_frame(connection,{'error':'retrieval failed'},RESPONSE_LIMIT)
                    except OSError:pass

def call(request,timeout):
    """Bounded client; raises on any failure so callers keep BM25."""
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
        connection.settimeout(max(0.05,timeout));connection.connect(SOCKET)
        send_frame(connection,request,REQUEST_LIMIT)
        reply=receive(connection,RESPONSE_LIMIT)
    if not isinstance(reply,dict) or 'error' in reply:raise OSError('Retrieval worker error')
    return reply

if __name__=='__main__' and sys.argv[1:]==['--serve']:serve()
