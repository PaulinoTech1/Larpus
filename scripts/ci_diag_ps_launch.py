"""TEMPORARY CI diagnostic: time protect-quarantine.ps1 launches from a child whose stdin is an open pipe (like the MCP child)."""
import json,os,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PS=str(Path(os.environ['SYSTEMROOT'])/'System32/WindowsPowerShell/v1.0/powershell.exe')
def child():
    target=Path(tempfile.mkdtemp(prefix='larpus-diag-'))
    base=[PS,'-NoProfile','-NonInteractive','-File',str(ROOT/'scripts/protect-quarantine.ps1'),'-Target',str(target)]
    variants={
     'inherit_stdin':dict(),
     'stdin_devnull':dict(stdin=subprocess.DEVNULL),
     'create_no_window':dict(creationflags=subprocess.CREATE_NO_WINDOW),
     'devnull_no_window':dict(stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW),
     'inherit_stdin_again':dict(),
    }
    for name,extra in variants.items():
        start=time.monotonic()
        try:
            r=subprocess.run(base,shell=False,capture_output=True,timeout=40,**extra);result=r.returncode
        except subprocess.TimeoutExpired:result='timeout'
        print(json.dumps({'variant':name,'seconds':round(time.monotonic()-start,2),'result':result}),file=sys.stderr,flush=True)
if __name__=='__main__':
    if sys.argv[1:]==['--child']:child();raise SystemExit
    # Parent: keep the child's stdin as an open, silent pipe, as the MCP client does.
    p=subprocess.Popen([sys.executable,__file__,'--child'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    p.wait(timeout=400);p.stdin.close();print('child exit',p.returncode)
