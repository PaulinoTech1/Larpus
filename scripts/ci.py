"""Public checkout checks. Never deploys or reads ignored owner data."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
UI_TESTS=('voice-ui.cjs','chat-stream-ui.cjs','context-ui.cjs','memory-ui.cjs',
          'teaching-ui.cjs','diagnostics-ui.cjs','speech-text.cjs')
PRIVATE_NAMES={'provenance.json','github-manifest.json','embeddings-manifest.json','notes-manifest.json'}

def forbidden(name):
    path=Path(name)
    if path.parts[0] in ('data','vendor'):return True
    if path.suffix.lower() in ('.sqlite','.npy','.gguf','.safetensors','.key','.pem'):return True
    if name=='.env' or path.name.startswith('.env.'):return True
    return path.parts[0]=='knowledge' and (path.name in PRIVATE_NAMES or '.sqlite-' in path.name)

def inventory(root=ROOT):
    result=subprocess.run(['git','ls-files','-z'],cwd=root,capture_output=True,check=True,timeout=30)
    names=result.stdout.decode('utf8').strip('\0').split('\0')
    bad=[name for name in names if name and forbidden(name)]
    if bad:raise ValueError('Private-file boundary failed: '+', '.join(bad))
    print('Public tracked-file boundary passed; this is not a secret-content scanner.',flush=True)

def execute(command):
    print('CHECK '+ ' '.join(command),flush=True)
    subprocess.run(command,cwd=ROOT,check=True,timeout=600)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inventory-only',action='store_true');args=parser.parse_args()
    inventory()
    if args.inventory_only:return 0
    execute([sys.executable,'scripts/test-local.py'])
    for test in UI_TESTS:execute(['node','tests/'+test])
    execute([sys.executable,'scripts/broker-prompts.py','--check'])
    execute([sys.executable,'scripts/evaluate-companion.py'])
    execute([sys.executable,'scripts/evaluate-stegdetect.py'])
    print('Public contracts passed. No deployment or live-system acceptance claimed.',flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
