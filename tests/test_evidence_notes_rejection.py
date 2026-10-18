import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from runtime import knowledge
from runtime.text_filter import TextHeld


class RejectedNoteTests(unittest.TestCase):
    def retrieve(self,bad_field=None,inspect=None):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'notes.sqlite'
            with sqlite3.connect(path) as connection:
                connection.execute('CREATE VIRTUAL TABLE notes USING fts5(source_id,title,url,locator,question,text,context)')
                bad=['rejected-note','Study','https://example.org','page 1','topology topology','A derived note.','Original passage.']
                if bad_field is not None:bad[bad_field]='topology\u202e hidden'
                connection.execute('INSERT INTO notes VALUES (?,?,?,?,?,?,?)',bad)
                connection.execute('INSERT INTO notes VALUES (?,?,?,?,?,?,?)',('safe-note','Study','https://example.org','page 2','topology','A safe derived note.','A safe original passage.'))
            connection.close()
            with patch.object(knowledge,'notes_database',side_effect=lambda:sqlite3.connect(path)),patch.object(knowledge,'source_provenance',return_value={'section':'body'}),patch.object(knowledge,'author_cite',return_value=None),patch.object(knowledge,'_engine',return_value=None):
                if inspect is None:return knowledge.study_notes(['topology'],9000,limit=2)
                with patch.object(knowledge,'inspect_message',side_effect=inspect):
                    return knowledge.study_notes(['topology'],9000,limit=2)

    def test_rejected_optional_note_is_excluded_in_each_field(self):
        for field in (4,5,6):
            with self.subTest(field=field):
                result=self.retrieve(bad_field=field)
                self.assertEqual([item['id'] for item in result],['safe-note'])
                self.assertNotIn('\u202e',str(result))

    def test_unavailable_scanner_still_rejects_retrieval(self):
        with self.assertRaises(TextHeld):
            self.retrieve(inspect=TextHeld('scan_unavailable',unavailable=True))

    def test_incomplete_scan_still_rejects_retrieval(self):
        with self.assertRaises(TextHeld):
            self.retrieve(inspect=TextHeld('unicode_carrier_or_incomplete_scan',scan_complete=False))

    def test_database_integrity_failure_still_propagates(self):
        with patch.object(knowledge,'notes_database',side_effect=ValueError('Notes database hash mismatch')):
            with self.assertRaises(ValueError):knowledge.study_notes(['topology'],9000)


if __name__=='__main__':unittest.main()
