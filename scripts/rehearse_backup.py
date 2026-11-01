"""Disposable encrypted restore on D:. No owner database or persisted key is used."""
import json
from contextlib import closing
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.backup_store import DEFAULT_DIRECTORY,export_sqlite,restore_sqlite,retention_plan
from scripts.recovery_state import safe_path,protect_directory

def rehearse(directory=DEFAULT_DIRECTORY):
    directory=Path(directory);safe_path(directory)
    fresh=not directory.exists();directory.mkdir(parents=True,exist_ok=True)
    protect_directory(directory,initialize=fresh)
    key=secrets.token_bytes(32);started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='synthetic-restore-',dir=directory) as temporary:
        root=Path(temporary);protect_directory(root,initialize=True)
        source=root/'synthetic.sqlite';target=root/'restored';target.mkdir()
        with closing(sqlite3.connect(source)) as db:
            db.execute('CREATE TABLE records(id INTEGER PRIMARY KEY, value TEXT)')
            db.executemany('INSERT INTO records VALUES(?,?)',[(1,'synthetic one'),(2,'synthetic two')])
            db.commit()
        bundle=root/'synthetic.larpus';export_sqlite(source,bundle,key)
        restore_sqlite(bundle,target/'copy.sqlite',key)
        with closing(sqlite3.connect(target/'copy.sqlite')) as db:ids=[row[0] for row in db.execute('SELECT id FROM records ORDER BY id')]
        plan=retention_plan([bundle],key,keep=1)
        if ids!=[1,2] or plan['eligible']:raise ValueError('Synthetic restore contract failed')
    return {'state':'passed','committed_before':2,'committed_after':len(ids),'record_ids':ids,
            'seconds':time.monotonic()-started,'cleanup':'passed','scope':'synthetic-only; in-memory ephemeral key; no owner-data recovery proof'}

def main():
    print(json.dumps(rehearse()));return 0

if __name__=='__main__':raise SystemExit(main())
