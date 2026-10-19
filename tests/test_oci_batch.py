import json,unittest
from types import SimpleNamespace
from unittest.mock import patch
from runtime import isolation

class OciBatchTests(unittest.TestCase):
 def items(self):
  return [{'Id':c*64,'OCIConfigPath':'/home/larpus/.local/share/containers/storage/overlay-containers/'+c*64+'/userdata/config.json'} for c in 'abcd']
 def test_one_fresh_process_preserves_exact_path_order(self):
  items=self.items();raw=[{'path':i['OCIConfigPath'],'value':{'id':i['Id']}} for i in items]
  with patch.object(isolation,'wsl_command',return_value=['fixed']) as command,patch.object(isolation.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps(raw).encode())) as run:
   actual=isolation.read_oci_batch(items)
  self.assertEqual(actual,[{'id':i['Id']} for i in items]);self.assertEqual(run.call_count,1)
  self.assertEqual(command.call_args.args[:2],('python3','-c'))
 def test_malformed_identity_is_rejected_before_execution(self):
  items=self.items();items[0]['OCIConfigPath']='/tmp/other'
  with patch.object(isolation.subprocess,'run') as run:
   with self.assertRaises(ValueError):isolation.read_oci_batch(items)
   run.assert_not_called()
 def test_partial_reordered_and_invalid_results_fail_closed(self):
  items=self.items();raw=[{'path':i['OCIConfigPath'],'value':{'ok':True}} for i in items]
  for payload in (raw[:-1],raw[::-1],[{'path':i['OCIConfigPath'],'value':[]} for i in items]):
   with patch.object(isolation,'wsl_command',return_value=['fixed']),patch.object(isolation.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps(payload).encode())):
    with self.assertRaises(ValueError):isolation.read_oci_batch(items)
 def test_empty_batch_does_not_start_wsl(self):
  with patch.object(isolation.subprocess,'run') as run:
   self.assertEqual(isolation.read_oci_batch([]),[]);run.assert_not_called()

 def test_oversized_response_and_nonzero_process_fail_closed(self):
  import subprocess
  with patch.object(isolation,'wsl_command',return_value=['fixed']),patch.object(isolation.subprocess,'run',return_value=SimpleNamespace(stdout=b'x'*4100001)):
   with self.assertRaises(ValueError):isolation.read_oci_batch(self.items())
  with patch.object(isolation,'wsl_command',return_value=['fixed']),patch.object(isolation.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['fixed'])):
   with self.assertRaises(subprocess.CalledProcessError):isolation.read_oci_batch(self.items())
 def test_excessive_count_and_nonhex_ids_are_rejected_before_execution(self):
  for items in (self.items()+self.items(),[{'Id':'../escape','OCIConfigPath':'/tmp/other'}]):
   with patch.object(isolation.subprocess,'run') as run:
    with self.assertRaises(ValueError):isolation.read_oci_batch(items)
    run.assert_not_called()
