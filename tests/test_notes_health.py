import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('notes_health',Path(__file__).resolve().parents[1]/'scripts/notes-health.py')
health=importlib.util.module_from_spec(spec);spec.loader.exec_module(health)

class HealthTests(unittest.TestCase):
    def fixture(self,root,lines):
        (root/'knowledge').mkdir();(root/'data').mkdir()
        with sqlite3.connect(root/'knowledge/notes.build.sqlite') as db:
            db.execute('CREATE TABLE done(key TEXT,at REAL)');db.execute("INSERT INTO done VALUES('saved',990)")
            db.execute('CREATE TABLE notes(text TEXT)');db.execute("INSERT INTO notes VALUES('fact')")
        (root/'data/study-notes.log').write_text('launcher message\n'+''.join(json.dumps(e)+'\n' for e in lines)+'{partial',encoding='utf-8')

    def test_saved_progress_and_successful_timings_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.fixture(root,[{'seconds':20,'metrics':{'done_reason':'stop'}},{'seconds':999,'metrics':{}},{'seconds':40,'metrics':{'done_reason':'stop'}},{'kept':8}])
            r=health.report(root,1000)
            self.assertEqual(r['windows_done'],1);self.assertEqual(r['notes'],1)
            self.assertEqual(r['median_successful_request_seconds'],30)
            self.assertEqual(r['status'],'recent_progress')
            self.assertEqual(health.report(root,2000)['status'],'needs_check')

    def test_last_error_visible_until_next_saved_window(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.fixture(root,[{'kept':10},{'worker_error':'worker-exit'}])
            self.assertEqual(health.report(root,1000)['status'],'recovery_or_failure')
            with (root/'data/study-notes.log').open('a') as f:f.write('\n'+json.dumps({'kept':12})+'\n')
            self.assertEqual(health.report(root,1000)['status'],'recent_progress')

    def test_missing_database_is_unknown_and_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.assertEqual(health.report(root)['status'],'unknown')
            self.assertFalse((root/'knowledge/notes.build.sqlite').exists())

if __name__=='__main__':unittest.main()
