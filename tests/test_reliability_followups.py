import contextlib,importlib.util,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_model_switch import Backend
from runtime.model_switch import ModelSwitch
from scripts import releases
class Followups(unittest.TestCase):
 def test_ui_gates_share_all_suites_and_propagate_failure(self):
  from scripts import ui_checks,ci
  self.assertIn('model-switch-ui.cjs',ui_checks.TESTS);self.assertIn('session-ui.cjs',ui_checks.TESTS)
  self.assertEqual(ci.UI_TESTS,ui_checks.TESTS)
  with patch.object(releases,'run',side_effect=subprocess.CalledProcessError(7,['node'])) as execute:
   with self.assertRaises(subprocess.CalledProcessError):releases.check_ui(Path('.'))
   self.assertEqual(execute.call_count,1)
 def test_recovery_failure_has_safe_correlated_diagnostic_and_failing_cli(self):
  with tempfile.TemporaryDirectory() as d:
   b=Backend();b.fail={'larpus-3.5'};c=ModelSwitch(b,d,start=lambda fn:None);output=io.StringIO()
   with contextlib.redirect_stderr(output):self.assertFalse(c.recover())
   self.assertEqual(c.status()['phase'],'failed')
   evidence=json.loads((Path(d)/'diagnostic.json').read_text());self.assertRegex(evidence['error_id'],r'^[a-f0-9]{16}$')
   self.assertEqual(evidence['phase'],'restoring');self.assertIn(evidence['error_id'],output.getvalue());self.assertIn(evidence['error_id'],c.status()['error'])
   spec=importlib.util.spec_from_file_location('maintenance',Path(__file__).resolve().parents[1]/'scripts/model-switch.py');cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
   with patch.object(cli,'ModelSwitch',return_value=c),patch.object(sys,'argv',['model-switch.py','recover']),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):self.assertEqual(cli.main(),1)
 def test_diagnostic_storage_failure_cannot_prevent_restoration(self):
  with tempfile.TemporaryDirectory() as d:
   b=Backend();b.fail={'larpus-3.8'};c=ModelSwitch(b,d,start=lambda fn:None);replace=Path.replace
   def denied(path,target):
    if path.name=='diagnostic.tmp':raise PermissionError('synthetic diagnostic failure')
    return replace(path,target)
   c.request('larpus-3.8')
   with patch.object(Path,'replace',denied),contextlib.redirect_stderr(io.StringIO()):c.run('larpus-3.8')
   self.assertEqual(b.state['phase'],'ready');self.assertEqual(b.state['active_id'],'larpus-3.5');self.assertIn('restored',b.state['error'])
 # subprocess.run is mocked, but runtime.isolation.wsl_command refuses to build the
 # command unless os.name=='nt'; wsl.exe itself is never invoked.
 @unittest.skipUnless(os.name=='nt','owner WSL command builder is Windows-only')
 def test_owner_subprocess_preserves_numeric_failure_without_output(self):
  from runtime.model_backend import Backend as Owner
  b=Owner.__new__(Owner);b.profile={'agent_image':'pinned'}
  response=subprocess.CompletedProcess([],17,stdout='private output',stderr='private secret')
  with patch('runtime.model_backend.subprocess.run',return_value=response):
   with self.assertRaises(RuntimeError) as failed:b.call('/api/ps')
  self.assertEqual(failed.exception.__cause__.returncode,17);self.assertNotIn('private',str(failed.exception))
