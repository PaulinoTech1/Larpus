"""TEMPORARY CI diagnostic (round 2): time protect-quarantine.ps1 launches with the MCP child's allowlisted environment."""
import json,os,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PS=str(Path(os.environ['SYSTEMROOT'])/'System32/WindowsPowerShell/v1.0/powershell.exe')
ALLOW=('SYSTEMROOT','WINDIR','PATH','TEMP','TMP','HOME','USERPROFILE')
def run(name,env,**extra):
    target=Path(tempfile.mkdtemp(prefix='larpus-diag-'))
    base=[PS,'-NoProfile','-NonInteractive','-File',str(ROOT/'scripts/protect-quarantine.ps1'),'-Target',str(target)]
    start=time.monotonic()
    try:
        r=subprocess.run(base,shell=False,capture_output=True,timeout=60,env=env,**extra);result=[r.returncode,r.stderr.decode(errors='replace')[-300:]]
    except subprocess.TimeoutExpired:result='timeout'
    print(json.dumps({'variant':name,'seconds':round(time.monotonic()-start,2),'result':result}),file=sys.stderr,flush=True)
def child():
    full=dict(os.environ)
    mini={k:full[k] for k in ALLOW if k in full}
    print(json.dumps({'missing_vs_full':sorted(set(full)-set(mini))}),file=sys.stderr,flush=True)
    run('full_env',full);run('full_env_again',full)
    run('allowlist',mini);run('allowlist_again',mini)
    for key in ('LOCALAPPDATA','APPDATA','PSModulePath','ProgramFiles','PROGRAMDATA','PATHEXT','COMSPEC','SystemDrive','USERNAME','COMPUTERNAME','PROCESSOR_ARCHITECTURE'):
        if key in full or key.upper() in {k.upper() for k in full}:
            v=next(full[k] for k in full if k.upper()==key.upper());run('allowlist+'+key,{**mini,key:v})
    run('allowlist+devnull',mini,stdin=subprocess.DEVNULL)
if __name__=='__main__':
    if sys.argv[1:]==['--child']:child();raise SystemExit
    p=subprocess.Popen([sys.executable,__file__,'--child'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    p.wait(timeout=900);p.stdin.close();print('child exit',p.returncode)
