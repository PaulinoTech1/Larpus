"""Windows Home WSL2/rootless-Podman stdio executor; never falls back to host."""
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from runtime.skills import ROOT

PROFILE=ROOT/'deployment.json' if (ROOT/'deployment.json').is_file() else ROOT/'data/isolated-deployment.json'
DISTRO='Larpus'
USER='larpus'
AGENT='larpus-agent'
MODEL='larpus-model'

def agent_name(profile):
    name=profile.get('agent_name',AGENT)
    if not isinstance(name,str) or not re.fullmatch(r'larpus-agent(?:-[a-f0-9]{32})?',name):
        raise ValueError('Invalid sealed agent identity')
    return name

def mode():
    value=os.environ.get('LARPUS_ISOLATION')
    if value is None:
        configured=json.loads((ROOT/'config/isolation.json').read_text(encoding='utf-8'))
        if configured.get('version')!=1:
            raise ValueError('Invalid isolation selection')
        value=configured.get('mode')
    if value not in ('host','wsl-podman'):
        raise ValueError('Unknown isolation mode; refusing fallback')
    return value

def wsl_command(*args):
    if os.name!='nt':
        raise OSError('Windows WSL executor required')
    executable=Path(os.environ['SYSTEMROOT'])/'System32/wsl.exe'
    if args and args[0]=='podman':
        args=('/usr/bin/env','XDG_RUNTIME_DIR=/run/user/1000','/usr/bin/podman',*args[1:])
    return [str(executable),'--distribution',DISTRO,'--user',USER,'--exec',*args]

def query(*args):
    result=subprocess.run(wsl_command('podman',*args),capture_output=True,timeout=15,check=True)
    if len(result.stdout)>1_000_000:
        raise ValueError('Oversized isolation response')
    return json.loads(result.stdout.decode('utf-8'))

def read_oci(item):
    identifier=item['Id']
    if not re.fullmatch(r'[a-f0-9]{64}',identifier):
        raise ValueError('Invalid container ID')
    path=f'/home/larpus/.local/share/containers/storage/overlay-containers/{identifier}/userdata/config.json'
    if item.get('OCIConfigPath')!=path:
        raise ValueError('Unexpected OCI configuration path')
    result=subprocess.run(wsl_command('/usr/bin/cat',path),capture_output=True,timeout=10,check=True)
    if len(result.stdout)>1_000_000:
        raise ValueError('Oversized OCI configuration')
    return json.loads(result.stdout.decode())

def read_oci_many(items):
    """Overlap independent WSL reads; validate every result before execution.

    No cached isolation decisions: each request still reads current OCI data,
    and any failed read rejects the entire preflight.
    """
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(read_oci,items))

def selection_mounts(expected,source):
    return expected|{('/run/larpus-selection',False)} if source else expected
def validate_private_mount(mount,broker_volume,notes_volume,selection_source):
    if mount['Destination']=='/run/larpus-selection':
        if mount['Type']!='bind' or mount['Source']!=selection_source:raise ValueError('Invalid model selection mount')
        return
    name=broker_volume if mount['Destination']=='/run/larpus-broker' else notes_volume
    if mount['Type']!='volume' or mount.get('Name')!=name or not {'noexec','nosuid','nodev'}.issubset(set(mount.get('Options',[]))):raise ValueError('Invalid private broker volume')
def validate_selection_source(profile,broker):
    if profile.get('model_selection') and (not broker or profile['model_selection']!='/home/larpus/release-selection/'+broker['container'].removeprefix('larpus-broker-')):raise ValueError('Invalid owner selection source')

def validate_container(item,expected_image,is_model,oci=None,gpu_driver=None,broker_volume=None,broker_only=False,notes_volume=None,notes_only=False,selection_source=None):
    host=item['HostConfig']
    if item['State']['Running'] is not True or item['Image'].removeprefix('sha256:')!=expected_image.removeprefix('sha256:'):
        raise ValueError('Container stopped or image drifted')
    if host.get('ReadonlyRootfs') is not True or host.get('Privileged') or host.get('PortBindings'):
        raise ValueError('Container filesystem, privilege or ports violate isolation')
    if host.get('PidMode')=='host' or host.get('IpcMode')=='host':
        raise ValueError('Host process namespaces prohibited')
    all_dropped='ALL' in {str(v).upper().removeprefix('CAP_') for v in host.get('CapDrop',[])}
    empty_caps=all(key in item and item[key] in (None,[]) for key in ('EffectiveCaps','BoundingCaps'))
    if not (all_dropped or empty_caps):
        raise ValueError('Capabilities not dropped')
    if not any(str(v) in ('no-new-privileges','no-new-privileges:true') for v in host.get('SecurityOpt',[])):
        raise ValueError('Privilege escalation protection missing')
    if host.get('Memory',0)<=0 or host.get('PidsLimit',0)<=0:
        raise ValueError('Container resource limits missing')
    mounts={(m['Destination'],m.get('RW',False)) for m in item.get('Mounts',[]) if m['Type']!='tmpfs'}
    expected={('/models',False),('/usr/lib/wsl/lib',False)} if is_model else {('/app/data/quarantine',True)}
    if broker_volume:
        expected={('/run/larpus-broker',True)} if broker_only else expected|{('/run/larpus-broker',False)}
    if notes_volume and broker_only:expected.add(('/run/larpus-notes',True))
    if notes_only:expected={('/run/larpus-notes',False)}
    expected=selection_mounts(expected,selection_source)
    if is_model and gpu_driver:
        expected.add((gpu_driver,False))
    if mounts!=expected or len([m for m in item.get('Mounts',[]) if m['Type']!='tmpfs'])!=len(expected):
        raise ValueError('Unexpected model or quarantine mounts')
    for mount in item.get('Mounts',[]):
        if mount['Type']=='tmpfs':
            continue
        if is_model:
            expected_source={'/models':'/home/larpus/models','/usr/lib/wsl/lib':'/usr/lib/wsl/lib',gpu_driver:gpu_driver}[mount['Destination']]
            if mount['Type']!='bind' or mount['Source']!=expected_source:
                raise ValueError('Unexpected model mount source')
        elif mount['Destination'] in ('/run/larpus-broker','/run/larpus-notes','/run/larpus-selection'):
            validate_private_mount(mount,broker_volume,notes_volume,selection_source)
        elif mount['Type']!='volume' or mount.get('Name')!='larpus-quarantine':
            raise ValueError('Agent quarantine must use the dedicated named volume')
        elif not {'noexec','nosuid','nodev'}.issubset(set(mount.get('Options',[]))):
            raise ValueError('Quarantine mount safety options missing')
    devices=host.get('Devices',[])
    expected_devices={'/dev/dxg'} if is_model else set()
    actual_devices={device['PathOnHost'] for device in devices}
    if oci is not None:
        if oci['root'].get('readonly') is not True or oci['process'].get('noNewPrivileges') is not True:
            raise ValueError('OCI filesystem/privilege drift')
        if any(oci['process'].get('capabilities',{}).get(key) for key in ('effective','bounding','permitted','inheritable','ambient')):
            raise ValueError('OCI capabilities remain enabled')
        standard={'/dev/null','/dev/zero','/dev/full','/dev/random','/dev/urandom','/dev/tty'}
        bound={m['source'] for m in oci['mounts'] if m.get('type')=='bind' and m.get('source','').startswith('/dev/')}-standard
        if bound!=expected_devices:
            raise ValueError('Unexpected OCI device bindings')
        # Rootless Podman 4.9 records --device as an OCI bind, not HostConfig.Devices.
        if not devices:
            actual_devices=bound
    if actual_devices!=expected_devices:
        raise ValueError('Unexpected GPU/host devices')
    if not is_model and item['Config'].get('User')!='1000:1000':
        raise ValueError('Trusted agent must use non-root container identity')

def preflight():
    profile=json.loads(PROFILE.read_text(encoding='utf-8-sig'))
    if profile.get('version')!=1 or profile.get('distro')!=DISTRO or profile.get('user')!=USER:
        raise ValueError('Dedicated deployment profile missing or invalid')
    gpu_driver=profile.get('gpu_driver','')
    if not isinstance(gpu_driver,str) or not re.fullmatch(r'/usr/lib/wsl/drivers/nv_[a-z0-9]+\.inf_amd64_[a-f0-9]{16}',gpu_driver):
        raise ValueError('Narrow NVIDIA driver package pin required')
    from runtime.security_scan import fingerprint
    if profile.get('source_fingerprint')!=fingerprint():
        raise ValueError('Host sources changed since isolated image build; reseal deployment')
    distro_probe="import pathlib,configparser; c=configparser.ConfigParser();c.read('/etc/wsl.conf');assert not c.getboolean('automount','enabled');assert not c.getboolean('automount','mountFsTab');assert not c.getboolean('interop','enabled');assert not c.getboolean('interop','appendWindowsPath');assert not pathlib.Path('/mnt/c').exists();assert not pathlib.Path('/mnt/e').exists();assert not pathlib.Path('/proc/sys/fs/binfmt_misc/WSLInterop').exists()"
    subprocess.run(wsl_command('python3','-c',distro_probe),capture_output=True,check=True,timeout=10)
    info=query('info','--format','json')
    if info['host']['security']['rootless'] is not True:
        raise ValueError('Rootful Podman prohibited')
    selected_agent=agent_name(profile)
    broker=profile.get('broker')
    notes=profile.get('notes')
    if broker:
        required={'container','image','volume'}|({'protocol','notes_volume'} if broker.get('protocol')==2 else set())
        if set(broker)!=required or not re.fullmatch(r'larpus-broker-[a-f0-9]{32}',broker['container']) or broker['volume']!=broker['container'] or not re.fullmatch(r'[a-f0-9]{64}',broker['image']):
            raise ValueError('Invalid pinned broker')
        if broker.get('protocol')==2:
            if broker['notes_volume']!=broker['container']+'-notes' or not isinstance(notes,dict) or set(notes)!={'container','image','volume'} or notes['volume']!=broker['notes_volume'] or not re.fullmatch(r'larpus-notes-[a-f0-9]{32}',notes['container']) or not re.fullmatch(r'[a-f0-9]{64}',notes['image']):raise ValueError('Invalid notes capability pin')
    validate_selection_source(profile,broker)
    broker_policy=ROOT/'config/inference-broker.json'
    if broker_policy.exists() and json.loads(broker_policy.read_text())['version']==2 and (not broker or broker.get('protocol')!=2):raise ValueError('Scoped broker deployment required')
    containers=query('inspect',selected_agent,MODEL,*([broker['container']] if broker else []),*([notes['container']] if notes else []))
    by_name={c['Name'].lstrip('/'):c for c in containers}
    oci_by_name=dict(zip(by_name,read_oci_many(list(by_name.values()))))
    agent,model=by_name[selected_agent],by_name[MODEL]
    validate_container(agent,profile['agent_image'],False,oci_by_name[selected_agent],broker_volume=broker['volume'] if broker else None)
    validate_container(model,profile['model_image'],True,oci_by_name[MODEL],gpu_driver)
    if broker:
        guard=by_name[broker['container']]
        validate_container(guard,broker['image'],False,oci_by_name[broker['container']],broker_volume=broker['volume'],broker_only=True,notes_volume=broker.get('notes_volume'),selection_source=profile.get('model_selection'))
        if agent.get('Pod') or agent['HostConfig']['NetworkMode']!='none' or not model.get('Pod') or guard.get('Pod')!=model['Pod']:
            raise ValueError('Broker/agent namespace separation drift')
        if broker.get('protocol')==2:
            worker=by_name[notes['container']]
            validate_container(worker,notes['image'],False,oci_by_name[notes['container']],notes_volume=notes['volume'],notes_only=True)
            if worker.get('Pod') or worker['HostConfig']['NetworkMode']!='none' or 'LARPUS_BROKER_ROLE=notes' not in worker['Config'].get('Env',[]):raise ValueError('Notes namespace/capability drift')
            if 'OLLAMA_NUM_PARALLEL=1' not in model['Config'].get('Env',[]):raise ValueError('Cancellation fence requires pinned single-slot runner')
    elif not agent.get('Pod') or agent['Pod']!=model.get('Pod'):
        raise ValueError('Inference and guard are not in the same isolated pod')
    pod=query('pod','inspect',model['Pod'])
    if pod['InfraConfig']['HostNetwork'] or pod['InfraConfig']['Networks']:
        raise ValueError('Pod has external networking')
    infra=query('inspect',pod['InfraContainerID'])[0]
    if infra['HostConfig']['NetworkMode']!='none':
        raise ValueError('Pod must have network=none')
    if any(c['HostConfig']['NetworkMode']!='container:'+pod['InfraContainerID'] for c in ((guard,model) if broker else (agent,model))):
        raise ValueError('Container network namespace drift')
    return profile

def child_args():
    profile=preflight()
    return wsl_command('podman','exec','--interactive',agent_name(profile),'python','-m','runtime.mcp_server')

def check_behavior():
    profile=preflight()
    result=subprocess.run(wsl_command('podman','exec',agent_name(profile),'python','-m','runtime.namespace_probe'),capture_output=True,check=True,timeout=10)
    value=json.loads(result.stdout.decode())
    if profile.get('notes'):
        result=subprocess.run(wsl_command('podman','exec',profile['notes']['container'],'python','-m','runtime.notes_worker','--probe'),capture_output=True,check=True,timeout=10)
        if json.loads(result.stdout.decode()).get('notes_capability_only') is not True:raise ValueError('Notes capability probe failed')
        value['notes_capability_only']=True
    return value

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('operation',choices=('check','quarantine'))
    parser.add_argument('arguments',nargs='*')
    args=parser.parse_args()
    if args.operation=='check':
        print(json.dumps(check_behavior(),indent=2))
    else:
        if not args.arguments or args.arguments[0] not in ('list','inspect','delete'):
            parser.error('Use quarantine list, inspect ID, or delete ID')
        profile=preflight()
        subprocess.run(wsl_command('podman','exec',agent_name(profile),'python','-m','runtime.dlp',*args.arguments),check=True)

if __name__=='__main__':
    main()
