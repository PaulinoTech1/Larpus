"""Reproduce public synthetic broker tests locally, producing a bounded JSON receipt."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
FILES=('runtime/inference_broker.py','runtime/broker_scheduler.py','runtime/local_ollama.py','tests/test_broker_scheduling.py')

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--require-unix',action='store_true');args=p.parse_args()
    started=time.monotonic()
    if args.require_unix and not hasattr(__import__('socketserver'),'UnixStreamServer'):raise SystemExit('Linux Unix-socket tests required')
    with tempfile.TemporaryDirectory(prefix='larpus-public-broker-') as directory:
        workspace=Path(directory)
        hashes={}
        for name in FILES:
            raw=(ROOT/name).read_bytes();hashes[name]=hashlib.sha256(raw).hexdigest()
            dest=workspace/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        commands=[]
        for pattern in ('test_broker_scheduling.py',):
            result=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-p',pattern,'-v'],cwd=workspace,capture_output=True,text=True,timeout=45)
            output=(result.stdout+result.stderr)[-16000:]
            commands.append({'test':pattern,'exit':result.returncode,'output':output})
    try:
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
        dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip())
    except (OSError,subprocess.CalledProcessError):commit=None;dirty=None
    report={'schema':'larpus.broker-verification/v1','kind':'synthetic-public-fixtures','commit':commit,
            'working_tree_dirty':dirty,
            'python':platform.python_version(),'platform':sys.platform,'unix_tests_required':args.require_unix,
            'unix_socket_verification':'tested' if hasattr(__import__('socketserver'),'UnixStreamServer') else 'not_checked',
            'files_sha256':hashes,'seconds':round(time.monotonic()-started,3),'tests':commands,
            'pass':all(c['exit']==0 for c in commands),
            'limits':'No owner data, models or internet. Receipt hashes identify exact files, not a signed independent attestation. Synthetic tests do not prove a deployed GPU, OCI mounts, Windows reboot or physical HUD.'}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'pass':report['pass'],'kind':report['kind'],'platform':report['platform'],'report':str(args.output)}))
    return 0 if report['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
