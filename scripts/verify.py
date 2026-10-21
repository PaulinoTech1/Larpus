"""One offline checkout gate, shared by developers and public CI; never deploys."""
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.ui_checks import TESTS as UI_TESTS

ROOT=Path(__file__).resolve().parents[1]

def commands(python=None,node=None):
    python=python or sys.executable;node=node or shutil.which('node')
    if not node:raise ValueError('Node is required for the HUD verification suites')
    return [[python,'scripts/complexity.py','check'],[python,'scripts/test-local.py'],
            *[[node,'tests/'+test] for test in UI_TESTS],
            [python,'scripts/broker-prompts.py','--check'],[python,'scripts/quality_evaluation.py','--check']]

def main():
    try:
        for command in commands():
            print('CHECK '+' '.join(command),flush=True)
            subprocess.run(command,cwd=ROOT,check=True,timeout=900)
    except subprocess.CalledProcessError as exc:return exc.returncode or 1
    except (OSError,ValueError,subprocess.TimeoutExpired):
        print('Verification unavailable or timed out; gate remains failed.',file=sys.stderr);return 2
    print('Offline verification passed; no production or answer-quality acceptance claimed.');return 0

if __name__=='__main__':raise SystemExit(main())
