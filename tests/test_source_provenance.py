import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from runtime import provenance,knowledge

ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
owner=module('provenance_owner','scripts/source-provenance.py')
notes=module('provenance_notes','scripts/study-notes.py')

class SourceProvenanceTests(unittest.TestCase):
    def test_dates_do_not_promote_retrieval_time_to_publication(self):
        self.assertIsNone(provenance.date_value(None))
        for bad in ('yesterday','2026-13','2026-02-30',123):
            with self.assertRaises(ValueError):provenance.date_value(bad)
        items=[{'id':'unknown','retrieved_at':'2026-10-11'}, {'id':'new','published_on':'2024'}, {'id':'old','published_on':'1998-05'}]
        self.assertEqual([i['id'] for i in sorted(items,key=provenance.chronology)],['old','new','unknown'])

    def test_reviewed_authors_never_come_from_bibliography(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'knowledge').mkdir();(root/'research').mkdir();(root/'config').mkdir()
            (root/'knowledge/sources.json').write_text(json.dumps({'documents':[{'id':'manual','title':'Manual','url':'https://example.org','fetched_at':'2026-10-11'}]}))
            (root/'research/catalog.json').write_text(json.dumps({'entries':[{'id':'thesis','title':'Thesis','source_url':'https://example.edu','authors':['Actual Author'],'year':'2020'}]}))
            (root/'config/source-relationships.json').write_text('{"version":1,"links":[]}')
            value,raw=owner.build(root);(root/'knowledge/provenance.json').write_text(raw)
            item=provenance.evidence(root/'knowledge','thesis','REFERENCES [1] Other Author. A cited paper, 2010.')
            self.assertEqual(item['document_authors'],['Actual Author'])
            self.assertEqual(item['section'],'bibliography')
            self.assertIsNone(value['entries']['manual']['published_on'])
            self.assertEqual(value['entries']['manual']['document_authors'],[])

    def test_relationships_require_review_scope_and_reject_cycles(self):
        entries={'old':{},'new':{}}
        link={'new':'new','old':'old','kind':'corrects','scope':'AES implementation','evidence_url':'https://example.org/erratum','reviewed_on':'2026-10-11'}
        self.assertEqual(provenance.validate_relations({'version':1,'links':[link]},entries),[link])
        for bad in ({**link,'old':'missing'},{**link,'scope':''},{**link,'reviewed_on':None}):
            with self.assertRaises(ValueError):provenance.validate_relations({'version':1,'links':[bad]},entries)
        reverse={**link,'new':'old','old':'new'}
        with self.assertRaises(ValueError):provenance.validate_relations({'version':1,'links':[link,reverse]},entries)
        provenance.validate_relations({'version':1,'links':[{**link,'kind':'conflicts'},{**reverse,'kind':'conflicts'}]},entries)

    def test_reference_heading_rejects_reference_quotes_not_body_claims(self):
        quote='This matrix must be invertible before applying the proposed method.'
        ref='Other Author introduced the famous method in a separate publication.'
        text=quote+'\nREFERENCES\n'+ref
        self.assertFalse(notes.bibliographic(quote,text))
        self.assertTrue(notes.bibliographic(ref,text))
        self.assertEqual(provenance.section('We discuss references to related work in the next chapter.'),'body or unknown')
        self.assertIn('document authorship',knowledge.EVIDENCE_PROMPT)

    def test_index_mismatch_fails_closed_and_legacy_metadata_is_optional(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d);self.assertEqual(provenance.read(directory),{})
            (directory/'provenance.json').write_text('{"version":1,"index_sha256":"old","entries":{}}')
            (directory/'manifest.json').write_text('{"database_sha256":"new"}')
            with self.assertRaises(ValueError):provenance.read(directory)

    def test_scoped_correction_prefers_new_source_but_keeps_history(self):
        import hashlib
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d);path=directory/'approved.sqlite'
            with sqlite3.connect(path) as db:
                db.execute('CREATE VIRTUAL TABLE chunks USING fts5(source_id,title,url,snapshot,locator,text,role)')
                for sid,text in [('old','AES implementation condition AES implementation condition AES implementation condition.'),('new','AES implementation now has a documented correction.')]:
                    db.execute('INSERT INTO chunks VALUES(?,?,?,?,?,?,?)',(sid,'AES implementation','https://example.org','2026-10-11','document',text,'cryptographer'))
            db.close();digest=hashlib.sha256(path.read_bytes()).hexdigest()
            (directory/'manifest.json').write_text(json.dumps({'version':1,'database_sha256':digest,'database_bytes':path.stat().st_size}))
            link={'new':'new','old':'old','kind':'corrects','scope':'AES implementation','evidence_url':'https://example.org/erratum','reviewed_on':'2026-10-11'}
            entries={sid:{'id':sid,'published_on':year,'relationships':[link]} for sid,year in [('old','2020'),('new','2026')]}
            (directory/'provenance.json').write_text(json.dumps({'version':1,'index_sha256':digest,'entries':entries}))
            with patch.object(knowledge,'DIRECTORY',directory),patch.object(knowledge,'_engine',return_value=None),patch.object(knowledge,'author_cite',return_value=None):
                current=knowledge._retrieve('cryptographer','AES implementation',budget=700)
                historical=knowledge._retrieve('cryptographer','historical AES implementation',budget=700)
            self.assertEqual(current[0]['id'],'new')
            self.assertEqual(historical[0]['id'],'old')

    def test_chronological_queue_preserves_content_identity_and_saved_notes(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);directory=root/'knowledge';directory.mkdir()
            with sqlite3.connect(directory/'approved.sqlite') as db:
                db.execute('CREATE TABLE chunks(source_id,title,url,locator,text)')
                for sid in ['new','old','unknown']:db.execute('INSERT INTO chunks VALUES(?,?,?,?,?)',(sid,sid,'url','page 1 offset 0','A substantive passage from '+sid+'.'))
            db.close()
            entries={i:{'id':i,'published_on':year} for i,year in [('new','2025'),('old','2001'),('unknown',None)]}
            (directory/'provenance.json').write_text(json.dumps({'version':1,'entries':entries}))
            with patch.object(notes,'ROOT',root):first=list(notes.windows(None));again=list(notes.windows(None))
            self.assertEqual([row[1] for row in first],['old','new','unknown'])
            self.assertEqual(first,again)

if __name__=='__main__':unittest.main()
