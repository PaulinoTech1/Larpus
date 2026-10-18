import os,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from runtime import dlp
from runtime.mcp_client import child_parameters

class ProtectTimeoutTests(unittest.TestCase):
    def test_timeout_is_fixed_and_not_overridable(self):
        self.assertEqual(dlp.PROTECT_TIMEOUT_DEFAULT,10)
        self.assertFalse(hasattr(dlp,'protect_timeout'))
        with tempfile.TemporaryDirectory() as temp,patch.object(dlp,'QUARANTINE',Path(temp)/'data'/'quarantine'),\
             patch.object(dlp,'os',SimpleNamespace(**{**vars(os),'name':'nt','environ':{**os.environ,'SYSTEMROOT':'C:\\Windows','GITHUB_ACTIONS':'true','LARPUS_CI_QUARANTINE_TIMEOUT':'60'}})),\
             patch('runtime.dlp.subprocess.run',return_value=subprocess.CompletedProcess([],0)) as run:
            dlp.secure_directory()
        self.assertEqual(run.call_args.kwargs['timeout'],10)

class QuarantinePathTests(unittest.TestCase):
    def test_default_path_unless_github_actions(self):
        default=dlp.ROOT/'data/quarantine'
        self.assertEqual(dlp.quarantine_path({}),default)
        self.assertEqual(dlp.quarantine_path({'LARPUS_CI_QUARANTINE_DIR':str(Path(tempfile.gettempdir()).resolve())}),default)

    def test_ci_path_must_be_absolute(self):
        absolute=Path(tempfile.gettempdir()).resolve()/'larpus-quarantine'
        self.assertEqual(dlp.quarantine_path({'GITHUB_ACTIONS':'true','LARPUS_CI_QUARANTINE_DIR':str(absolute)}),absolute)
        with self.assertRaises(ValueError):
            dlp.quarantine_path({'GITHUB_ACTIONS':'true','LARPUS_CI_QUARANTINE_DIR':'relative/quarantine'})

class ChildEnvironmentTests(unittest.TestCase):
    def test_only_named_ci_settings_are_forwarded(self):
        values={'LARPUS_ISOLATION':'host','GITHUB_ACTIONS':'true','LARPUS_CI_QUARANTINE_DIR':'C:\\q','LARPUS_CI_QUARANTINE_TIMEOUT':'60','GITHUB_TOKEN':'secret','LARPUS_OTHER':'x'}
        with patch.dict(os.environ,values):
            env=child_parameters().env
        self.assertEqual(env['LARPUS_CI_QUARANTINE_DIR'],'C:\\q');self.assertEqual(env['GITHUB_ACTIONS'],'true')
        self.assertNotIn('LARPUS_CI_QUARANTINE_TIMEOUT',env)
        self.assertNotIn('GITHUB_TOKEN',env);self.assertNotIn('LARPUS_OTHER',env)

if __name__=='__main__':unittest.main()
