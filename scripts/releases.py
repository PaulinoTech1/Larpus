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
STORE=ROOT/'data/releases'
DIRECTORIES=('runtime','agents','skills','config','scripts','deploy','tests','web','knowledge')
FILES=('.containerignore','.gitattributes','LICENSE','LICENSE-NOTICE.md','requirements.txt','requirements-knowledge.txt','package.json','package-lock.json')
HTTP=urllib.request.build_opener(urllib.request.ProxyHandler({}))

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))

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
    for name in DIRECTORIES:paths.extend(p for p in (root/name).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='approved.build.sqlite')
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

def scan_gate(summary,report,baseline,targets=None):
    actual=[r.get('target') for r in summary['results']]
    if summary['status'] not in ('pass','warning') or len(actual)!=len(set(actual)):raise ValueError('Incomplete scan')
    if targets is None:
        if len(actual)!=65 or 'mcp' not in actual:raise ValueError('Incomplete scan')
    elif set(actual)!=set(targets):raise ValueError('Incomplete scan target inventory')
    for result in summary['results']:
        if not result.get('complete') or (result['target']!='mcp' and result['status']!='pass'):raise ValueError('Skill scan failed or has findings')
    if issue_signatures(report)!=issue_signatures(baseline):raise ValueError('MCP finding inventory changed; review before release')

def validate(root):
    meta=read(root/'release.json')
    if meta.get('version')!=1 or meta.get('id')!=root.name:raise ValueError('Invalid release metadata')
    if not meta.get('files') or payload(root)!=meta['files']:raise ValueError('Frozen release files changed')
    fingerprint=run(root,sys.executable,'-c','from runtime.security_scan import fingerprint;print(fingerprint())')
    if fingerprint!=meta['source_fingerprint'] or read(root/'deployment.json')['source_fingerprint']!=fingerprint:raise ValueError('Release fingerprint mismatch')
    if not meta.get('bootstrap'):
        summary=read(root/'release-state/security/summary.json')
        if summary.get('fingerprint')!=fingerprint or meta.get('status')!='prepared':raise ValueError('Candidate not prepared')
        for name,pin in (('deployment.json','deployment_sha256'),('release-state/security/summary.json','scan_summary_sha256'),('release-state/security/mcp.json','scan_report_sha256')):
            if checksum(root/name)!=meta.get(pin):raise ValueError('Candidate deployment or scan receipt changed')
    return meta

def stage():
    import _winapi
    identifier=uuid.uuid4().hex;dest=release_path(identifier)
    before=payload(ROOT);dest.mkdir(parents=True)
    for name in DIRECTORIES:shutil.copytree(ROOT/name,dest/name,ignore=shutil.ignore_patterns('__pycache__','approved.build.sqlite'))
    for name in FILES:
        if (ROOT/name).is_file():shutil.copyfile(ROOT/name,dest/name)
    _winapi.CreateJunction(str((ROOT/'data').resolve()),str(dest/'data'))
    _winapi.CreateJunction(str((ROOT/'vendor').resolve()),str(dest/'vendor'))
    if before!=payload(ROOT) or before!=payload(dest):raise ValueError('Checkout changed during snapshot; candidate retained, not activated')
    fingerprint=run(dest,sys.executable,'-c','from runtime.security_scan import fingerprint;print(fingerprint())')
    write(dest/'release.json',{'version':1,'id':identifier,'source_fingerprint':fingerprint,'files':before,'status':'staged'})
    print('Staged '+identifier+'; active release untouched.',flush=True)
    return identifier

def prepare(identifier):
    dest=release_path(identifier);meta=read(dest/'release.json')
    if payload(dest)!=meta['files']:raise ValueError('Candidate changed after staging')
    active=read(STORE/'active.json');old=release_path(active['id'])
    profile=read(old/'deployment.json');profile['agent_name']='larpus-agent-'+identifier
    profile['source_fingerprint']=meta['source_fingerprint']
    # Fixed cache, no download or duplicate GPU model/voice worker.
    linux='/home/larpus/releases/'+identifier
    wsl('/bin/mkdir','-p',linux)
    archive=STORE/(identifier+'.tar')
    with tarfile.open(archive,'w') as tar:
        for name in (*DIRECTORIES,*FILES):
            if (dest/name).exists():tar.add(dest/name,arcname=name,filter=lambda info:None if '__pycache__' in info.name else info)
    with archive.open('rb') as source:wsl('/bin/tar','-xf','-','-C',linux,input_file=source)
    # Runtime wheels already live in the dedicated Linux preparation cache.
    wsl('/bin/mkdir','-p',linux+'/vendor')
    wsl('/bin/cp','-a','/home/larpus/build/vendor/runtime-wheels',linux+'/vendor/runtime-wheels')
    wsl('/usr/bin/env','--chdir='+linux+'/vendor/runtime-wheels','/usr/bin/sha256sum','--strict','--check','SHA256SUMS')
    base=podman('image','inspect','docker.io/library/python:3.12-slim-bookworm','--format','{{.Id}}')
    if not re.fullmatch(r'(?:sha256:)?[a-f0-9]{64}',base):raise ValueError('Invalid cached base image')
    print('Building offline candidate; current gateway remains available.',flush=True)
    podman('build','--pull=never','--network=none','--build-arg','BASE_IMAGE='+base,'-f',linux+'/deploy/windows-home/Containerfile','-t','localhost/larpus-agent:'+identifier,linux)
    profile['agent_image']=podman('image','inspect','localhost/larpus-agent:'+identifier,'--format','{{.Id}}').removeprefix('sha256:')
    podman('run','--detach','--pull=never','--name',profile['agent_name'],'--pod','larpus-offline','--read-only','--read-only-tmpfs=false','--user=1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=64','--memory=1g','--cpus=2','--log-driver=none','--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=128m','--volume=larpus-quarantine:/app/data/quarantine:rw,noexec,nosuid,nodev',profile['agent_image'])
    write(dest/'deployment.json',profile)
    print(run(dest,sys.executable,'scripts/test-local.py'),flush=True)
    for test in ('tests/voice-ui.cjs','tests/chat-stream-ui.cjs','tests/context-ui.cjs'):print(run(dest,'node.exe',test),flush=True)
    print(run(dest,sys.executable,'-m','runtime.isolation','check'),flush=True)
    print('Scanning candidate independently of the active release.',flush=True)
    run(dest,sys.executable,'-c',"import json;from runtime.security_scan import scan,discover,APPROVED;d=discover();assert d==json.loads(APPROVED.read_text())['tools'];r=scan(d);print(r['status'])",timeout=900)
    scan_dir=old/('data/security' if read(old/'release.json').get('bootstrap') else 'release-state/security')
    scan_gate(read(dest/'release-state/security/summary.json'),read(dest/'release-state/security/mcp.json'),read(scan_dir/'mcp.json'),[e['id'] for e in read(dest/'skills/registry.json')['skills']]+['mcp'])
    if payload(dest)!=meta['files']:raise ValueError('Candidate files changed during checks')
    meta.update(status='prepared',deployment_sha256=checksum(dest/'deployment.json'),scan_summary_sha256=checksum(dest/'release-state/security/summary.json'),scan_report_sha256=checksum(dest/'release-state/security/mcp.json'))
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

def launch(identifier,settings):
    root=release_path(identifier);validate(root)
    (root/'release-state/drain').unlink(missing_ok=True)
    env=os.environ.copy();env.update(LARPUS_HOST=settings['host'],LARPUS_LAN_CIDR=settings['subnet'],LARPUS_PORT=str(settings['port']),LARPUS_ISOLATION='wsl-podman',PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
    code='import sys,runpy;sys.path.insert(0,'+repr(str(root))+');runpy.run_module("runtime.gateway",run_name="__main__")'
    with (STORE/(identifier+'.gateway.log')).open('ab') as log:child=subprocess.Popen([sys.executable,'-c',code],cwd=root,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    identity=process(child.pid)
    if not identity:raise RuntimeError('Gateway exited before startup')
    return {**settings,'version':1,'id':identifier,'pid':child.pid,'process':identity}

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
            if required.issubset(checks) and all(checks[n]=='pass' for n in required):return
        except OSError:pass
        time.sleep(.5)
    raise RuntimeError('New gateway functional readiness failed')

def cutover(identifier):
    if (STORE/'pending.json').exists():raise ValueError('Interrupted cutover recorded; run start to recover first')
    root=release_path(identifier);validate(root)
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
    podman('pod','start','larpus-offline');podman('start','larpus-voice')
    podman('start',profile.get('agent_name','larpus-agent'))
    new=launch(state['id'],state);write(STORE/'active.json',new);ready(new)
    print('Started active release '+state['id'])

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=('stage','prepare','activate','rollback','start','status'));parser.add_argument('id',nargs='?');args=parser.parse_args()
    if os.name!='nt':raise SystemExit('Owner Windows release manager required')
    if args.operation=='status':
        state=read(STORE/'active.json');print(json.dumps({'id':state['id'],'running':running(state),'previous':state.get('previous'),'pending':(STORE/'pending.json').exists()},indent=2));return
    with exclusive():
        if args.operation=='stage':stage()
        elif args.operation=='prepare':prepare(args.id)
        elif args.operation=='activate':cutover(args.id)
        elif args.operation=='rollback':cutover(read(STORE/'active.json')['previous'])
        elif args.operation=='start':start()
        else:
            state=read(STORE/'active.json');print(json.dumps({'id':state['id'],'running':running(state),'previous':state.get('previous'),'pending':(STORE/'pending.json').exists()},indent=2))

if __name__=='__main__':main()
