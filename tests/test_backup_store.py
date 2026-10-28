import errno
import os
from datetime import datetime,timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from scripts import backup_store as backup

class BackupStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source.sqlite';self.key=b'k'*32
        with sqlite3.connect(self.source) as db:
            db.execute('CREATE TABLE records(id PRIMARY KEY, body)')
            db.execute('INSERT INTO records VALUES(1,?)',('private committed payload',))
        self.bundle=self.root/'snapshot.larpus'

    def test_encrypted_separate_location_restore_only_committed_rows(self):
        connection=sqlite3.connect(self.source);self.addCleanup(connection.close)
        connection.execute('INSERT INTO records VALUES(2,?)',('not committed',))
        receipt=backup.export_sqlite(self.source,self.bundle,self.key)
        self.assertNotIn(b'private committed payload',self.bundle.read_bytes())
        self.assertNotIn(b'SQLite format',self.bundle.read_bytes())
        restore=self.root/'separate'/'restore.sqlite';restore.parent.mkdir()
        backup.restore_sqlite(self.bundle,restore,self.key)
        with sqlite3.connect(restore) as db:self.assertEqual(db.execute('SELECT id FROM records').fetchall(),[(1,)])
        self.assertEqual(receipt['algorithm'],'AES-256-GCM')
        self.assertFalse(any(p.name.startswith('.larpus-backup-') for p in self.root.iterdir()))

    def test_wrong_key_tampering_and_existing_targets_are_refused(self):
        backup.export_sqlite(self.source,self.bundle,self.key)
        target=self.root/'restored.sqlite'
        with self.assertRaises(ValueError):backup.restore_sqlite(self.bundle,target,b'x'*32)
        self.assertFalse(target.exists())
        raw=self.bundle.read_bytes();self.bundle.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        with self.assertRaises(ValueError):backup.restore_sqlite(self.bundle,target,self.key)
        target.write_bytes(b'previous commit')
        with self.assertRaises(ValueError):backup.restore_sqlite(self.bundle,target,self.key)
        self.assertEqual(target.read_bytes(),b'previous commit')

    def test_full_disk_or_publish_race_never_leaves_partial_target(self):
        before=self.source.read_bytes()
        with patch.object(backup.os,'link',side_effect=OSError(errno.ENOSPC,'full')):
            with self.assertRaises(OSError):backup.export_sqlite(self.source,self.bundle,self.key)
        self.assertFalse(self.bundle.exists());self.assertEqual(self.source.read_bytes(),before)
        backup.export_sqlite(self.source,self.bundle,self.key)
        target=self.root/'target.sqlite'
        def race(source,destination):
            Path(destination).write_bytes(b'concurrent commit');raise FileExistsError()
        with patch.object(backup.os,'link',side_effect=race):
            with self.assertRaises(FileExistsError):backup.restore_sqlite(self.bundle,target,self.key)
        self.assertEqual(target.read_bytes(),b'concurrent commit')
        self.assertFalse(any(p.name.startswith('.larpus-backup-') for p in self.root.iterdir()))

    def test_key_and_retention_policy_fail_closed_without_deleting(self):
        with self.assertRaises(ValueError):backup.export_sqlite(self.source,self.bundle,b'short')
        self.assertFalse(self.bundle.exists())
        backup.export_sqlite(self.source,self.bundle,self.key)
        other=self.root/'second.larpus';backup.export_sqlite(self.source,other,self.key)
        with self.assertRaises(ValueError):backup.retention_plan([self.bundle,other],self.key,keep=0)
        plan=backup.retention_plan([self.bundle,other],self.key,keep=1,now=datetime(2100,1,1,tzinfo=timezone.utc))
        self.assertEqual(len(plan['retain']),1);self.assertEqual(len(plan['eligible']),1)
        self.assertTrue(all(p.exists() for p in (self.bundle,other)))

    def test_owner_policy_retains_three_calendar_months_and_one_verified_copy(self):
        self.assertEqual(backup.DEFAULT_DIRECTORY,Path('D:/LARPUS-Backups'))
        now=datetime(2026,5,31,tzinfo=timezone.utc)
        cutoff=backup.retention_cutoff(now)
        self.assertEqual(cutoff,datetime(2026,2,28,tzinfo=timezone.utc))
        backup.export_sqlite(self.source,self.bundle,self.key)
        plan=backup.retention_plan([self.bundle],self.key,keep=1,now=now)
        self.assertEqual(plan['eligible'],[])

    def test_private_permissions_are_set_before_plaintext_publication(self):
        path=self.root/'private-output'
        with patch.object(backup.os,'chmod',wraps=backup.os.chmod) as chmod:
            backup._write(path,b'private fixture')
        chmod.assert_called_once_with(path,0o600)
        if os.name!='nt':self.assertEqual(path.stat().st_mode&0o077,0)

