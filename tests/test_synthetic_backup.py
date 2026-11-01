import errno
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.synthetic_backup import export_sqlite, restore_sqlite

def source():
    directory=tempfile.TemporaryDirectory()
    path=Path(directory.name)/'live.sqlite'
    connection=sqlite3.connect(path)
    connection.execute('CREATE TABLE records(id INTEGER PRIMARY KEY, body TEXT)')
    connection.execute('INSERT INTO records VALUES (1,?)',('committed',))
    connection.commit()
    return directory,path,connection

class SyntheticBackupTests(unittest.TestCase):
    def test_restore_keeps_committed_rows_and_drops_an_open_write(self):
        directory,path,connection=source();self.addCleanup(directory.cleanup)
        connection.execute('INSERT INTO records VALUES (2,?)',('uncommitted',))
        key=hashlib.sha256(b'synthetic-test-key').digest()
        with tempfile.TemporaryDirectory() as backup,tempfile.TemporaryDirectory() as restored:
            export_sqlite(path,Path(backup)/'bundle',key)
            restore_sqlite(Path(backup)/'bundle',Path(restored)/'copy.sqlite',key)
            rows=sqlite3.connect(Path(restored)/'copy.sqlite').execute('SELECT id,body FROM records').fetchall()
        self.assertEqual(rows,[(1,'committed')])

    def test_corrupt_partial_and_full_disk_do_not_replace_the_source(self):
        directory,path,connection=source();self.addCleanup(directory.cleanup);connection.close()
        before=path.read_bytes();key=b'k'*32
        with tempfile.TemporaryDirectory() as backup:
            bundle=Path(backup)/'bundle'
            export_sqlite(path,bundle,key)
            (bundle/'backup.sqlite').write_bytes(b'truncated')
            with self.assertRaises(ValueError):restore_sqlite(bundle,Path(backup)/'copy.sqlite',key)
            manifest=(bundle/'manifest.json').read_bytes()
            (bundle/'manifest.json').write_bytes(manifest[:-1]+b'0')
            with self.assertRaises(ValueError):restore_sqlite(bundle,Path(backup)/'copy.sqlite',key)
        with patch('scripts.synthetic_backup.os.replace',side_effect=OSError(errno.ENOSPC,'No space')):
            with self.assertRaises(OSError):export_sqlite(path,Path(directory.name)/'full',key)
        self.assertEqual(path.read_bytes(),before)
