"""Owner-only Windows release staging/cutover. Never imported by the model."""
import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
STORE=ROOT/'data/releases'
DIRECTORIES=('runtime','agents','skills','config','scripts','deploy','tests','web','knowledge','evals')
FILES=('.containerignore','.gitattributes','LICENSE','LICENSE-NOTICE.md','requirements.txt','requirements-knowledge.txt','requirements-retrieval.txt','package.json','package-lock.json')
# Resumable owner build temporaries never enter a frozen release.
BUILD_TEMP=('approved.build.sqlite','notes.build.sqlite','notes.build.sqlite-journal','embeddings.build.npy','embeddings-rowids.build.npy','embeddings-manifest.tmp','notes.build.sqlite-wal','notes.build.sqlite-shm')
# Agent container limits: room for CPU embedding/reranking (owner-approved 2026-10-09).
AGENT_LIMITS=('--pids-limit=64','--memory=12g','--cpus=8')
HTTP=urllib.request.build_opener(urllib.request.ProxyHandler({}))

class ModelPlacementPending(RuntimeError):pass

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))

def _wait_until(deadline,interval,message):
    remaining=deadline-time.monotonic()
    if remaining<=0:raise RuntimeError(message)
    time.sleep(min(interval,remaining))

def _startup_gate(identifier):
    if not isinstance(identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',identifier):raise ValueError('Invalid startup release identity')
    path=STORE/(identifier+'.startup-ready')
    if path.is_symlink():raise ValueError('Startup readiness gate redirected')
    return path

def _mark_startup_ready(state):
    path=_startup_gate(state['id']);temp=path.with_name(path.name+'.tmp')
    if temp.is_symlink():raise ValueError('Startup readiness temporary redirected')
    temp.write_text('ready\n',encoding='ascii');temp.replace(path)

def _startup_model_status(backend,deadline,poll_interval):
    remaining=deadline-time.monotonic()
    if remaining<=0:raise RuntimeError('Local model service did not become ready within the startup deadline')
    try:
        status=backend.call('/api/ps',timeout=max(1,min(5,int(remaining))),
                            process_timeout=max(2,remaining+2))
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
        if time.monotonic()>=deadline:
            raise RuntimeError('Local model service did not become ready within the startup deadline') from exc
        _wait_until(deadline,poll_interval,'Local model service did not become ready within the startup deadline')
        return None
    models=status.get('models') if isinstance(status,dict) else None
    if not isinstance(models,list) or any(not isinstance(model,dict) for model in models):
        raise ValueError('Local model service returned an invalid process list')
    return models

def _await_selected_model(backend,identifier,tag,timeout,poll_interval):
    deadline=time.monotonic()+timeout;warmed=False
    while True:
        models=_startup_model_status(backend,deadline,poll_interval)
        if models is None:continue
        if any(model.get('name')==tag for model in models):
            try:return backend.verify(identifier)
            except ModelPlacementPending as exc:
                _wait_until(deadline,poll_interval,'Selected model did not reach full GPU residency before the startup deadline')
                continue
        if not warmed:
            if backend.notes_busy():raise RuntimeError('Nightly notes workload is active; model warm-up is deferred')
            backend.load(identifier);warmed=True;deadline=time.monotonic()+timeout
            continue
        _wait_until(deadline,poll_interval,'Selected model did not become resident before the startup deadline')

def checksum(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');temp.replace(path)

def release_path(identifier):
    if not isinstance(identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',identifier):raise ValueError('Invalid release ID')
    path=STORE/identifier
    if path.is_symlink() or path.resolve()!=STORE.resolve()/identifier:raise ValueError('Release path redirected')
    return path

@contextmanager
def exclusive():
    import msvcrt
    STORE.mkdir(parents=True,exist_ok=True)
    with (STORE/'manage.lock').open('a+b') as lock:
        lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:yield
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)

def payload(root):
    paths=[root/name for name in FILES if (root/name).is_file()]
    for name in DIRECTORIES:paths.extend(p for p in (root/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in BUILD_TEMP)
    result={}
    for path in sorted(paths):
        if path.is_symlink():raise ValueError('Symlink in release payload')
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            while block:=stream.read(1024*1024):digest.update(block)
        result[path.relative_to(root).as_posix()]=digest.hexdigest()
    return result

def run(root,*arguments,timeout=180):
    env=os.environ.copy();env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',LARPUS_ISOLATION='wsl-podman')
    result=subprocess.run(list(arguments),cwd=root,env=env,capture_output=True,text=True,timeout=timeout)
    if result.returncode:raise RuntimeError('Release check failed: '+str(arguments[1:3])+'\n'+(result.stdout+result.stderr)[-2500:])
    return result.stdout.strip()

def wsl(*args,timeout=180,input_file=None):
    command=[str(Path(os.environ['SYSTEMROOT'])/'System32/wsl.exe'),'--distribution','Larpus','--user','larpus','--exec',*args]
    result=subprocess.run(command,stdin=input_file,capture_output=True,timeout=timeout)
    if result.returncode:raise RuntimeError('WSL release operation failed: '+result.stderr.decode(errors='replace')[-1500:])
    return result.stdout.decode().strip()

def podman(*args,timeout=180):return wsl('/usr/bin/env','XDG_RUNTIME_DIR=/run/user/1000','/usr/bin/podman',*args,timeout=timeout)

def issue_signatures(report):
    return Counter((x['category'],x['pattern'],x['severity'],x['location']['file']) for x in report['issues'])

def reviewed_signatures(entries):
    result=Counter()
    for item in entries:
        if set(item)!={'category','pattern','severity','file','count'} or type(item['count']) is not int or not 1<=item['count']<=100:raise ValueError('Invalid reviewed inventory')
        key=tuple(item[k] for k in ('category','pattern','severity','file'))
        if key in result:raise ValueError('Duplicate reviewed signature')
        result[key]=item['count']
    return result

def scan_gate(summary,report,baseline,targets=None,reviewed=None,source_hashes=None):
    actual=[r.get('target') for r in summary['results']]
    if summary['status'] not in ('pass','warning') or len(actual)!=len(set(actual)):raise ValueError('Incomplete scan')
    if targets is None:
        if len(actual)!=65 or 'mcp' not in actual:raise ValueError('Incomplete scan')
    elif set(actual)!=set(targets):raise ValueError('Incomplete scan target inventory')
    for result in summary['results']:
        if not result.get('complete') or (result['target']!='mcp' and result['status']!='pass'):raise ValueError('Skill scan failed or has findings')
    if issue_signatures(report)!=issue_signatures(baseline):
        if not reviewed or reviewed.get('version')!=1 or not reviewed.get('reason') or not reviewed.get('sources') or source_hashes!=reviewed['sources']:
            raise ValueError('MCP finding inventory changed; source-pinned review required')
        if reviewed_signatures(reviewed['previous'])!=issue_signatures(baseline) or reviewed_signatures(reviewed['approved'])!=issue_signatures(report):
            raise ValueError('MCP finding inventory differs from reviewed transition')

def check_catalog_counts(root):
    # Older retained releases predate this gate and remain valid rollback targets.
    if (root/'scripts/knowledge_counts.py').is_file():
        from scripts.knowledge_counts import reconcile
        reconcile(root)

def validate(root):
    meta=read(root/'release.json')
    if meta.get('version')!=1 or meta.get('id')!=root.name:raise ValueError('Invalid release metadata')
    if not meta.get('files') or payload(root)!=meta['files']:raise ValueError('Frozen release files changed')
    check_catalog_counts(root)
    fingerprint=run(root,sys.executable,'-c','from runtime.security_scan import fingerprint;print(fingerprint())')
    if fingerprint!=meta['source_fingerprint'] or read(root/'deployment.json')['source_fingerprint']!=fingerprint:raise ValueError('Release fingerprint mismatch')
    if not meta.get('bootstrap'):
        summary=read(root/'release-state/security/summary.json')
        if summary.get('fingerprint')!=fingerprint or meta.get('status')!='prepared':raise ValueError('Candidate not prepared')
        for name,pin in (('deployment.json','deployment_sha256'),('release-state/security/summary.json','scan_summary_sha256'),('release-state/security/mcp.json','scan_report_sha256')):
            if checksum(root/name)!=meta.get(pin):raise ValueError('Candidate deployment or scan receipt changed')
        if meta.get('voice_sha256') and checksum(root/'voice-deployment.json')!=meta['voice_sha256']:raise ValueError('Candidate voice receipt changed')
    return meta

def stage(source=None):
    source=ROOT if source is None else Path(source)
    if source.is_symlink() or not source.is_dir():raise ValueError('Invalid staging source')
    source=source.resolve()
    from scripts.knowledge_counts import reconcile
    reconcile(source)
    if (source/'knowledge/provenance.json').exists():run(source,sys.executable,'scripts/source-provenance.py','check')
    import _winapi
    identifier=uuid.uuid4().hex;dest=release_path(identifier)
    before=payload(source);dest.mkdir(parents=True)
    for name in DIRECTORIES:shutil.copytree(source/name,dest/name,ignore=shutil.ignore_patterns('__pycache__',*BUILD_TEMP))
    for name in FILES:
        if (source/name).is_file():shutil.copyfile(source/name,dest/name)
    _winapi.CreateJunction(str((ROOT/'data').resolve()),str(dest/'data'))
    _winapi.CreateJunction(str((ROOT/'vendor').resolve()),str(dest/'vendor'))
    if before!=payload(source) or before!=payload(dest):raise ValueError('Checkout changed during snapshot; candidate retained, not activated')
    fingerprint=run(dest,sys.executable,'-c','from runtime.security_scan import fingerprint;print(fingerprint())')
    write(dest/'release.json',{'version':1,'id':identifier,'source_fingerprint':fingerprint,'files':before,'status':'staged'})
    print('Staged '+identifier+'; active release untouched.',flush=True)
    return identifier

def prepare_voice(dest,old,linux):
    prior=read(old/('voice-deployment.json' if (old/'voice-deployment.json').exists() else 'data/voice-deployment.json'))
    digest=checksum(dest/'runtime/voice_worker.py')
    profile=dict(prior)
    if prior['worker_sha256']!=digest or prior.get('protocol')!='unix-persistent':
        base=prior['image']
        if not re.fullmatch(r'(?:sha256:)?[a-f0-9]{64}',base):raise ValueError('Invalid cached voice base')
        name='larpus-voice-'+dest.name
        print('Building separate persistent CPU voice; active voice preserved.',flush=True)
        podman('build','--pull=never','--network=none','--build-arg','BASE_IMAGE='+base,'-f',linux+'/deploy/voice/Persistent.Containerfile','-t','localhost/larpus-voice:'+dest.name,linux)
        image=podman('image','inspect','localhost/larpus-voice:'+dest.name,'--format','{{.Id}}')
        podman('run','--detach','--pull=never','--name',name,'--network=none','--read-only','--read-only-tmpfs=false','--user=1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=128','--memory=4g','--cpus=8','--log-driver=none','--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=128m','--mount=type=bind,src=/home/larpus/voice-models,dst=/models,ro',image)
        profile.update(image=image,container=name,protocol='unix-persistent',worker_sha256=digest)
    write(dest/'voice-deployment.json',profile)
    # The source/image/mount preflight remains mandatory before every request.
    for attempt in range(10):
        try:
            run(dest,sys.executable,'-c',"from runtime.voice import call;assert call({'action':'status'})['ready']")
            break
        except (OSError,RuntimeError,subprocess.SubprocessError):
            if attempt==9:raise
            time.sleep(0.5)

def prepare_selection(dest,profile,identifier):
    selection_args=[]
    if read(dest/'config/inference-broker.json').get('selection_enabled'):
        from runtime.model_selection import initial,validate
        state=initial()
        if profile.get('model_selection'):
            previous=validate(json.loads(wsl('/usr/bin/python3','-c','print(open('+repr(profile['model_selection']+'/state.json')+').read())')))
            if previous['phase']!='ready':raise ValueError('Model selection must be ready before preparation')
            state['active_id']=previous['active_id']
        source='/home/larpus/release-selection/'+identifier
        code='import json,os;from pathlib import Path;p=Path('+repr(source)+');p.mkdir(parents=True,exist_ok=True);f=p/"state.json";f.write_text('+repr(json.dumps(state))+');os.chmod(p,0o755);os.chmod(f,0o644)'
        wsl('/usr/bin/python3','-c',code)
        selection_args=['--mount=type=bind,src='+source+',dst=/run/larpus-selection,ro']
        profile['model_selection']=source
    return selection_args

def check_ui(root):
    tests=json.loads(run(root,sys.executable,'-c','import json;from scripts.ui_checks import TESTS;print(json.dumps(TESTS))'))
    for test in tests:print(run(root,'node.exe','tests/'+test),flush=True)


def verify_pipeline(profile):
    code="""import json,time
from runtime.retrieval_worker import call
for attempt in range(60):
 try:
  initial=call({'action':'pipeline'},2);break
 except OSError:
  if attempt==59:raise
  time.sleep(0.5)
numpy=call({'action':'pipeline','pipeline_id':'numpy'},8)
assembly=call({'action':'pipeline','pipeline_id':'assembly'},8)
optimized=call({'action':'pipeline','pipeline_id':'assembly-optimized'},8)
restored=call({'action':'pipeline','pipeline_id':initial['active_id']},8)
print(json.dumps({'initial':initial,'numpy':numpy,'assembly':assembly,'optimized':optimized,'restored':restored}))
"""
    state=json.loads(podman('exec',profile['agent_name'],'python','-c',code))
    if state['initial']['active_id'] not in ('numpy','assembly','assembly-optimized') or (state['numpy']['active_id'],state['assembly']['active_id'],state['optimized']['active_id'],state['restored']['active_id'])!=('numpy','assembly','assembly-optimized',state['initial']['active_id']):
        raise ValueError('Pipeline switch/restore readiness failed')
    print('Candidate Assembly/NumPy worker switching verified; initial pipeline restored.',flush=True)

def select_gpu_driver(profile,gpu_driver):
    if gpu_driver is None:return profile
    if not re.fullmatch(r'/usr/lib/wsl/drivers/nv_[a-z0-9]+\.inf_amd64_[a-f0-9]{16}',gpu_driver):
        raise ValueError('Invalid narrow NVIDIA driver package')
    wsl('/usr/bin/test','-f',gpu_driver+'/libcuda.so.1.1')
    return {**profile,'gpu_driver':gpu_driver}

def prepare(identifier,gpu_driver=None):
    dest=release_path(identifier);meta=read(dest/'release.json')
    if payload(dest)!=meta['files']:raise ValueError('Candidate changed after staging')
    active=read(STORE/'active.json');old=release_path(active['id'])
    profile=read(old/'deployment.json');profile['agent_name']='larpus-agent-'+identifier
    profile['source_fingerprint']=meta['source_fingerprint']
    profile=select_gpu_driver(profile,gpu_driver)
    # Fixed offline cache; GPU model stays shared, voice candidate stays separate.
    linux='/home/larpus/releases/'+identifier
    wsl('/bin/mkdir','-p',linux)
    archive=STORE/(identifier+'.tar')
    with tarfile.open(archive,'w') as tar:
        for name in (*DIRECTORIES,*FILES):
            if (dest/name).exists():tar.add(dest/name,arcname=name,filter=lambda info:None if '__pycache__' in info.name or info.name.rsplit('/',1)[-1] in BUILD_TEMP else info)
    with archive.open('rb') as source:wsl('/bin/tar','-xf','-','-C',linux,input_file=source)
    # Runtime wheels already live in the dedicated Linux preparation cache.
    wsl('/bin/mkdir','-p',linux+'/vendor')
    wsl('/bin/cp','-a','/home/larpus/build/vendor/runtime-wheels',linux+'/vendor/runtime-wheels')
    wsl('/usr/bin/env','--chdir='+linux+'/vendor/runtime-wheels','/usr/bin/sha256sum','--strict','--check','SHA256SUMS')
    # Pinned CPU retrieval models (scripts/prepare-retrieval.py sync); hard links, immutable.
    wsl('/bin/cp','-al','/home/larpus/build/vendor/retrieval-models',linux+'/vendor/retrieval-models')
    wsl('/usr/bin/env','--chdir='+linux+'/vendor/retrieval-models','/usr/bin/sha256sum','--strict','--check','--quiet','SHA256SUMS')
    base=podman('image','inspect','docker.io/library/python:3.12-slim-bookworm','--format','{{.Id}}')
    if not re.fullmatch(r'(?:sha256:)?[a-f0-9]{64}',base):raise ValueError('Invalid cached base image')
    print('Building offline candidate; current gateway remains available.',flush=True)
    run(dest,sys.executable,'scripts/broker-prompts.py','--check')
    podman('build','--pull=never','--network=none','--build-arg','BASE_IMAGE='+base,'-f',linux+'/deploy/windows-home/Containerfile','-t','localhost/larpus-agent:'+identifier,linux)
    profile['agent_image']=podman('image','inspect','localhost/larpus-agent:'+identifier,'--format','{{.Id}}').removeprefix('sha256:')
    broker_policy=dest/'config/inference-broker.json'
    boundary=['--pod','larpus-offline']
    if broker_policy.exists() and read(broker_policy).get('enabled') is True:
        name='larpus-broker-'+identifier
        podman('build','--pull=never','--network=none','--build-arg','BASE_IMAGE='+base,'-f',linux+'/deploy/windows-home/Broker.Containerfile','-t','localhost/larpus-broker:'+identifier,linux)
        broker_image=podman('image','inspect','localhost/larpus-broker:'+identifier,'--format','{{.Id}}').removeprefix('sha256:')
        notes_volume=name+'-notes'
        selection_args=prepare_selection(dest,profile,identifier)
        podman('run','--detach','--pull=never',*selection_args,'--name',name,'--pod','larpus-offline','--read-only','--read-only-tmpfs=false','--user=1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=64','--memory=256m','--cpus=1','--log-driver=none','--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=16m','--volume='+name+':/run/larpus-broker:rw,noexec,nosuid,nodev','--volume='+notes_volume+':/run/larpus-notes:rw,noexec,nosuid,nodev',broker_image)
        profile['broker']={'protocol':2,'container':name,'image':broker_image,'volume':name,'notes_volume':notes_volume}
        for attempt in range(20):
            try:
                podman('exec',name,'python','-c',"from pathlib import Path; assert all(Path(p).is_socket() for p in ('/run/larpus-broker/inference.sock','/run/larpus-notes/inference.sock'))");break
            except (RuntimeError,subprocess.CalledProcessError):time.sleep(.25)
        else:raise ValueError('Broker failed readiness')
        boundary=['--network=none','--volume='+name+':/run/larpus-broker:ro,noexec,nosuid,nodev']
        notes_name='larpus-notes-'+identifier
        podman('build','--pull=never','--network=none','--build-arg','BASE_IMAGE='+base,'-f',linux+'/deploy/windows-home/Notes.Containerfile','-t','localhost/larpus-notes:'+identifier,linux)
        notes_image=podman('image','inspect','localhost/larpus-notes:'+identifier,'--format','{{.Id}}').removeprefix('sha256:')
        podman('run','--detach','--pull=never','--name',notes_name,'--network=none','--read-only','--read-only-tmpfs=false','--user=1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=32','--memory=128m','--cpus=1','--log-driver=none','--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=16m','--volume='+notes_volume+':/run/larpus-notes:ro,noexec,nosuid,nodev',notes_image)
        profile['notes']={'container':notes_name,'image':notes_image,'volume':notes_volume}
    podman('run','--detach','--pull=never','--name',profile['agent_name'],*boundary,'--read-only','--read-only-tmpfs=false','--user=1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges',*AGENT_LIMITS,'--log-driver=none','--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=128m','--volume=larpus-quarantine:/app/data/quarantine:rw,noexec,nosuid,nodev',profile['agent_image'])
    write(dest/'deployment.json',profile)
    if (dest/'runtime/scoring_pipeline.py').exists():verify_pipeline(profile)
    prepare_voice(dest,old,linux)
    print(run(dest,sys.executable,'scripts/test-local.py',timeout=600),flush=True)
    print(run(dest,sys.executable,'scripts/evaluate-companion.py'),flush=True)
    check_ui(dest)
    print(run(dest,sys.executable,'-m','runtime.isolation','check'),flush=True)
    print('Scanning candidate independently of the active release.',flush=True)
    run(dest,sys.executable,'-c',"import json;from runtime.security_scan import scan,discover,APPROVED;d=discover();assert d==json.loads(APPROVED.read_text())['tools'];r=scan(d);print(r['status'])",timeout=900)
    scan_dir=old/('data/security' if read(old/'release.json').get('bootstrap') else 'release-state/security')
    reviewed_file=dest/'config/mcp-scan-reviewed.json'
    reviewed=read(reviewed_file) if reviewed_file.exists() else None
    source_hashes=None
    if reviewed:
        if any(name not in meta['files'] for name in reviewed.get('sources',{})):raise ValueError('Review source outside frozen payload')
        source_hashes={name:checksum(dest/name) for name in reviewed['sources']}
    scan_gate(read(dest/'release-state/security/summary.json'),read(dest/'release-state/security/mcp.json'),read(scan_dir/'mcp.json'),[e['id'] for e in read(dest/'skills/registry.json')['skills']]+['mcp'],reviewed,source_hashes)
    if payload(dest)!=meta['files']:raise ValueError('Candidate files changed during checks')
    meta.update(status='prepared',deployment_sha256=checksum(dest/'deployment.json'),voice_sha256=checksum(dest/'voice-deployment.json'),scan_summary_sha256=checksum(dest/'release-state/security/summary.json'),scan_report_sha256=checksum(dest/'release-state/security/mcp.json'))
    write(dest/'release.json',meta)
    print('Prepared '+identifier+'; activate only when ready for a brief cutover.',flush=True)

def process(pid):
    if type(pid)!=int or pid<=0:raise ValueError('Invalid gateway PID')
    command=f'Get-CimInstance Win32_Process -Filter "ProcessId={pid}" | Select-Object ProcessId,CreationDate,CommandLine | ConvertTo-Json -Compress'
    raw=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,check=True,timeout=15).stdout.strip()
    return json.loads(raw) if raw else None

def running(state):
    actual=process(state['pid'])
    return actual==state['process'] if actual else False

def _drop_unrecorded(child):
    """Close the exact process handle when its identity was never stored."""
    if child.poll() is not None:return
    child.terminate()
    try:child.wait(timeout=15)
    except subprocess.TimeoutExpired:
        child.kill();child.wait(timeout=15)

def launch(identifier,settings):
    root=release_path(identifier);validate(root)
    gate=_startup_gate(identifier)
    gate.unlink(missing_ok=True)
    (root/'release-state/drain').unlink(missing_ok=True)
    env=os.environ.copy();env.update(LARPUS_HOST=settings['host'],LARPUS_LAN_CIDR=settings['subnet'],LARPUS_PORT=str(settings['port']),LARPUS_ISOLATION='wsl-podman',LARPUS_STARTUP_GATE=str(gate),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
    code='import sys,runpy;sys.path.insert(0,'+repr(str(root))+');runpy.run_module("runtime.gateway",run_name="__main__")'
    with (STORE/(identifier+'.gateway.log')).open('ab') as log:child=subprocess.Popen([sys.executable,'-c',code],cwd=root,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    try:found=process(child.pid)
    except (OSError,ValueError,subprocess.SubprocessError):
        try:_drop_unrecorded(child)
        except (OSError,subprocess.SubprocessError):raise RuntimeError('Unrecorded gateway still running') from None
        raise
    if not found:
        try:_drop_unrecorded(child)
        except (OSError,subprocess.SubprocessError):raise RuntimeError('Unrecorded gateway still running') from None
        raise RuntimeError('Gateway exited before startup')
    return {**settings,'version':1,'id':identifier,'pid':child.pid,'process':found}

def stop(state):
    actual=process(state['pid'])
    if actual and actual!=state['process']:raise ValueError('Gateway PID was reused; refusing to signal it')
    if not running(state):return
    root=release_path(state['id']);drain=root/'release-state/drain';drain.parent.mkdir(exist_ok=True);drain.write_text('owner update\n')
    if read(root/'release.json').get('bootstrap'):
        # One-time legacy gateway has no drain watcher. Identity is checked above.
        subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',f'Stop-Process -Id {state["pid"]}'],check=True,timeout=15)
    deadline=time.monotonic()+180
    while running(state):
        if time.monotonic()>deadline:
            drain.unlink(missing_ok=True)
            raise RuntimeError('Gateway did not drain; no forced termination')
        time.sleep(.5)

def ready(state,timeout=60):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if not running(state):raise RuntimeError('New gateway exited')
        try:
            with HTTP.open(f'http://127.0.0.1:{state["port"]}/api/station-health',timeout=3) as response:health=json.load(response)
            checks={c['name']:c['status'] for c in health.get('checks',[])}
            required={'password','local_skills','approved_knowledge','input_filter','output_dlp','mcp_surface','models','model_gpu','egress_enforcement','voice'}
            if required.issubset(checks) and all(checks[n]=='pass' for n in required):
                _mark_startup_ready(state)
                return
        except OSError:pass
        time.sleep(.5)
    raise RuntimeError('New gateway functional readiness failed')

def ensure_startup_model(backend=None,timeout=60,poll_interval=1):
    """Verify the approved local model before the agent can admit inference."""
    from runtime import model_selection
    if backend is None:
        from runtime.model_backend import Backend
        backend=Backend()
    state=model_selection.validate(backend.read())
    if state['phase']!='ready':raise RuntimeError('Model selection is not ready; owner recovery is required')
    identifier=state['active_id']
    return _await_selected_model(backend,identifier,model_selection.model(identifier)['tag'],timeout,poll_interval)

def verify_broker_startup(profile,timeout=15,poll_interval=.5):
    name=profile.get('broker',{}).get('container')
    if not isinstance(name,str) or not re.fullmatch(r'larpus-broker-[a-f0-9]{32}',name):
        raise ValueError('Invalid broker startup identity')
    code="""import http.client,json,socket,stat
from pathlib import Path
for path in ('/run/larpus-broker/inference.sock','/run/larpus-notes/inference.sock'):
 info=Path(path).lstat()
 if not stat.S_ISSOCK(info.st_mode) or info.st_mode&0o077 or info.st_uid!=1000:raise SystemExit('Invalid broker socket')
c=http.client.HTTPConnection('localhost',timeout=2);c.sock=socket.socket(socket.AF_UNIX);c.sock.settimeout(2);c.sock.connect('/run/larpus-broker/inference.sock');c.request('GET','/broker/state');r=c.getresponse();v=json.loads(r.read(8193));c.close()
if r.status!=200 or not isinstance(v,dict) or type(v.get('faulted')) is not bool or 'active' not in v or type(v.get('waiting_chat')) is not int:raise SystemExit('Invalid broker state')
print(json.dumps(v))
"""
    deadline=time.monotonic()+timeout
    while True:
        remaining=deadline-time.monotonic()
        if remaining<=0:raise RuntimeError('Broker sockets did not become idle and ready before the startup deadline')
        try:
            value=json.loads(podman('exec',name,'python','-c',code,timeout=max(3,remaining+2)))
        except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
            if time.monotonic()>=deadline:raise RuntimeError('Broker sockets did not become ready before the startup deadline') from exc
            time.sleep(min(poll_interval,max(0,deadline-time.monotonic())))
            continue
        if value['faulted']:raise RuntimeError('Broker cancellation fence is faulted; owner recovery is required')
        if value['active'] is None and value['waiting_chat']==0:return value
        if time.monotonic()>=deadline:raise RuntimeError('Broker remained busy; startup did not interrupt active inference')
        time.sleep(min(poll_interval,max(0,deadline-time.monotonic())))

def ensure_execution(root):
    path=root/'deployment.json'
    if not path.exists():return
    profile=read(path)
    selected=[(profile.get('agent_name','larpus-agent'),profile['agent_image'])]
    if profile.get('broker'):selected.insert(0,(profile['broker']['container'],profile['broker']['image']))
    if profile.get('notes'):selected.append((profile['notes']['container'],profile['notes']['image']))
    for name,image in selected:
        if not re.fullmatch(r'larpus-(?:agent|broker|notes)(?:-[a-f0-9]{32})?',name):raise ValueError('Invalid retained execution identity')
        item=json.loads(podman('inspect',name))[0]
        if item['Image'].removeprefix('sha256:')!=image.removeprefix('sha256:'):raise ValueError('Retained execution image drift')
        if not item['State']['Running']:podman('start',name)

def check_cutover_selection(candidate,current):
    """Refuse stale prepared model state before stopping any gateway."""
    from runtime.model_selection import initial,validate
    states=[]
    for root in (candidate,current):
        source=read(root/'deployment.json').get('model_selection')
        state=validate(json.loads(wsl('/usr/bin/python3','-c','print(open('+repr(source+'/state.json')+').read())'))) if source else initial()
        if state['phase']!='ready':raise ValueError('Finish model switching or recovery before activation')
        states.append(state['active_id'])
    if states[0]!=states[1]:raise ValueError('Prepared selection is stale; select its model before activation or prepare a fresh release')


def cutover(identifier):
    if (STORE/'pending.json').exists():raise ValueError('Interrupted cutover recorded; run start to recover first')
    root=release_path(identifier);validate(root)
    old=read(STORE/'active.json');check_cutover_selection(root,release_path(old['id']))
    ensure_execution(root)
    run(root,sys.executable,'-m','runtime.isolation','check')
    old=read(STORE/'active.json')
    if identifier==old['id']:raise ValueError('Release already active')
    write(STORE/'pending.json',{'old':old,'candidate_id':identifier})
    new=None
    try:
        stop(old)
        new=launch(identifier,{k:old[k] for k in ('host','subnet','port')})
        write(STORE/'pending.json',{'old':old,'candidate':new,'candidate_id':identifier})
        ready(new)
        new['previous']=old['id'];write(STORE/'active.json',new)
        (STORE/'pending.json').unlink()
        print('Active '+identifier+'; previous '+old['id']+' retained.',flush=True)
    except Exception:
        if new:stop(new)
        if running(old):
            (release_path(old['id'])/'release-state/drain').unlink(missing_ok=True)
        else:
            restored=launch(old['id'],old);write(STORE/'active.json',restored);ready(restored)
        (STORE/'pending.json').unlink(missing_ok=True)
        raise

def start():
    if (STORE/'pending.json').exists():
        pending=read(STORE/'pending.json')
        current=read(STORE/'active.json')
        # The active pointer may already contain a completed cutover or a
        # restored gateway with a new PID. Never replace it with a stale PID.
        if running(current) and current!=pending['old']:
            ready(current)
        else:
            if pending.get('candidate'):stop(pending['candidate'])
            write(STORE/'active.json',pending['old'])
        (STORE/'pending.json').unlink()
    state=read(STORE/'active.json')
    if running(state):print('Active gateway already running: '+state['id']);return
    profile=read(release_path(state['id'])/'deployment.json')
    voice=read(release_path(state['id'])/('voice-deployment.json' if (release_path(state['id'])/'voice-deployment.json').exists() else 'data/voice-deployment.json'))
    voice_name=voice.get('container','larpus-voice')
    if not re.fullmatch(r'larpus-voice(?:-[a-f0-9]{32})?',voice_name):raise ValueError('Invalid voice identity')
    # Starting the whole pod also revives retained historical containers.
    # Podman starts its infrastructure with this one approved member instead.
    podman('start','larpus-model')
    if profile.get('broker'):podman('start',profile['broker']['container'])
    if profile.get('notes'):podman('start',profile['notes']['container'])
    if profile.get('broker'):
        verify_broker_startup(profile)
        ensure_startup_model()
        verify_broker_startup(profile)
    podman('start',voice_name)
    podman('start',profile.get('agent_name','larpus-agent'))
    new=launch(state['id'],state)
    try:ready(new)
    except Exception:
        stop(new)
        raise
    write(STORE/'active.json',new)
    print('Started active release '+state['id'])

def keep_names(state):
    """Containers the active and previous releases need; everything else is idle."""
    names={'larpus-model'}
    for identifier in (state.get('id'),state.get('previous')):
        if not identifier:continue
        root=release_path(identifier)
        profile=read(root/'deployment.json') if (root/'deployment.json').exists() else {}
        names.add(profile.get('agent_name','larpus-agent'))
        if profile.get('broker'):names.add(profile['broker']['container'])
        if profile.get('notes'):names.add(profile['notes']['container'])
        voice_file=root/'voice-deployment.json' if (root/'voice-deployment.json').exists() else ROOT/'data/voice-deployment.json'
        names.add(read(voice_file).get('container','larpus-voice') if voice_file.exists() else 'larpus-voice')
    return names

def prune():
    """Stop (never remove) idle Larpus agent/voice containers to free RAM and CPU."""
    state=read(STORE/'active.json');keep=keep_names(state)
    # Prepared candidates newer than the active release are awaiting activation; keep them.
    active_time=release_path(state['id']).stat().st_mtime
    for folder in (STORE.iterdir() if STORE.is_dir() else []):
        if re.fullmatch(r'[a-f0-9]{32}',folder.name) and (folder/'deployment.json').exists() and folder.stat().st_mtime>active_time:
            profile=read(folder/'deployment.json')
            keep.add(profile.get('agent_name','larpus-agent-'+folder.name))
            if profile.get('broker'):keep.add(profile['broker']['container'])
            if profile.get('notes'):keep.add(profile['notes']['container'])
    active_profile=release_path(state['id'])/'deployment.json'
    if active_profile.exists() and read(active_profile).get('broker') and state.get('previous'):
        previous_profile=release_path(state['previous'])/'deployment.json'
        if previous_profile.exists() and not read(previous_profile).get('broker'):
            keep.discard(read(previous_profile).get('agent_name','larpus-agent'))
        elif previous_profile.exists() and read(active_profile)['broker'].get('protocol')==2:
            previous=read(previous_profile)
            keep.discard(previous.get('agent_name','larpus-agent'))
            for key in ('broker','notes'):
                if previous.get(key):keep.discard(previous[key]['container'])
    running_names=podman('ps','--format','{{.Names}}').split()
    idle=[n for n in running_names if re.fullmatch(r'larpus-(agent|voice|broker|notes)(-[a-z0-9-]+)?',n) and n not in keep]
    if idle:podman('stop','--time','5',*idle,timeout=300)
    print(json.dumps({'kept':sorted(keep),'stopped':idle}),flush=True)
    return idle

def validate_cli_args(parser,args):
    if args.source is not None and args.operation!='stage':parser.error('--source is only valid with stage')
    if args.gpu_driver is not None and args.operation!='prepare':parser.error('--gpu-driver is only valid with prepare')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=('stage','prepare','activate','rollback','start','status','prune'));parser.add_argument('id',nargs='?')
    parser.add_argument('--source',type=Path,help='Explicit prepared source tree for stage; owner data/store remain unchanged')
    parser.add_argument('--gpu-driver',help='Reviewed narrow WSL driver package for a newly prepared release')
    args=parser.parse_args()
    validate_cli_args(parser,args)
    if os.name!='nt':raise SystemExit('Owner Windows release manager required')
    if args.operation=='status':
        state=read(STORE/'active.json');print(json.dumps({'id':state['id'],'running':running(state),'previous':state.get('previous'),'pending':(STORE/'pending.json').exists()},indent=2));return
    with exclusive():
        if args.operation=='stage':stage(args.source)
        elif args.operation=='prepare':prepare(args.id,args.gpu_driver)
        elif args.operation=='activate':cutover(args.id);prune()
        elif args.operation=='rollback':cutover(read(STORE/'active.json')['previous'])
        elif args.operation=='start':start();prune()
        elif args.operation=='prune':prune()
        else:
            state=read(STORE/'active.json');print(json.dumps({'id':state['id'],'running':running(state),'previous':state.get('previous'),'pending':(STORE/'pending.json').exists()},indent=2))

if __name__=='__main__':main()
