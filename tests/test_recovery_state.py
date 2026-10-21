import errno
import json
import os
from pathlib import Path
import tempfile
import unittest
from dataclasses import replace
from unittest.mock import patch
from scripts.recovery_policy import History
from scripts.recovery_state import Journal, StateError
from tests.test_recovery_policy import IDENTITY

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'recovery'
        self.journal=Journal(self.path,protect=lambda p,**kw:None)

    def test_absent_journal_is_disabled_and_corrupt_journal_holds(self):
        self.assertFalse(self.journal.read().armed)
        self.journal.write(History())
        for raw in ('null','{}','x'*65537,json.dumps({'version':2})):
            self.journal.path.write_text(raw)
            with self.assertRaises(StateError):self.journal.read()

    def test_failed_replace_preserves_previous_commit_and_prevents_launch(self):
        self.journal.set_armed(True);before=self.journal.path.read_bytes()
        with patch('scripts.recovery_state.os.replace',side_effect=OSError(errno.ENOSPC,'synthetic full disk')):
            with self.assertRaises(StateError):self.journal.reserve(IDENTITY,1000,0)
        self.assertEqual(self.journal.path.read_bytes(),before)
        self.assertEqual(self.journal.read().attempts,())

    def test_restart_retains_reservation_budget_and_owner_disable(self):
        self.journal.set_armed(True)
        token=self.journal.reserve(IDENTITY,1000,3)
        restarted=Journal(self.path,protect=lambda p,**kw:None)
        self.assertEqual(restarted.read().attempts,(1000.,))
        self.assertEqual(restarted.read().next_attempt_wall_time,1063)
        self.assertEqual(restarted.read().reservation['id'],token)
        self.assertEqual(restarted.read().reservation['expected']['pid'],IDENTITY.pid)
        restarted.record_launch(token,replace(IDENTITY,pid=124))
        self.assertEqual(restarted.read().reservation['launched']['pid'],124)
        restarted.set_armed(False);self.assertFalse(self.journal.read().armed)
        self.assertIsNotNone(self.journal.read().reservation)

    def test_budget_and_clock_are_enforced_at_reservation(self):
        self.journal.set_armed(True)
        token=self.journal.reserve(IDENTITY,1000,0)
        self.journal.finish('recovered')
        for now in (999,1059):
            with self.assertRaises(StateError):self.journal.reserve(IDENTITY,now,0)
        self.journal.reserve(IDENTITY,1060,0);self.journal.finish('recovered')
        with self.assertRaises(StateError):self.journal.reserve(IDENTITY,1120,0)
        self.assertEqual(len(self.journal.read().attempts),2)

    def test_singleton_excludes_a_second_owner(self):
        with self.journal.singleton():
            with self.assertRaises(StateError):
                with Journal(self.path,protect=lambda p,**kw:None).singleton():pass

    def test_redirected_path_and_invalid_reservation_reject(self):
        self.journal.write(History())
        value=json.loads(self.journal.path.read_text());value['reservation']={'id':'anything'}
        self.journal.path.write_text(json.dumps(value))
        with self.assertRaises(StateError):self.journal.read()
        with patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaises(StateError):self.journal.read()

    def test_acl_failure_prevents_persistence(self):
        journal=Journal(self.path,protect=lambda p,**kw:(_ for _ in ()).throw(OSError('denied')))
        with self.assertRaises(StateError):journal.set_armed(True)
        self.assertFalse(journal.path.exists())

    def test_boolean_schema_version_is_rejected(self):
        self.journal.write(History())
        value=json.loads(self.journal.path.read_text());value['version']=True
        self.journal.path.write_text(json.dumps(value))
        with self.assertRaises(StateError):self.journal.read()

    @unittest.skipUnless(os.name=='nt','Windows ACL contract')
    def test_real_windows_acl_adapter(self):
        journal=Journal(self.path)
        journal.write(History())
        self.assertEqual(journal.read(),History())


