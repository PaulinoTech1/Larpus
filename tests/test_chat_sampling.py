import copy,unittest
from runtime import inference_broker as broker

class ChatSamplingTests(unittest.TestCase):
 def test_regular_chat_gets_owner_fixed_repetition_controls_without_mutation(self):
  body={'messages':[{'role':'system','content':'CONVERSATION PROGRESS: trusted policy'},{'role':'user','content':'Continue'}],'options':{'temperature':.4},'stream':False}
  original=copy.deepcopy(body);result=broker.generation_body(body,'chat')
  self.assertEqual(body,original)
  self.assertEqual(result['options']['repeat_last_n'],4096)
  self.assertEqual(result['options']['repeat_penalty'],1.1)
  self.assertTrue(result['stream'])

 def test_notes_and_summary_templates_keep_existing_sampling(self):
  for lane,system in (('notes','CONVERSATION PROGRESS: trusted policy'),('chat','Return a structured conversation summary')):
   body={'messages':[{'role':'system','content':system}],'options':{'temperature':0},'stream':False}
   result=broker.generation_body(body,lane)
   self.assertEqual(result['options'],body['options'])

 def test_client_cannot_supply_sampling_controls(self):
  policy={'version':1,'enabled':True,'model':'qwen3.5:27b-q4_K_M','context':131072,'max_output':6000}
  for key,value in (('repeat_last_n',4096),('repeat_penalty',1.1)):
   body={'model':policy['model'],'messages':[{'role':'user','content':'Hello'}],'stream':False,'think':False,'keep_alive':-1,'options':{'temperature':.4,'num_ctx':131072,'num_predict':1024,'num_gpu':99,key:value}}
   with self.assertRaises(ValueError):broker.validate_chat(body,policy)

if __name__=='__main__':unittest.main()
