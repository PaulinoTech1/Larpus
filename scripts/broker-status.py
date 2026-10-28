"""Owner-only read-only status of the active release broker; no generation/recovery."""
import json
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime.isolation import agent_name,wsl_command

ROOT=Path(__file__).resolve().parents[1]
CLIENT="import json;from runtime.local_ollama import broker_status;print(json.dumps(broker_status()))"

def status(root=ROOT):
    state=json.loads((root/'data/releases/active.json').read_text(encoding='utf-8-sig'))
    identifier=state['id']
    if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{32}',identifier):
        raise ValueError('Invalid active release ID')
    profile=json.loads((root/'data/releases'/identifier/'deployment.json').read_text(encoding='utf-8-sig'))
    if profile.get('broker',{}).get('protocol')!=2:raise ValueError('Broker status requires protocol 2')
    result=subprocess.run(wsl_command('podman','exec',agent_name(profile),'python','-c',CLIENT),capture_output=True,check=True,timeout=15)
    if len(result.stdout)>8192:raise ValueError('Oversized broker status')
    value=json.loads(result.stdout)
    if not isinstance(value,dict) or type(value.get('faulted')) is not bool or value.get('scope')!='broker-admission':
        raise ValueError('Invalid broker status')
    # Keep this owner diagnostic limited to admission metadata.
    fields=('scope','active','received_frame','waiting_chat','faulted','preemptions','confirmed_recoveries')
    return {'release_id':identifier,'broker':{key:value[key] for key in fields if key in value}}

def main():
    try:print(json.dumps(status(),indent=2))
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        print('Broker status unavailable: '+type(exc).__name__+'. Run from owner PowerShell with WSL access; no recovery was attempted.',file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
