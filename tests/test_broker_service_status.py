import unittest
from unittest.mock import patch
from runtime import inference
from runtime.local_ollama import BrokerRejected

class BrokerServiceStatusTests(unittest.TestCase):
    def test_normal_and_streamed_chat_preserve_budget_and_unavailable_status(self):
        prepared=[{'role':'system','content':'Trusted persona.'},{'role':'user','content':'Hello'}]
        for streaming in (False,True):
            for status,code,expected in ((429,'inference_budget',429),(503,'cancellation_unconfirmed',503),(403,'system_template_denied',503)):
                refusal=BrokerRejected(status,code)
                with patch.object(inference,'augment',return_value=(prepared,[])),patch.object(inference,'ollama',side_effect=refusal),patch.object(inference,'chat_stream',side_effect=refusal):
                    result=inference.chat('home-assistant',[{'role':'user','content':'Hello'}],on_chunk=(lambda _:None) if streaming else None)
                self.assertEqual(result['status'],expected)
                self.assertNotEqual(result['status'],502)
                if code=='system_template_denied':self.assertEqual(result['code'],'broker_held')

if __name__=='__main__':unittest.main()
