import json,tempfile,unittest
from pathlib import Path
from runtime import model_selection as ms
class SelectionTests(unittest.TestCase):
 def test_catalog_and_state_are_fixed(self):
  catalog=ms.catalog();self.assertEqual(set(catalog),{'larpus-3.5','larpus-3.8'})
  for bad in ('other','../larpus-3.8','https://example.com',True):
   with self.assertRaises(ValueError):ms.model(bad)
 def test_missing_malformed_and_busy_state_fail_closed(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'state.json'
   with self.assertRaises((OSError,ValueError)):ms.read_selection(p)
   s=ms.initial();p.write_text(json.dumps(s));self.assertEqual(ms.read_selection(p)['active_id'],'larpus-3.5')
   s['phase']='loading';s['target_id']='larpus-3.8';p.write_text(json.dumps(s));self.assertTrue(ms.is_switching(ms.read_selection(p)))
   s['active_id']='unknown';p.write_text(json.dumps(s))
   with self.assertRaises(ValueError):ms.read_selection(p)
 def test_only_active_tag_can_generate(self):
  from runtime import inference_broker as b
  from unittest.mock import patch
  s=ms.initial();s['active_id']='larpus-3.8'
  with patch.object(ms,'read_selection',return_value=s):
   p=b.selected_policy({'model':'qwen3.5:27b-q4_K_M','selection_enabled':True})
  self.assertEqual(p['model'],'larpus3.8:27b-q4')
  self.assertFalse(p['switching'])
