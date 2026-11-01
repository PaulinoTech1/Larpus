"""Consistent SQLite export for synthetic drills. Not owner-key custody or a live restore."""
import hashlib
import hmac
import json
import os
import sqlite3
from pathlib import Path

def _digest(path):
    hasher=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):hasher.update(block)
    return hasher.hexdigest()

def _manifest(digest,size,key):
    if not isinstance(key,bytes) or len(key)<32:raise ValueError('Backup key required')
    body=json.dumps({'version':1,'sha256':digest,'bytes':size},separators=(',',':')).encode()
    return body,hmac.new(key,body,hashlib.sha256).hexdigest()

def export_sqlite(source,destination,key):
    """Copy committed rows only. An uncommitted writer on the source is not included."""
    source=Path(source);destination=Path(destination)
    if destination.exists():raise ValueError('Backup destination exists')
    destination.mkdir()
    database=destination/'backup.sqlite'
    src=sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        dst=sqlite3.connect(database)
        try:
            src.backup(dst);dst.commit()
            if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup integrity failed')
        finally:dst.close()
    finally:src.close()
    body,mac=_manifest(_digest(database),database.stat().st_size,key)
    temporary=destination/'manifest.json.tmp'
    temporary.write_bytes(body+b'\n'+mac.encode())
    os.replace(temporary,destination/'manifest.json')
    return {'sha256':_digest(database),'bytes':database.stat().st_size}

def restore_sqlite(backup,destination,key):
    backup=Path(backup);destination=Path(destination)
    if destination.exists():raise ValueError('Restore destination exists')
    body,mac=(backup/'manifest.json').read_bytes().split(b'\n',1)
    expected_body,expected_mac=_manifest(json.loads(body)['sha256'],json.loads(body)['bytes'],key)
    if not hmac.compare_digest(mac.decode(),expected_mac) or body!=expected_body:raise ValueError('Backup manifest rejected')
    database=backup/'backup.sqlite'
    if _digest(database)!=json.loads(body)['sha256'] or database.stat().st_size!=json.loads(body)['bytes']:
        raise ValueError('Backup payload rejected')
    destination.parent.mkdir(parents=True,exist_ok=True)
    src=sqlite3.connect(database)
    try:
        if src.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup integrity failed')
        dst=sqlite3.connect(destination)
        try:src.backup(dst);dst.commit()
        finally:dst.close()
    finally:src.close()
    return {'sha256':_digest(destination)}
