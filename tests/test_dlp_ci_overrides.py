import os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from runtime import dlp
from runtime.mcp_client import child_parameters

class ProtectTimeoutTests(unittest.TestCase):
    def test_default_is_unchanged(self):
        self.assertEqual(dlp.PROTECT_TIMEOUT_DEFAULT,10)
        self.assertEqual(dlp.protect_timeout({}),10)
        self.assertEqual(dlp.protect_timeout({'GITHUB_ACTIONS':'true'}),10)

    def test_override_ignored_outside_github_actions(self):
        for environ in ({'LARPUS_CI_QUARANTINE_TIMEOUT':'60'},{'LARPUS_CI_QUARANTINE_TIMEOUT':'60','GITHUB_ACTIONS':'false'},{'LARPUS_CI_QUARANTINE_TIMEOUT':'999'}):
            self.assertEqual(dlp.protect_timeout(environ),10)

    def test_bounded_override_on_github_actions(self):
        self.assertEqual(dlp.protect_timeout({'GITHUB_ACTIONS':'true','LARPUS_CI_QUARANTINE_TIMEOUT':'45'}),45)
        self.assertEqual(dlp.protect_timeout({'GITHUB_ACTIONS':'true','LARPUS_CI_QUARANTINE_TIMEOUT':'60'}),dlp.PROTECT_TIMEOUT_MAX)

    def test_cap_and_invalid_values_fail_closed(self):
        for raw in ('61','999','9','0','-5','abc','','12.5',' 30','1000'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                dlp.protect_timeout({'GITHUB_ACTIONS':'true','LARPUS_CI_QUARANTINE_TIMEOUT':raw})

    def test_gate_withholds_output_when_override_invalid(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(dlp,'QUARANTINE',Path(temp)/'quarantine'),\
             patch.dict(os.environ,{'GITHUB_ACTIONS':'true','LARPUS_CI_QUARANTINE_TIMEOUT':'61'}):
            self.assertEqual(dlp.gate('Plain safe text.')['status'],503)

    @unittest.skipUnless(os.name=='nt','Windows ACL helper path')
    def test_windows_helper_receives_bounded_timeout(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(dlp,'QUARANTINE',Path(temp)/'quarantine'),\
             patch.dict(os.environ,{'GITHUB_ACTIONS':'true','LARPUS_CI_QUARANTINE_TIMEOUT':'45'}),\
             patch('runtime.dlp.subprocess.run',return_value=subprocess.CompletedProcess([],0)) as run:
            dlp.secure_directory()
            self.assertEqual(run.call_args.kwargs['timeout'],45)

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
        values={'LARPUS_ISOLATION':'host','GITHUB_ACTIONS':'true','LARPUS_CI_QUARANTINE_TIMEOUT':'60','GITHUB_TOKEN':'secret','LARPUS_OTHER':'x'}
        with patch.dict(os.environ,values):
            env=child_parameters().env
        self.assertEqual(env['LARPUS_CI_QUARANTINE_TIMEOUT'],'60');self.assertEqual(env['GITHUB_ACTIONS'],'true')
        self.assertNotIn('GITHUB_TOKEN',env);self.assertNotIn('LARPUS_OTHER',env)

if __name__=='__main__':unittest.main()
