import unittest
from runtime import knowledge

class StudyNoteTierTests(unittest.TestCase):
    def test_notes_are_labeled_and_carry_their_vetted_passage(self):
        if knowledge.notes_database() is None:self.skipTest('no published notes')
        for item in knowledge.study_notes(['aes','block','cipher','mode'],20000,limit=5):
            self.assertEqual(item['tier'],knowledge.NOTE_TIER)
            self.assertTrue(item['original_passage'])
            self.assertIn('not a source',item['tier'])

    def test_prompt_never_lets_notes_stand_as_sources(self):
        self.assertIn('never cite the note itself as a source',knowledge.EVIDENCE_PROMPT)
