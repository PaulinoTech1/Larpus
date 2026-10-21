"""Bounded encrypted SQLite snapshots. Owner-only staging; never overwrites targets."""
from contextlib import contextmanager,closing
import calendar
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
import time
from scripts.recovery_state import safe_path, protect_directory

MAGIC=b'LARPUS-SQLITE-AESGCM-1\n'
MAX_BYTES=64*1024*1024
DEFAULT_DIRECTORY=Path('D:/LARPUS-Backups')

def _cipher(key):
    if type(key) is not bytes or len(key)!=32:raise ValueError('A 32-byte backup key is required')
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    return AESGCM(key)

@contextmanager
def _staging(parent):
    safe_path(parent)
    with tempfile.TemporaryDirectory(prefix='.larpus-backup-',dir=parent) as directory:
        path=Path(directory);protect_directory(path,initialize=True)
        yield path

def _target(path):
    path=Path(path).absolute();safe_path(path)
    if path.exists():raise ValueError('Destination already exists')
    if not path.parent.is_dir():raise ValueError('Destination parent must exist')
    return path

def _read(path,limit):
    safe_path(path)
    with Path(path).open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError('Backup size limit exceeded')
    return raw

def _write(path,raw):
    with path.open('xb') as stream:
        os.chmod(path,0o600)
        stream.write(raw);stream.flush();os.fsync(stream.fileno())

def _integrity(path):
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite integrity rejected')

def _snapshot(source,target):
    safe_path(source);deadline=time.monotonic()+60
    def progress(status,remaining,total):
        if time.monotonic()>deadline:raise TimeoutError('SQLite backup deadline exceeded')
        if total*page_size>MAX_BYTES:raise ValueError('Backup size limit exceeded')
    with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True,timeout=1)) as src:
        with closing(sqlite3.connect(target)) as dst:
            page_size=src.execute('PRAGMA page_size').fetchone()[0]
            src.backup(dst,pages=32,progress=progress,sleep=.05);dst.commit()
    _integrity(target)

def _payload(raw):
    metadata={'version':1,'algorithm':'AES-256-GCM','id':secrets.token_hex(16),
              'created_ns':time.time_ns(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    header=json.dumps(metadata,sort_keys=True,separators=(',',':')).encode()
    return metadata,len(header).to_bytes(4,'big')+header+raw

def _decode(bundle,key):
    cipher=_cipher(key);envelope=_read(bundle,MAX_BYTES+4096)
    if not envelope.startswith(MAGIC):raise ValueError('Backup format rejected')
    start=len(MAGIC)
    from cryptography.exceptions import InvalidTag
    try:clear=cipher.decrypt(envelope[start:start+12],envelope[start+12:],MAGIC)
    except (InvalidTag,ValueError):raise ValueError('Backup authentication rejected') from None
    size=int.from_bytes(clear[:4],'big')
    if not 1<=size<=2048:raise ValueError('Backup header rejected')
    metadata=json.loads(clear[4:4+size]);raw=clear[4+size:]
    _validate_metadata(metadata,raw)
    return metadata,raw

def _validate_metadata(metadata,raw):
    if not isinstance(metadata,dict) or set(metadata)!={'version','algorithm','id','created_ns','bytes','sha256'}:
        raise ValueError('Backup metadata rejected')
    _format(metadata)
    if type(metadata['created_ns']) is not int or metadata['created_ns']<=0:raise ValueError('Backup chronology rejected')
    if type(metadata['bytes']) is not int or metadata['bytes']!=len(raw) or len(raw)>MAX_BYTES:
        raise ValueError('Backup length rejected')
    if metadata['sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('Backup digest rejected')
    if not isinstance(metadata['id'],str) or len(metadata['id'])!=32:raise ValueError('Backup identity rejected')

def _format(metadata):
    if type(metadata['version']) is not int or metadata['version']!=1 or metadata['algorithm']!='AES-256-GCM':
        raise ValueError('Backup version rejected')

def export_sqlite(source,destination,key):
    cipher=_cipher(key);target=_target(destination);source=Path(source).absolute()
    with _staging(target.parent) as staging:
        snapshot=staging/'snapshot.sqlite';_snapshot(source,snapshot)
        metadata,payload=_payload(_read(snapshot,MAX_BYTES));nonce=secrets.token_bytes(12)
        encrypted=staging/'encrypted';_write(encrypted,MAGIC+nonce+cipher.encrypt(nonce,payload,MAGIC))
        # Hard-link publication is create-only on supported filesystems. No unsafe rename fallback.
        safe_path(target);os.link(encrypted,target)
    return metadata

def restore_sqlite(bundle,destination,key):
    target=_target(destination);metadata,raw=_decode(Path(bundle),key)
    with _staging(target.parent) as staging:
        snapshot=staging/'restore.sqlite';_write(snapshot,raw);_integrity(snapshot)
        safe_path(target);os.link(snapshot,target)
    return metadata

def retention_cutoff(now):
    if now.tzinfo is None:raise ValueError('Retention requires an aware clock')
    month_index=now.year*12+now.month-1-3
    year,month=divmod(month_index,12);month+=1
    return now.replace(year=year,month=month,day=min(now.day,calendar.monthrange(year,month)[1]))

def retention_plan(paths,key,*,keep,now=None):
    """Authenticate explicit artifacts and propose retention; never delete anything."""
    _cipher(key)
    if type(keep) is not int or keep<1:raise ValueError('Retain at least one backup')
    if not isinstance(paths,(list,tuple)) or len(paths)>1000:raise ValueError('Retention inventory limit')
    entries=[(_decode(Path(path),key)[0],str(Path(path).absolute())) for path in paths]
    if len({m['id'] for m,p in entries})!=len(entries):raise ValueError('Duplicate backup identity')
    ordered=sorted(entries,key=lambda row:(row[0]['created_ns'],row[0]['id']),reverse=True)
    cutoff=int(retention_cutoff(now or datetime.now(timezone.utc)).timestamp()*1e9)
    return _retention_result(ordered,keep,cutoff)

def _retention_result(ordered,keep,cutoff):
    retain=[p for i,(m,p) in enumerate(ordered) if i<keep or m['created_ns']>=cutoff]
    return {'retain':retain,'eligible':[p for m,p in ordered if p not in retain],'action':'plan-only'}
