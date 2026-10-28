import json
from pathlib import Path
import tempfile
import time
import unittest
from scripts import owner_status

class OwnerStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.release=self.root/'data/releases'/('a'*32)
        self.release.mkdir(parents=True)
        (self.release.parent/'active.json').write_text(json.dumps({'id':'a'*32,'pid':123}))

    def test_absent_health_is_unknown_and_absent_recovery_is_disabled(self):
        report=owner_status.collect(self.root,git_probe=lambda root:{'branch':'test','dirty_files':[],'worktrees':[]})
        self.assertEqual(report['active']['id'],'a'*32)
        self.assertEqual(report['readiness']['state'],'unknown')
        self.assertFalse(report['recovery']['armed']);self.assertFalse((self.root/'data/recovery').exists())

    def test_readiness_and_scan_warning_are_independent_and_stale_never_passes(self):
        directory=self.release/'release-state/health';directory.mkdir(parents=True)
        checks=[{'name':name,'status':'pass'} for name in owner_status.REQUIRED]
        checks.append({'name':'security_scan','status':'warn'})
        path=directory/'latest.json';path.write_text(json.dumps({'status':'degraded','checks':checks,
            'producer':{'version':1,'release_id':'a'*32,'pid':123,'token':'b'*32,'started':1,'finished':2}}))
        probe=lambda root:{}
        report=owner_status.collect(self.root,git_probe=probe,monotonic_now=3)
        self.assertEqual(report['readiness']['state'],'ready')
        self.assertEqual(report['scan']['status'],'warn')
        report=owner_status.collect(self.root,git_probe=probe,monotonic_now=1000)
        self.assertEqual(report['readiness']['state'],'stale')

    def test_scan_completeness_is_reported_without_relabeling_warnings(self):
        directory=self.release/'release-state/security';directory.mkdir(parents=True)
        (directory/'summary.json').write_text(json.dumps({'status':'warning','results':[
            {'complete':True,'status':'pass'},{'complete':True,'status':'warning'},{'complete':False,'status':'error'}]}))
        report=owner_status.collect(self.root,git_probe=lambda root:{})
        self.assertEqual(report['scan']['complete_targets'],2)
        self.assertEqual(report['scan']['incomplete_targets'],1)
        self.assertEqual(report['scan']['warning_targets'],1)
        self.assertFalse(report['scan']['pins_reverified'])

    def test_unsafe_release_ids_and_oversized_state_are_not_followed(self):
        active=self.release.parent/'active.json';active.write_text('{"id":"../../outside"}')
        report=owner_status.collect(self.root,git_probe=lambda root:{})
        self.assertEqual(report['active']['state'],'unknown')
        active.write_text('x'*65537)
        self.assertEqual(owner_status.collect(self.root,git_probe=lambda root:{})['active']['state'],'unknown')

