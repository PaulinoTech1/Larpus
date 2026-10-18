"""Private, bounded transport diagnostics for the study-notes builder.

Writes one timestamped JSON file per failure under data/diagnostics/, capped in size and
rotated to the newest KEEP files. Never receives note content or prompts; every captured
string is passed through redact() and truncated before it is written.
"""
from datetime import datetime,timezone
import json,os,re,subprocess
from pathlib import Path

KEEP=50
MAX_BYTES=64*1024
SECTION=12000
PREFIX='notes-transport-'
SECRET=[re.compile(p) for p in (
    r'(?i)\b(authorization|bearer|token|api[_-]?key|secret|password|passwd|cookie|session)\b\s*[:=]\s*\S+',
    r'(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}',
    r'\bsk-[A-Za-z0-9_-]{16,}',r'\bgh[pousr]_[A-Za-z0-9]{20,}',r'\bxox[abpr]-[A-Za-z0-9-]{10,}',
    r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(-----END [A-Z ]*PRIVATE KEY-----|$)',
    r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}')]

def redact(text,limit=SECTION):
    text=str(text or '')
    for pattern in SECRET:text=pattern.sub('[redacted]',text)
    return text[-limit:] if len(text)>limit else text

def tail_file(path,limit=4000):
    try:
        with open(path,'rb') as f:
            f.seek(0,os.SEEK_END);size=f.tell();f.seek(max(0,size-limit))
            return f.read().decode('utf-8','replace')
    except OSError as exc:return 'unavailable: '+type(exc).__name__

def run(command,timeout=20):
    try:
        r=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        return (r.stdout or '')+(('\n[stderr]\n'+r.stderr) if r.stderr else '')
    except Exception as exc:return 'unavailable: '+type(exc).__name__

def wsl(*args):return ['wsl','-d','Larpus','-u','larpus','-e',*args]

def collect(agent,worker_log,runner=run,model='larpus-model'):
    """Gather bounded environment state; no prompts, notes or stdin are ever touched."""
    return {
        'worker_stderr_tail':tail_file(worker_log),
        'model_log_tail':runner(wsl('podman','logs','--tail','200',model)),
        'worker_container_state':runner(wsl('podman','inspect','--format',
            '{{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}} restarts={{.RestartCount}}',agent)),
        'model_container_state':runner(wsl('podman','inspect','--format',
            '{{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}} restarts={{.RestartCount}}',model)),
        'gpu':runner(['nvidia-smi','--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu','--format=csv,noheader']),
    }

def write(directory,event,sections,keep=KEEP,max_bytes=MAX_BYTES):
    """Write a redacted, size-capped diagnostic file and prune to the newest `keep`."""
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc)
    record={'schema':'larpus.notes-transport-diagnostic/v1','time':now.isoformat(),
            'event':{k:redact(v,500) for k,v in event.items()},
            'sections':{k:redact(v) for k,v in sections.items()},
            'omitted':'Prompts, passages, note content and credentials are never captured.'}
    body=json.dumps(record,ensure_ascii=False,indent=1)
    while len(body.encode('utf-8'))>max_bytes and any(record['sections'].values()):
        biggest=max(record['sections'],key=lambda k:len(record['sections'][k]))
        s=record['sections'][biggest];record['sections'][biggest]='[cut]'+s[len(s)//2:] if len(s)>64 else ''
        body=json.dumps(record,ensure_ascii=False,indent=1)
    body=body.encode('utf-8')[:max_bytes].decode('utf-8','ignore')
    path=directory/(PREFIX+now.strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    path.write_text(body,encoding='utf-8')
    try:
        if os.name!='nt':os.chmod(path,0o600)
    except OSError:pass
    files=sorted(directory.glob(PREFIX+'*.json'))
    for old in files[:-keep] if keep>0 else []:
        try:old.unlink()
        except OSError:pass
    return path
