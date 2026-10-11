import unittest
from unittest.mock import patch
from runtime import knowledge,inference

class StudyNoteTierTests(unittest.TestCase):
    def test_chat_and_stream_preview_original_passage_for_derived_notes(self):
        note={'id':'crypto-thesis','title':'Cryptography study','url':'https://example.org/thesis','locator':'page 1',
              'tier':knowledge.NOTE_TIER,'note':'Derived interpretation.','original_passage':'Original approved passage.'}
        prepared=[{'role':'system','content':'Trusted persona.'},{'role':'user','content':'Explain the source.'}]
        frame={'message':{'content':'A brief explanation.'},'done':True}
        for streaming in (False,True):
            chunks=[]
            with patch.object(inference,'augment',return_value=(prepared,[note])),patch.object(inference,'gpu_placement',return_value='GPU'),patch.object(inference,'ollama',return_value=frame),patch.object(inference,'chat_stream',return_value=iter([frame])),patch.object(inference,'gate',side_effect=lambda text,*_: {'status':200,'content':text}) as guard:
                result=inference.chat('home-assistant',[{'role':'user','content':'Explain the source.'}],on_chunk=chunks.append if streaming else None)
            self.assertEqual(result['status'],200)
            self.assertEqual(result['sources'][0]['preview'],note['original_passage'])
            self.assertEqual(result['sources'][0]['tier'],knowledge.NOTE_TIER)
            self.assertEqual(result['sources'][0]['snapshot'],'derived study note')
            self.assertNotIn(note['note'],[call.args[0] for call in guard.call_args_list])
            if streaming:self.assertEqual(''.join(chunks),frame['message']['content'])

    def test_notes_are_labeled_and_carry_their_vetted_passage(self):
        if knowledge.notes_database() is None:self.skipTest('no published notes')
        for item in knowledge.study_notes(['aes','block','cipher','mode'],20000,limit=5):
            self.assertEqual(item['tier'],knowledge.NOTE_TIER)
            self.assertTrue(item['original_passage'])
            self.assertIn('not a source',item['tier'])

    def test_prompt_never_lets_notes_stand_as_sources(self):
        self.assertIn('never cite the note itself as a source',knowledge.EVIDENCE_PROMPT)
