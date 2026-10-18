import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('notes_resilience',ROOT/'scripts/study-notes.py')
notes=importlib.util.module_from_spec(spec);spec.loader.exec_module(notes)
from scripts import notes_diagnostics as nd

TRUNCATED={'ok':'{"facts":[','metrics':{'done_reason':'length'}}
def reply(text):
    quote=text.strip()[:60]
    return {'ok':json.dumps({'facts':[{'claim':'A claim.','quote':quote}]}),'metrics':{'done_reason':'stop'}}

class Resilience(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory();self.addCleanup(self.dir.cleanup)
        self.root=patch.object(notes,'BUILD',Path(self.dir.name)/'b.sqlite');self.root.start();self.addCleanup(self.root.stop)
        self.out=patch('sys.stdout',io.StringIO());self.log=self.out.start();self.addCleanup(self.out.stop)
        self.db=notes.build_db();self.addCleanup(self.db.close)
        self.text=('First paragraph sentence about block ciphers and their modes of operation. '*6+'\n\n'+
                   'Second paragraph sentence about key schedules and diffusion properties here. '*6)

    def run_window(self,infer):
        return notes.process_window(self.db,'k1','src','T','u','page 50 offset 0',self.text,infer)

    def test_truncation_counts_then_split_then_skip(self):
        calls=[]
        def infer(passage):
            calls.append(passage)
            # Whole window and second half always truncate; first half succeeds.
            if passage.startswith('First') and len(passage)<len(self.text):return reply(passage)
            return TRUNCATED
        status,kept=self.run_window(infer)
        self.assertEqual((status,kept),('done',1))
        self.assertEqual(notes.truncation_count(self.db,'k1'),3)
        self.assertEqual(calls[:3],[self.text]*3)
        first,second=notes.split_half(self.text)
        self.assertTrue(first.rstrip().endswith('.') and second.startswith('Second'))
        self.assertEqual(calls[3:],[first]+[second]*3)
        rows=dict(self.db.execute('SELECT key,kept FROM done'))
        self.assertEqual(rows,{'k1':1,'k1:h1':1,'k1:h2':0})
        self.assertEqual(self.db.execute('SELECT reason FROM truncations WHERE key=?',('k1:h2',)).fetchone()[0],notes.SKIP_REASON)
        self.assertEqual(self.db.execute('SELECT key FROM notes').fetchall(),[('k1',)])
        self.assertIn(notes.SKIP_REASON,self.log.getvalue())

    def test_truncation_counts_persist_across_restarts(self):
        count=[0]
        def boom(passage):
            count[0]+=1
            if count[0]>2:return {'error':'worker-unavailable'}
            return TRUNCATED
        self.assertEqual(self.run_window(boom)[0],'error')
        self.assertEqual(notes.truncation_count(self.db,'k1'),2)
        calls=[]
        def infer(passage):calls.append(passage);return TRUNCATED if passage==self.text else reply(passage)
        self.assertEqual(self.run_window(infer)[0],'done')
        self.assertEqual(calls[0],self.text);self.assertEqual(len(calls),3)  # one more full try, then halves

    def test_publish_gate_counts_skipped_windows_done(self):
        self.run_window(lambda p:TRUNCATED)
        self.db.execute('INSERT INTO done VALUES(?,?,?)',('k2',3,0));self.db.commit()
        status=notes.progress(self.db,[('k1',),('k2',)])
        self.assertEqual(status['windows_pending'],0)
        self.assertEqual(status['units_skipped'],2)

    def test_overlap_removed_and_keys_stable(self):
        a='Alpha beta gamma delta epsilon zeta eta theta iota.'
        b='zeta eta theta iota. Kappa lambda mu nu xi omicron.'
        joined=notes.join_chunk(notes.join_chunk('',a),b)
        self.assertEqual(joined,a+'\n Kappa lambda mu nu xi omicron.\n')
        self.assertEqual(notes.overlap('abc the','the end'),0)  # short accidental match ignored
        self.assertEqual(notes.overlap('x'*500+'y'*450,'y'*450),400)
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'knowledge').mkdir()
            c=sqlite3.connect(Path(d)/'knowledge/approved.sqlite')
            c.execute('CREATE TABLE chunks(source_id,title,url,locator,text)')
            c.executemany('INSERT INTO chunks VALUES(?,?,?,?,?)',[('s','T','u','doc offset 0',a),('s','T','u','doc offset 30',b)]);c.commit();c.close()
            with patch.object(notes,'ROOT',Path(d)),patch.object(notes,'provenance_entries',return_value={}),patch.object(notes,'chronology',return_value=0),patch.object(notes,'appended_windows',return_value=([],{})):
                (key,_,_,_,loc,text),=list(notes.windows(None))
        legacy=notes.hashlib.sha256(('s|doc offset 0|'+a+'\n'+b+'\n').encode()).hexdigest()[:32]
        self.assertEqual(key,legacy)
        self.assertEqual(text.count('zeta eta theta iota.'),1)

    def test_diagnostics_redact_cap_and_rotate(self):
        d=Path(self.dir.name)/'diag'
        for i in range(5):
            path=nd.write(d,{'code':'LARP-NOTES-TRANSPORT','exception_message':'token=abc123SECRET'},
                          {'model_log_tail':'Authorization: Bearer sk-ABCDEFGHIJKLMNOPQRSTUV\n'+'x'*200000,'gpu':'10 MiB'},keep=3,max_bytes=8000)
        files=list(d.glob('notes-transport-*.json'))
        self.assertEqual(len(files),3)
        body=path.read_text(encoding='utf-8')
        self.assertLessEqual(len(body.encode()),8000)
        self.assertNotIn('abc123SECRET',body);self.assertNotIn('sk-ABCDEF',body)
        self.assertEqual(json.loads(body)['sections']['gpu'],'10 MiB')

    def test_worker_failure_writes_pointer_without_job_content(self):
        with patch.object(notes,'ROOT',Path(self.dir.name)),patch.object(notes.subprocess,'Popen',side_effect=OSError('spawn failed')),patch.object(notes.time,'sleep'):
            worker=notes.NotesWorker('agent')
            worker.request({'messages':[{'content':'SECRET PASSAGE'}]},notes.time.time()+30)
        files=list((Path(self.dir.name)/'data/diagnostics').glob('*.json'))
        self.assertEqual(len(files),3)
        self.assertIn('diagnostic_file',self.log.getvalue())
        self.assertNotIn('SECRET PASSAGE',''.join(f.read_text(encoding='utf-8') for f in files))

if __name__=='__main__':unittest.main()
