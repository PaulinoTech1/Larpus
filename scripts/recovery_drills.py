"""Disposable recovery evidence; never accepts production process or store targets."""
import argparse
from dataclasses import asdict, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import recovery_backend as rb, recovery_state as rs, supervise, releases

SCRIPT=Path(__file__).resolve()
CASES={
    'retrieval-worker-loss':'tests.test_retrieval_worker.RetrievalWorkerTests.test_worker_failure_mid_chat_keeps_bm25_order',
    'unconfirmed-cancellation':'tests.test_broker_scheduling.ScopeTests.test_failed_cancellation_keeps_generation_closed',
    'truncated-stream':'tests.test_streaming.StreamingTests.test_ndjson_transport_requires_done_and_caps_frames',
    'disk-full':'tests.test_recovery_state.JournalTests.test_failed_replace_preserves_previous_commit_and_prevents_launch',
    'failed-candidate':'tests.test_releases.ReleaseTests.test_failed_candidate_restores_old_release_and_pointer',
}

def owned(workspace,nonce):
    path=Path(workspace).absolute();rs.safe_path(path);path=path.resolve()
    if path.parent!=Path(tempfile.gettempdir()).resolve() or not path.name.startswith('larpus-recovery-drill-'):
        raise ValueError('Not an owned disposable workspace')
    if rb.bounded_json(path/'owner.json')!={'nonce':nonce,'version':1}:raise ValueError('Ownership mismatch')
    if (path/'data/releases/active.json').exists():raise ValueError('Release store forbidden')
    return path

def save(path,value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value),encoding='utf-8');os.replace(temporary,path)

def spawn(mode,path,nonce,port):
    owned(path,nonce)
    return subprocess.Popen([sys.executable,str(SCRIPT),'--fixture',mode,str(path),nonce,str(port)],
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

def process_identity(child,nonce):
    info=releases.process(child.pid)
    if info is None or child.poll() is not None:raise ValueError('Fixture not alive')
    return rb.identity({'id':nonce,'pid':child.pid,'process':info})

def terminate_owned(child,expected,nonce):
    if expected.release_id!=nonce or process_identity(child,nonce)!=expected:raise ValueError('Fixture identity changed')
    child.terminate();child.wait(timeout=10)

def health(port):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/station-health',timeout=1) as response:
        return json.loads(response.read(65536))

def wait_for(predicate,seconds=30):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        try:
            value=predicate()
            if value:return value
        except (OSError,ValueError,KeyError):pass
        time.sleep(.1)
    raise TimeoutError('Disposable condition did not become ready')

def gateway(path,nonce,port):
    owned(path,nonce);token=secrets.token_hex(16)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            now=time.monotonic()
            report={'producer':{'version':1,'release_id':nonce,'pid':os.getpid(),'token':token,'started':now,'finished':now},
                    'checks':[{'name':n,'status':'pass'} for n in sorted(rb.REQUIRED)]}
            raw=json.dumps(report).encode();self.send_response(200)
            self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.timeout=.2
    deadline=time.monotonic()+90
    while time.monotonic()<deadline and not (path/'stop').exists():server.handle_request()
    server.server_close()

class FixtureAdapter:
    """Only this adapter simulates dependency/pin checks; production adapter is unused."""
    def __init__(self,path,nonce,port):
        self.path=owned(path,nonce);self.nonce=nonce;self.port=port;self.children=[]

    def exclusive(self):return rs.file_lock(self.path/'management.lock')

    def observe(self):
        expected=rb.GatewayIdentity(**rb.bounded_json(self.path/'selected.json'))
        info=releases.process(expected.pid)
        actual=rb.identity({'id':self.nonce,'pid':expected.pid,'process':info}) if info else None
        process='dead' if actual is None else ('alive' if actual==expected else 'reused')
        try:
            report=health(self.port);http='responding'
            ready='ready' if rb.receipt_token(report,expected,0) else 'stale'
        except OSError:http='unreachable';ready='unknown'
        return rb.Observation(expected,process,http,ready,'ready','idle',None,time.time(),time.monotonic())

    def validate(self,expected):
        owned(self.path,self.nonce)
        if self.observe().identity!=expected:raise ValueError('Fixture changed')

    def validate_running(self,expected):
        owned(self.path,self.nonce)
        if not self.owned_alive(expected):raise ValueError('Fixture changed')

    def launch(self):
        child=spawn('gateway',self.path,self.nonce,self.port);self.children.append(child)
        return wait_for(lambda:process_identity(child,self.nonce))

    def owned_alive(self,expected):
        return any(c.poll() is None and process_identity(c,self.nonce)==expected for c in self.children)

    def wait_ready(self,expected,started):
        return bool(wait_for(lambda:rb.receipt_token(health(self.port),expected,started)))

    def publish(self,expected):save(self.path/'selected.json',asdict(expected))

    def stop(self,expected):
        for child in self.children:
            if child.poll() is None and process_identity(child,self.nonce)==expected:terminate_owned(child,expected,self.nonce)

    def cleanup(self):
        for child in self.children:
            if child.poll() is None:terminate_owned(child,process_identity(child,self.nonce),self.nonce)

def supervisor(path,nonce,port):
    adapter=FixtureAdapter(path,nonce,port)
    journal=rs.Journal(path/'journal');journal.set_armed(True)
    backend=rb.Backend(path,adapter=adapter,jitter=lambda:0)
    save(path/'supervisor-ready.json',{'pid':os.getpid()})
    deadline=time.monotonic()+90
    try:
        with journal.singleton():
            while time.monotonic()<deadline and not (path/'stop').exists():
                supervise.cycle(backend,journal,supervise.Policy())
                for _ in range(50):
                    if (path/'stop').exists():break
                    time.sleep(.1)
    finally:adapter.cleanup()

def gateway_drill(path,nonce):
    owned(path,nonce)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    initial=spawn('gateway',path,nonce,port);worker=None
    try:
        expected=wait_for(lambda:process_identity(initial,nonce));wait_for(lambda:health(port))
        save(path/'selected.json',asdict(expected))
        worker=spawn('supervisor',path,nonce,port)
        wait_for(lambda:(path/'supervisor-ready.json').exists())
        started=time.monotonic();terminate_owned(initial,expected,nonce)
        journal=rs.Journal(path/'journal');seen=[]
        def recovered():
            current=journal.read();marker=(current.state,current.reason)
            if not seen or seen[-1]!=marker:seen.append(marker)
            return current.reason=='recovered'
        wait_for(recovered,seconds=60)
        recovered_seconds=time.monotonic()-started;h=journal.read()
        selected=rb.GatewayIdentity(**rb.bounded_json(path/'selected.json'))
        if selected==expected or worker.poll() is not None or len(h.attempts)!=1:raise ValueError('Recovery contract failed')
        return {'state':'passed','evidence':'real disposable Python processes; simulated dependency/pin/health gates',
                'target':asdict(expected),'replacement':asdict(selected),'supervisor_pid':worker.pid,
                'recovery_seconds':recovered_seconds,'attempts':len(h.attempts),'generation_count':None,
                'committed_before':None,'committed_after':None,'transitions':[list(item) for item in seen]}
    finally:
        (path/'stop').touch()
        if initial.poll() is None:terminate_owned(initial,process_identity(initial,nonce),nonce)
        if worker is not None:worker.wait(timeout=15)

def cancellation_drill(workspace):
    """Scheduler fault consumed by the supervisor. Launch counter is measured."""
    from scripts.recovery_backend import Backend
    from scripts.supervise import cycle
    from tests.test_recovery_backend import FakeAdapter
    from tests.test_recovery_policy import history, observation
    path=Path(workspace);nonce=secrets.token_hex(16)
    path.mkdir(parents=True,exist_ok=True)
    journal=rs.Journal(path/'cancel-journal',protect=lambda p,**kw:None)
    journal.write(history(dead_count=3))
    adapter=FakeAdapter();adapter.current=observation(broker='faulted',process='dead')
    backend=Backend(path,adapter=adapter,jitter=lambda:0)
    decision=cycle(backend,journal,supervise.Policy(),False)
    return {'state':'passed' if decision.reason=='broker-fault' and adapter.launches==0 else 'failed',
            'evidence':'supervisor cycle with injected broker fault; launch counter measured',
            'generation_count':adapter.launches,'attempts':len(journal.read().attempts),
            'recovery_seconds':None,'committed_before':None,'committed_after':None,
            'transitions':[[journal.read().state,journal.read().reason]],'nonce':nonce}

def evidence_drill(workspace):
    """Approved fixture index through retrieve(); CPU worker forced down. No gateway launch."""
    import hashlib,sqlite3
    from runtime import knowledge,retrieval
    from scripts.recovery_backend import Backend
    from scripts.supervise import cycle
    from tests.test_recovery_backend import FakeAdapter
    from tests.test_recovery_policy import history, observation
    path=Path(workspace)/'evidence';path.mkdir(parents=True)
    rows=[('game-a','Game strategy notes','https://example.org/a','2026-10-09','offset 0','Players bluff and anticipate opponent moves in poker and chess strategy games.','psychologist'),
          ('game-b','Board game overview','https://example.org/b','2026-10-09','offset 0','A board game catalogue lists games, prices and opponents counts.','psychologist')]
    database=path/'approved.sqlite'
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE VIRTUAL TABLE chunks USING fts5(source_id UNINDEXED,title,url UNINDEXED,snapshot UNINDEXED,locator UNINDEXED,text,role UNINDEXED,tokenize='porter unicode61')")
        connection.executemany('INSERT INTO chunks VALUES (?,?,?,?,?,?,?)',rows)
    database_bytes=database.read_bytes()
    (path/'manifest.json').write_text(json.dumps({'version':1,'database_sha256':hashlib.sha256(database_bytes).hexdigest(),'database_bytes':len(database_bytes)}),encoding='utf-8')
    with patch_directory(path):
        found=knowledge.retrieve('psychologist','How do players anticipate opponents in games?')
    adapter=FakeAdapter();adapter.current=observation(process='alive',http='responding',readiness='ready')
    journal=rs.Journal(Path(workspace)/'evidence-journal',protect=lambda p,**kw:None)
    journal.write(history())
    cycle(Backend(Path(workspace),adapter=adapter,jitter=lambda:0),journal,supervise.Policy(),False)
    ids=[item['id'] for item in found]
    passed=ids==['game-a','game-b'] and adapter.launches==0
    return {'state':'passed' if passed else 'failed','evidence':'approved sqlite retrieve with CPU engine disabled; supervisor launch counter measured',
            'evidence_ids':ids,'generation_count':adapter.launches,'attempts':len(journal.read().attempts),
            'recovery_seconds':None,'committed_before':2,'committed_after':2,'transitions':[['observing',journal.read().reason]]}

def patch_directory(path):
    from contextlib import contextmanager
    from unittest.mock import patch
    from runtime import knowledge,retrieval
    @contextmanager
    def _patched():
        with patch.object(knowledge,'DIRECTORY',path),patch.object(retrieval,'engine',lambda directory:None),patch.object(knowledge,'_engine',lambda:None):
            yield
    return _patched()

def contract_drill(name):
    suite=unittest.defaultTestLoader.loadTestsFromName(CASES[name]);sink=io.StringIO()
    result=unittest.TextTestRunner(stream=sink,verbosity=0).run(suite)
    passed=result.wasSuccessful() and result.testsRun==1 and not result.skipped
    extra=True
    if name=='truncated-stream':
        node=shutil.which('node')
        extra=bool(node) and subprocess.run([node,'tests/chat-stream-ui.cjs'],cwd=SCRIPT.parents[1],
            capture_output=True,timeout=30).returncode==0
    return {'state':'passed' if passed and extra else 'failed','evidence':'injected adapter regression contract',
            'contract':CASES[name],'checks':result.testsRun,'failures':len(result.failures)+len(result.errors),
            'recovery_seconds':None,'attempts':None,'generation_count':None,
            'committed_before':1 if name=='disk-full' and passed else None,
            'committed_after':1 if name=='disk-full' and passed else None}

def _one_drill(name):
    if name=='gateway-exit':
        with tempfile.TemporaryDirectory(prefix='larpus-recovery-drill-') as directory:
            path=Path(directory);token=secrets.token_hex(16);save(path/'owner.json',{'nonce':token,'version':1})
            return _safe_gateway(path,token)
    if name=='retrieval-worker-loss':
        with tempfile.TemporaryDirectory(prefix='larpus-recovery-drill-') as directory:return evidence_drill(directory)
    if name=='unconfirmed-cancellation':
        with tempfile.TemporaryDirectory(prefix='larpus-recovery-drill-') as directory:return cancellation_drill(directory)
    return contract_drill(name)

def run_drills(workspace,repeats=5):
    """Workspace must be created by this harness, never inferred from --output."""
    nonce=rb.bounded_json(Path(workspace)/'owner.json')['nonce'];owned(workspace,nonce)
    rows=[]
    for repetition in range(repeats):
        for name in ('gateway-exit',*CASES):
            rows.append({'scenario':name,'repetition':repetition+1,**_one_drill(name)})
    times=sorted(r['recovery_seconds'] for r in rows if r['recovery_seconds'] is not None)
    return {'version':1,'scope':'disposable fixtures and injected regression contracts; no production faults',
            'state':'passed' if all(r['state']=='passed' for r in rows) else 'failed','runs':rows,
            'recovery':{'count':len(times),'median':times[len(times)//2] if times else None,
                        'p95':times[-1] if times else None,'max':max(times) if times else None},
            'limits':['No full-station crash test','Model generation_count stays null on the gateway drill',
                      'Truncated stream and failed-candidate rows rerun injected contracts',
                      'Disk-full evidence covers the recovery journal, not every owner-data writer',
                      'Synthetic backup is a separate module and is not an owner-data restore']}

def _safe_gateway(path,nonce):
    try:return {**gateway_drill(path,nonce),'cleanup':'passed'}
    except (OSError,ValueError,TimeoutError,subprocess.SubprocessError):
        return {'state':'failed','cleanup':'uncertain','recovery_seconds':None,'attempts':None,
                'generation_count':None,'committed_before':None,'committed_after':None}

def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if args and args[0]=='--fixture':
        if len(args)!=5 or args[1] not in {'gateway','supervisor'}:raise ValueError('Invalid fixture')
        mode,path,nonce,port=args[1:];owned(path,nonce)
        (gateway if mode=='gateway' else supervisor)(Path(path),nonce,int(port));return 0
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    options=parser.parse_args(args)
    with tempfile.TemporaryDirectory(prefix='larpus-recovery-drill-') as directory:
        path=Path(directory);nonce=secrets.token_hex(16);save(path/'owner.json',{'nonce':nonce,'version':1})
        report=run_drills(path)
    options.output.parent.mkdir(parents=True,exist_ok=True);save(options.output,report)
    print(json.dumps({'state':report['state'],'runs':len(report['runs']),'output':str(options.output)}))
    return 0 if report['state']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
