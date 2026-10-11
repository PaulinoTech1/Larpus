"""Fixed offline voice container; no user-selected executable, path or URL."""
import json
import hashlib
import subprocess
import threading
import re
import time
from runtime.agents import ROOT
from runtime.isolation import query, read_oci, wsl_command

LOCK=threading.Lock()
PROFILE=ROOT/('voice-deployment.json' if (ROOT/'voice-deployment.json').is_file() else 'data/voice-deployment.json')

def preflight():
    profile=json.loads(PROFILE.read_text(encoding='utf-8-sig'))
    if profile.get('version')!=1 or profile.get('worker_sha256')!=hashlib.sha256((ROOT/'runtime/voice_worker.py').read_bytes()).hexdigest():
        raise ValueError('Voice worker source changed; rebuild voice image')
    name=profile.get('container','larpus-voice')
    if not re.fullmatch(r'larpus-voice(?:-[a-f0-9]{32})?',name):raise ValueError('Invalid voice identity')
    item=query('inspect',name)[0]
    host=item['HostConfig']
    if item['Image']!=profile['image'] or not item['State']['Running']:
        raise ValueError('Voice image drift or stopped worker')
    if host.get('NetworkMode')!='none' or host.get('PortBindings') or host.get('Privileged') or not host.get('ReadonlyRootfs'):
        raise ValueError('Voice boundary violated')
    mounts=[m for m in item['Mounts'] if m['Type']!='tmpfs']
    if len(mounts)!=1 or mounts[0]['Type']!='bind' or mounts[0]['Source']!='/home/larpus/voice-models' or mounts[0]['Destination']!='/models' or mounts[0]['RW']:
        raise ValueError('Unexpected voice mounts')
    if item['Config'].get('User')!='1000:1000' or host.get('Memory',0)<=0 or host.get('PidsLimit',0)<=0:
        raise ValueError('Voice identity/resource limits missing')
    oci=read_oci(item)
    if not oci['root'].get('readonly') or not oci['process'].get('noNewPrivileges') or any(oci['process'].get('capabilities',{}).values()):
        raise ValueError('Voice privileges violated')
    if host.get('Devices') or any(m.get('type')=='bind' and m.get('source','').startswith('/dev/') and m['source'] not in {'/dev/null','/dev/zero','/dev/full','/dev/random','/dev/urandom','/dev/tty'} for m in oci['mounts']):
        raise ValueError('Voice host devices prohibited')

def call(request):
    if not LOCK.acquire(blocking=False):
        raise OSError('Voice worker busy')
    try:
        start=time.monotonic();preflight();profile=json.loads(PROFILE.read_text(encoding='utf-8-sig'))
        arguments=['podman','exec','--interactive',profile.get('container','larpus-voice'),'python','/app/voice_worker.py']
        if profile.get('protocol')=='unix-persistent':arguments.append('--client')
        result=subprocess.run(wsl_command(*arguments),input=json.dumps(request).encode(),capture_output=True,timeout=120,check=True)
        if len(result.stdout)>16000000:
            raise ValueError('Voice response too large')
        reply=json.loads(result.stdout)
        if not isinstance(reply,dict) or 'error' in reply:
            raise ValueError('Invalid voice response')
        reply.setdefault('timing',{})['gateway_ms']=round((time.monotonic()-start)*1000)
        return reply
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:
        raise OSError('Local voice unavailable; no cloud fallback.') from exc
    finally:
        LOCK.release()
