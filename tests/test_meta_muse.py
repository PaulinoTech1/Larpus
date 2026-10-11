"""Product evidence survives focused retrieval without connecting a service."""
import unittest
from runtime.knowledge import retrieve


class MetaMuseTests(unittest.TestCase):
    def text(self,question):
        evidence=retrieve('home-assistant',question)
        self.assertTrue(evidence)
        return ' '.join(item.get('text',item.get('original_passage','')) for item in evidence)

    def test_referral_answer_has_conditional_credit_and_verification_gap(self):
        text=self.text('Meta Muse referral invite billion token credit recommendations')
        self.assertIn('1 billion',text)
        self.assertIn('48 hours',text)
        self.assertIn('not independently primary-source verified',text)
        self.assertIn('not cash',text)

    def test_spark_shorthand_retains_version_and_audio_limit(self):
        text=self.text('Meta Spark 1.3 model audio understanding compared with 1.2')
        self.assertIn('1,048,576',text)
        self.assertIn('incomplete',text)
        self.assertIn('1.2',text)

    def test_comparison_supplies_both_agent_products(self):
        evidence=retrieve('home-assistant','Compare Grok Bot and Meta Muse agents for everyday tasks and scheduled routines')
        text=' '.join(item.get('text',item.get('original_passage','')) for item in evidence)
        self.assertIn('Grok Bot',text)
        self.assertIn('Muse',text)
        self.assertIn('both agents',text)
        self.assertTrue(any('grok' in item['id'] for item in evidence))
        self.assertTrue(any('muse' in item['id'] for item in evidence))


if __name__=='__main__':unittest.main()
