import json
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from tests.test_notes_throughput import notes


class NuancedNotesTests(unittest.TestCase):
    def test_retains_fifteen_facts_with_qualifications_and_quotes(self):
        quote='This conclusion holds only under the stated assumptions, and exceptions remain possible.'
        facts=[{'claim':f'Finding {i}: {quote}','quote':quote} for i in range(16)]
        kept=notes.ground(json.dumps({'facts':facts}),quote,facts_only=True)
        self.assertEqual(len(kept),15)
        self.assertTrue(all(row[3]==quote and 'only under' in row[2] for row in kept))

    def test_sparse_passage_is_not_padded(self):
        quote='A sparse source supports only this one qualified statement.'
        kept=notes.ground(json.dumps({'facts':[{'claim':quote,'quote':quote}]}),quote,facts_only=True)
        self.assertEqual(len(kept),1)
        self.assertEqual(notes.ground('{"facts":[]}',quote,facts_only=True),[])
        self.assertIn('never invent or pad',notes.FACT_PROMPT)
        self.assertIn('at least 8 and up to 15',notes.FACT_PROMPT)

    def test_truncation_is_retryable_with_larger_note_budget(self):
        process=Mock(stdin=io.StringIO(),stdout=io.StringIO(json.dumps({'ok':'{"facts":[]}','metrics':{'done_reason':'length'}})+'\n'))
        sent=[]
        process.stdin.close=lambda:sent.append(process.stdin.getvalue())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'config').mkdir()
            (root/'config/models.json').write_text('{"recommended":"mock"}')
            with patch.object(notes,'ROOT',root),patch.object(notes,'BUILD',root/'build.sqlite'),patch.object(notes,'windows',return_value=iter([('key','source','Title','url','page 1','text')])),patch.object(notes.subprocess,'Popen',return_value=process),patch('sys.stdout',new_callable=io.StringIO):
                notes.generate(1,1)
                db=notes.build_db()
                self.assertEqual(db.execute('SELECT count(*) FROM done').fetchone()[0],0)
                db.close()
        self.assertEqual(json.loads(sent[0].splitlines()[0])['num_predict'],6000)


if __name__=='__main__':unittest.main()
