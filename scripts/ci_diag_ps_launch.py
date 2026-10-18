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
    print(json.dumps({'runner_PSModulePath':full.get('PSMODULEPATH')}),file=sys.stderr,flush=True)
    inbox=str(Path(full['SYSTEMROOT'])/'system32/WindowsPowerShell/v1.0/Modules')
    pf=str(Path(full['SYSTEMROOT']).drive+'\\')+'Program Files\\WindowsPowerShell\\Modules'
    run('allowlist',mini)
    run('allowlist+inbox_only',{**mini,'PSModulePath':inbox})
    run('allowlist+inbox_only_again',{**mini,'PSModulePath':inbox})
    run('allowlist+inbox_only+e22523d_flags',{**mini,'PSModulePath':inbox},creationflags=subprocess.CREATE_NO_WINDOW)
    run('allowlist+programfiles+inbox',{**mini,'PSModulePath':pf+os.pathsep+inbox})
    run('allowlist+empty_PSModulePath',{**mini,'PSModulePath':''})
    run('allowlist+runner_PSModulePath',{**mini,'PSModulePath':full.get('PSMODULEPATH','')})

if __name__=='__main__':
    if sys.argv[1:]==['--child']:child();raise SystemExit
    p=subprocess.Popen([sys.executable,__file__,'--child'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    p.wait(timeout=900);p.stdin.close();print('child exit',p.returncode)
