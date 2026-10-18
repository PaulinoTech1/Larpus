import unittest
from runtime.agents import load_personas,messages_for

class ConversationProgressTests(unittest.TestCase):
 def test_new_turn_keeps_history_once_and_requires_progress(self):
  history=[{'role':'user','content':'Grok costs me 10 per month during my promotion.'},{'role':'assistant','content':'Try a harder project to use the allowance.'},{'role':'user','content':'I already tried that. I feel trapped by trying to use the allowance.'}]
  prepared=messages_for(load_personas()['home-assistant'],history)
  self.assertEqual(prepared[1:],history)
  self.assertIn('Do not recycle',prepared[0]['content'])
  self.assertIn('promotional terms',prepared[0]['content'])
  self.assertIn('psychological',prepared[0]['content'])

 def test_repetition_is_allowed_when_requested_and_policy_is_shared(self):
  for persona in load_personas().values():
   prepared=messages_for(persona,[{'role':'user','content':'Repeat the previous explanation.'}])
   self.assertIn('unless the user asks',prepared[0]['content'])
   self.assertNotIn('most of the time, add one crisp deadpan',prepared[0]['content'])
   self.assertIn('humour is optional',prepared[0]['content'])
   self.assertIn('without measurements',prepared[0]['content'])

if __name__=='__main__':unittest.main()
