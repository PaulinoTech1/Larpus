import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from scripts.knowledge_counts import reconcile


class KnowledgeCountTests(unittest.TestCase):
    def fixture(self,root):
        knowledge=root/'knowledge';knowledge.mkdir()
        catalog={'documents':[
            {'id':'unit42','url':'https://example.test/brief','indexed_passages':2},
            {'id':'other','url':'https://example.test/other','indexed_passages':1},
            {'id':'owner','url':'https://example.test/owner'},
        ]}
        (knowledge/'sources.json').write_text(json.dumps(catalog),encoding='utf-8')
        with sqlite3.connect(knowledge/'approved.sqlite') as db:
            db.execute('CREATE TABLE chunks(source_id TEXT,url TEXT,locator TEXT,text TEXT,role TEXT)')
            db.executemany('INSERT INTO chunks VALUES (?,?,?,?,?)',[
                ('unit42','https://example.test/brief','brief','whole brief','coach'),
                ('unit42','https://example.test/brief','brief','whole brief','home'),
                ('unit42','https://example.test/different','offset 0','other document','coach'),
                ('other','https://example.test/other','offset 0','evidence','coach'),
            ])
        return knowledge,catalog

    def test_check_fails_on_selected_index_mismatch_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);knowledge,catalog=self.fixture(root)
            before=(knowledge/'sources.json').read_bytes()
            with self.assertRaisesRegex(ValueError,"'unit42', 2, 1"):
                reconcile(root)
            self.assertEqual((knowledge/'sources.json').read_bytes(),before)

    def test_write_reconciles_only_declared_count_and_check_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);knowledge,_=self.fixture(root)
            self.assertEqual(reconcile(root,write=True),[('unit42',2,1)])
            self.assertEqual(reconcile(root),[])
            entries=json.loads((knowledge/'sources.json').read_text())['documents']
            self.assertEqual(entries[0]['indexed_passages'],1)
            self.assertNotIn('indexed_passages',entries[2])

    def test_missing_or_redirected_index_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);knowledge,_=self.fixture(root)
            (knowledge/'approved.sqlite').unlink()
            with self.assertRaisesRegex(ValueError,'missing or redirected'):
                reconcile(root)


if __name__=='__main__':unittest.main()
