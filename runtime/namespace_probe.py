"""Fixed, non-secret behavioral checks inside the trusted network-disabled agent."""
import json
import os
import socket
from pathlib import Path
from runtime.dlp import secure_directory,QUARANTINE

def check():
    if os.getuid()!=1000 or {p.name for p in Path('/sys/class/net').iterdir()}!={'lo'}:
        raise ValueError('Unexpected identity or network interface')
    status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    if int(status['CapEff'].strip(),16) or int(status['CapBnd'].strip(),16) or status['NoNewPrivs'].strip()!='1':
        raise ValueError('Process capability/privilege protection missing')
    for ip in ('1.1.1.1','192.168.1.1'):
        try:
            with socket.create_connection((ip,443),timeout=1):
                pass
        except OSError:
            continue
        raise ValueError('External/LAN connection succeeded')
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        try:
            sock.sendto(b'larpus-denial-probe',('1.1.1.1',53))
        except OSError:
            pass
        else:
            raise ValueError('External DNS/UDP send succeeded')
    for path in ('/mnt/c','/mnt/e','/run/podman/podman.sock','/var/run/docker.sock'):
        if Path(path).exists():
            raise ValueError('Host drive or container control socket present')
    secure_directory()
    if QUARANTINE.stat().st_mode & 0o077:
        raise ValueError('Quarantine is not owner-only')
    broker=Path(__file__).resolve().parents[1]/'config/inference-broker.json'
    if broker.exists() and json.loads(broker.read_text()).get('enabled') is True:
        if json.loads(broker.read_text()).get('version')==2:
            if Path('/run/larpus-notes').exists():raise ValueError('Agent has background capability')
            from runtime.local_ollama import broker_status
            if broker_status()['faulted']:raise ValueError('Broker cancellation fence failed; inference closed')
        try:
            with socket.create_connection(('127.0.0.1',11434),timeout=2):pass
        except OSError:pass
        else:raise ValueError('Agent can bypass inference broker')
        from runtime.local_ollama import ollama
        if not ollama('/api/tags',timeout=2).get('models'):raise ValueError('Broker model unavailable')
    else:
        with socket.create_connection(('127.0.0.1',11434),timeout=2):pass
    return {'raw_ollama_denied':broker.exists(),'denied_external_and_lan':True,'denied_dns_udp':True,'local_ollama':True,'host_paths_absent':True,'quarantine_owner_only':True,'effective_and_bounding_capabilities_zero':True}

if __name__=='__main__':
    print(json.dumps(check()))
