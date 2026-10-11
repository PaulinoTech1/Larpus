"""Minimal notes-only stdio worker. No corpus, DLP volume, GPU or chat socket."""
import json
import sys
import os
import socket
from pathlib import Path
from runtime.local_ollama import ollama,BrokerRejected

def probe():
    if os.getuid()!=1000 or {p.name for p in Path('/sys/class/net').iterdir()}!={'lo'}:raise ValueError('Notes identity/network drift')
    for path in ('/run/larpus-broker','/app/knowledge','/app/data/quarantine','/mnt/c','/mnt/e','/run/podman/podman.sock','/var/run/docker.sock'):
        if Path(path).exists():raise ValueError('Unexpected notes capability')
    status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    if int(status['CapEff'].strip(),16) or int(status['CapBnd'].strip(),16) or status['NoNewPrivs'].strip()!='1':raise ValueError('Notes privilege drift')
    for address in ('127.0.0.1','1.1.1.1','192.168.1.1'):
        try:
            with socket.create_connection((address,11434 if address=='127.0.0.1' else 443),timeout=1):pass
        except OSError:continue
        raise ValueError('Notes raw network reachable')
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        try:sock.sendto(b'larpus-denial-probe',('1.1.1.1',53))
        except OSError:pass
        else:raise ValueError('Notes DNS/UDP reachable')
    if not ollama('/api/tags',timeout=3).get('models'):raise ValueError('Notes broker unavailable')
    return {'notes_capability_only':True,'raw_and_external_denied':True,'host_paths_absent':True}

def main():
    policy=json.loads((Path(__file__).resolve().parents[1]/'config/inference-broker.json').read_text())
    for line in sys.stdin:
        try:
            if len(line.encode())>524288:raise ValueError('Job too large')
            job=json.loads(line)
            if not isinstance(job,dict) or set(job)-{'model','messages','num_predict'}:raise ValueError('Invalid job')
            result=ollama('/api/chat',{'model':job['model'],'messages':job['messages'],'stream':False,'think':False,
                'format':'json','keep_alive':-1,'options':{'temperature':0.2,'num_ctx':policy['context'],
                'num_predict':job.get('num_predict',2400),'num_gpu':99}},timeout=210)
            metrics={key:result.get(key) for key in ('total_duration','load_duration','prompt_eval_count','prompt_eval_duration','eval_count','eval_duration','done_reason')}
            reply={'ok':result['message']['content'],'metrics':metrics}
        except BrokerRejected as exc:reply={'error':'broker-held','code':exc.code,'http_status':exc.status}
        except Exception as exc:reply={'error':type(exc).__name__}
        print(json.dumps(reply),flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['--probe']:print(json.dumps(probe()))
    else:main()
