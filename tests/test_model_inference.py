import unittest
from unittest.mock import patch
from runtime import inference,notes_worker
class InferenceSelectionTests(unittest.TestCase):
 def test_active_model_comes_from_broker_not_browser(self):
  with patch.object(inference,'ollama',return_value={'models':[],'active_model':'larpus3.8:27b-q4'}):self.assertEqual(inference.active_model('qwen3.5:27b-q4_K_M'),'larpus3.8:27b-q4')
 def test_old_broker_status_retains_legacy_compatibility(self):
  with patch.object(inference,'ollama',return_value={'models':[]}):self.assertEqual(inference.active_model('qwen3.5:27b-q4_K_M'),'qwen3.5:27b-q4_K_M')
 def test_notes_reports_actual_model_and_rejects_arbitrary_tag(self):
  with patch.object(notes_worker,'ollama',return_value={'active_model':'larpus3.8:27b-q4'}):self.assertEqual(notes_worker.producer('qwen3.5:27b-q4_K_M'),'larpus3.8:27b-q4')
  with self.assertRaises(ValueError):notes_worker.producer('unapproved')
