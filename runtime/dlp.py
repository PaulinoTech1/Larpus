"""Fail-closed output gate and owner-only inert quarantine; no web release path."""
import argparse
import base64
import json
import os
import re
import subprocess
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from runtime.skills import ROOT

POLICY=ROOT/'config/dlp.json'
QUARANTINE=ROOT/'data/quarantine'
RULES=(
    ('credential_token', re.compile(r'\bAKIA[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9]{20,}\b|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b')),
    ('credential', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:api[_ -]?key|access[_ -]?token|password|secret)["\x27]?\s*[:=]\s*["\x27]?[^\s"\x27]{8,}',re.I)),
    ('private_address', re.compile(r'\b(?:127|10)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b|\b192\.168\.\d{1,3}\.\d{1,3}\b|\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b|\blocalhost\b|(?<!\w)::1(?!\w)|\b(?:fc|fd)[0-9a-f]{2}:[0-9a-f:]+',re.I)),
    ('local_path', re.compile(r'[a-z]:[\\/]|\\\\[^\s\\]+\\|/(?:home|root|etc|var|Users|mnt|run|tmp)/',re.I)),
)

def policy():
    value=json.loads(POLICY.read_text(encoding='utf-8'))
    if set(value)!={'version','private_values','max_output_bytes','max_quarantine_bytes','max_records'} or value['version']!=1:
        raise ValueError('Invalid DLP policy')
    if not isinstance(value['private_values'],list) or len(value['private_values'])>128 or any(not isinstance(s,str) or not 4<=len(s)<=4096 for s in value['private_values']):
        raise ValueError('Invalid private values')
    for key,maximum in (('max_output_bytes',65536),('max_quarantine_bytes',67108864),('max_records',1024)):
        if type(value[key]) is not int or not 1<=value[key]<=maximum:
            raise ValueError('Invalid DLP limits')
    return value

def shadow(text):
    return ' '.join(unicodedata.normalize('NFKC',text).casefold().split())

def inspect_output(text,system_prompt='',settings=None):
    settings=settings or policy()
    if not isinstance(text,str) or len(text.encode('utf-8'))>settings['max_output_bytes']:
        return ['output_limit']
    reasons=[]
    normalized=unicodedata.normalize('NFKC',text)
    if any(unicodedata.category(c) in ('Cf','Cc') and c not in '\n\r\t' for c in normalized):
        reasons.append('hidden_control')
    for reason,pattern in RULES:
        if pattern.search(normalized):
            reasons.append(reason)
    protected=[str(ROOT),str(Path.home())]+settings['private_values']
    protected += [line.strip() for line in system_prompt.splitlines() if len(line.strip())>=40]
    folded=shadow(text)
    for value in protected:
        if shadow(value) in folded:
            reasons.append('protected_value')
            break
        encoded=base64.b64encode(value.encode()).decode()
        if encoded in text or value.encode().hex() in text.casefold():
            reasons.append('encoded_protected_value')
            break
    return sorted(set(reasons))

def secure_directory():
    for path in (QUARANTINE.parent,QUARANTINE):
        if path.exists() and (path.is_symlink() or (os.name=='nt' and path.stat().st_file_attributes & 1024)):
            raise OSError('Quarantine reparse point rejected')
    QUARANTINE.mkdir(parents=True,exist_ok=True,mode=0o700)
    if os.name=='nt':
        executable=Path(os.environ['SYSTEMROOT'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
        subprocess.run([str(executable),'-NoProfile','-NonInteractive','-File',str(ROOT/'scripts/protect-quarantine.ps1'),'-Target',str(QUARANTINE)],shell=False,check=True,capture_output=True,timeout=10)
    else:
        QUARANTINE.chmod(0o700)
        if QUARANTINE.stat().st_uid!=os.getuid():
            raise OSError('Quarantine owner mismatch')

def gate(text,system_prompt=''):
    try:
        settings=policy()
        # Reject oversized output before writing unbounded evidence.
        if not isinstance(text,str) or len(text.encode('utf-8'))>settings['max_output_bytes']:
            return {'status':422,'error':'Output held by local DLP.'}
        secure_directory()
        files=list(QUARANTINE.iterdir())
        if any(not f.is_file() or f.is_symlink() for f in files):
            raise OSError('Unexpected quarantine artifact')
        record={'id':uuid.uuid4().hex,'created_at':datetime.now(timezone.utc).isoformat(),'state':'staged','output':text}
        raw=json.dumps(record,ensure_ascii=True).encode()
        if len(files)>=settings['max_records'] or sum(f.stat().st_size for f in files)+len(raw)+1024>settings['max_quarantine_bytes']:
            raise OSError('Quarantine capacity exceeded')
        staged=QUARANTINE/(record['id']+'.json')
        descriptor=os.open(staged,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(descriptor,'wb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        reasons=inspect_output(text,system_prompt,settings)
        if reasons:
            record.update({'state':'held','reasons':reasons})
            with staged.open('w',encoding='utf-8') as stream:
                json.dump(record,stream,ensure_ascii=True);stream.flush();os.fsync(stream.fileno())
            return {'status':422,'error':'Output held by local DLP for owner investigation.','incident':record['id']}
        staged.unlink()  # Clean content is released only after deletion succeeds.
        return {'status':200,'content':text}
    except Exception:
        return {'status':503,'error':'Local output inspection unavailable. Response withheld.'}

def main():
    parser=argparse.ArgumentParser(description='Owner-side quarantine inspection; never executes output')
    parser.add_argument('operation',choices=('list','inspect','delete'))
    parser.add_argument('incident',nargs='?')
    args=parser.parse_args()
    secure_directory()
    if args.operation=='list':
        for path in sorted(QUARANTINE.glob('*.json')):
            print(path.stem)
        return
    if not args.incident or not re.fullmatch(r'[0-9a-f]{32}',args.incident):
        parser.error('Exact incident ID required')
    path=QUARANTINE/(args.incident+'.json')
    if path.is_symlink() or path.stat().st_size>400000:
        raise SystemExit('Invalid evidence')
    if args.operation=='delete':
        path.unlink()
    else:
        # ASCII JSON escaping prevents terminal control-sequence execution.
        record=json.loads(path.read_text(encoding='utf-8'))
        print(json.dumps(record,ensure_ascii=True,indent=2))

if __name__=='__main__':
    main()
