import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

spec=importlib.util.spec_from_file_location('notes_recovery',Path(__file__).resolve().parents[1]/'scripts/study-notes.py')
notes=importlib.util.module_from_spec(spec);spec.loader.exec_module(notes)

class RecoveryTests(unittest.TestCase):
    def process(self,output):
        process=Mock(stdin=io.StringIO(),stdout=io.StringIO(output))
        process.stdin.close=lambda:None
        return process

    def test_eof_retries_same_job_and_keeps_success_metrics(self):
        first=self.process('');second=self.process(json.dumps({'ok':'{}','metrics':{'eval_count':7}})+'\n')
        job={'model':'local','messages':[{'role':'user','content':'original passage'}]}
        with tempfile.TemporaryDirectory() as directory,patch.object(notes,'ROOT',Path(directory)),patch.object(notes.subprocess,'Popen',side_effect=[first,second]),patch.object(notes.time,'sleep'),patch('sys.stdout',io.StringIO()):
            worker=notes.NotesWorker('agent')
            reply=worker.request(job,notes.time.time()+30)
            self.assertEqual(reply['metrics']['eval_count'],7)
            self.assertEqual(first.stdin.getvalue(),second.stdin.getvalue())
            self.assertIsNotNone(worker.errors)
            worker.close();self.assertIsNone(worker.errors)

    def test_failures_are_bounded_and_expired_deadline_never_starts(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(notes,'ROOT',Path(directory)),patch.object(notes.subprocess,'Popen',side_effect=lambda *a,**k:self.process('')) as launch,patch.object(notes.time,'sleep'),patch('sys.stdout',io.StringIO()):
            worker=notes.NotesWorker('agent')
            self.assertEqual(worker.request({},notes.time.time()+30),{'error':'worker-unavailable'})
            self.assertEqual(launch.call_count,3)
            self.assertEqual(worker.request({},0),{'error':'worker-unavailable'})
            self.assertEqual(launch.call_count,3)

    def test_writer_lock_rejects_other_process_then_releases(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(notes,'ROOT',Path(directory)):
            code="import importlib.util; from pathlib import Path; s=importlib.util.spec_from_file_location('n',"+repr(str(Path(notes.__file__)))+"); n=importlib.util.module_from_spec(s);s.loader.exec_module(n);n.ROOT=Path("+repr(directory)+");exec('with n.writer_lock(): pass')"
            with notes.writer_lock():
                result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('Another study-notes writer',result.stderr)
            result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
