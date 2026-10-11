import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, Mock

from runtime import knowledge

spec=importlib.util.spec_from_file_location('study_notes_throughput',Path(__file__).resolve().parents[1]/'scripts/study-notes.py')
notes=importlib.util.module_from_spec(spec)
spec.loader.exec_module(notes)


class NotesThroughputTests(unittest.TestCase):
    def test_fact_grounding_preserves_exact_quote_and_conditions(self):
        quote='This method works only when the matrix is invertible.'
        kept=notes.ground(json.dumps({'facts':[{'claim':quote,'quote':quote}]}),quote)
        self.assertEqual(kept,[('fact','',quote,quote,quote)])
        self.assertEqual(notes.ground('{"facts":[]}',quote),[])
        self.assertEqual(notes.ground(json.dumps({'facts':[{'claim':'Unsupported','quote':'This invented passage is not in the original source.'}]}),quote),[])
        with self.assertRaises(json.JSONDecodeError):notes.ground('broken',quote)

    def test_same_source_reuse_keeps_each_locator_and_author_identifier(self):
        with tempfile.TemporaryDirectory() as d,patch.object(notes,'BUILD',Path(d)/'build.sqlite'):
            db=notes.build_db()
            quote='An exact quoted passage with enough characters to retain.'
            db.execute('INSERT INTO notes VALUES(?,?,?,?,?,?,?,?,?,?)',('old','source','Title','https://example.org','page 1','fact','',quote,quote,quote))
            db.commit()
            self.assertEqual(notes.duplicate_notes(db,'old','new','source','Title','https://example.org','page 9'),1)
            row=db.execute('SELECT source_id,url,locator,quote FROM notes WHERE key="new"').fetchone()
            self.assertEqual(row,('source','https://example.org','page 9',quote))
            self.assertEqual(notes.duplicate_notes(db,'old','other','another-source','Other','https://example.net','page 2'),0)
            db.close()
        with patch.object(knowledge,'_AUTHORS',{'source':'Author, 2026'}):
            self.assertEqual(knowledge.author_cite('source'),'Author, 2026')

    def test_generator_reuses_only_identical_same_source_and_keeps_errors_retryable(self):
        text='This exact original passage contains enough characters for a valid quote.'
        windows=[('old','source','Title','url','page 1',text),
                 ('duplicate','source','Title','url','page 2',text),
                 ('different-author','other','Title','url','page 3',text),
                 ('different-text','source','Title','url','page 4',text+' More.'),
                 ('bad','source','Title','url','page 5','bad input')]
        good=json.dumps({'ok':json.dumps({'facts':[{'claim':text,'quote':text}]}),'metrics':{'eval_count':50}})
        process=Mock(stdin=io.StringIO(),stdout=io.StringIO(good+'\n'+good+'\n'+json.dumps({'ok':'broken'})+'\n'))
        captured=[]
        # Preserve writes for assertions even after generator closes the mock pipe.
        process.stdin.close=lambda:captured.append(process.stdin.getvalue())
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'config').mkdir();(root/'config/models.json').write_text('{"recommended":"mock"}')
            with patch.object(notes,'ROOT',root),patch.object(notes,'BUILD',root/'build.sqlite'),patch.object(notes,'windows',return_value=iter(windows)),patch.object(notes.subprocess,'Popen',return_value=process),patch('sys.stdout',new_callable=io.StringIO) as log:
                db=notes.build_db()
                db.execute('INSERT INTO notes VALUES(?,?,?,?,?,?,?,?,?,?)',('old','source','Title','url','page 1','fact','',text,text,text))
                db.execute('INSERT INTO done VALUES(?,?,?)',('old',1,0));db.commit();db.close()
                notes.generate(10,1)
                db=notes.build_db()
                keys={r[0] for r in db.execute('SELECT key FROM done')}
                self.assertEqual(keys,{'old','duplicate','different-author','different-text'})
                self.assertEqual(db.execute('SELECT locator FROM notes WHERE key="duplicate"').fetchone()[0],'page 2')
                db.close()
                self.assertIn('"eval_count": 50',log.getvalue())
                self.assertIn('"reused_windows": 1',log.getvalue())
        calls=[json.loads(line) for line in captured[0].splitlines()]
        self.assertEqual(len(calls),3)
        self.assertTrue(all(call['messages'][0]['content']==notes.FACT_PROMPT for call in calls))

    def test_legacy_summaries_and_qa_remain_groundable(self):
        quote='A sufficiently long exact passage from the original document.'
        raw={'summary':'Existing summary','facts':[{'claim':'One','quote':quote},{'claim':'Two','quote':quote}],
             'qa':[{'q':'Existing question','a':'Existing answer','quote':quote}]}
        self.assertEqual([r[0] for r in notes.ground(json.dumps(raw),quote)],['fact','fact','qa','summary'])
        self.assertEqual([r[0] for r in notes.ground(json.dumps(raw),quote,facts_only=True)],['fact','fact'])


if __name__=='__main__':unittest.main()
