import ast
import hashlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from runtime.source_integrity import fingerprint

class SourceIntegrityTests(unittest.TestCase):
    def test_legacy_algorithm_and_freshness(self):
        source=Path('runtime/security_scan.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        old=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='fingerprint')
        # Stored old implementation is the independent pre-refactor oracle.
        oracle=Path('tests/fixtures/legacy_fingerprint.txt').read_text(encoding='utf-8')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name in ('runtime/a.py','skills/demo/SKILL.md','agents/personas/a.json','runtime/native/a.S','deploy/voice/a','knowledge/briefs/a.txt'):
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(name)
            ns={'ROOT':root,'APPROVED':root/'config/mcp-approved.json','hashlib':hashlib}
            exec(oracle,ns)
            self.assertEqual(fingerprint(root),ns['fingerprint']())
            before=fingerprint(root);(root/'runtime/a.py').write_text('changed')
            self.assertNotEqual(before,fingerprint(root))
            with patch.object(Path,'is_symlink',return_value=True):
                with self.assertRaises(ValueError):fingerprint(root)
            (root/'runtime/a.py').write_bytes(b'x'*1000001)
            with self.assertRaises(ValueError):fingerprint(root)
    def test_import_has_no_mcp_or_subprocess_dependency(self):
        result=subprocess.run([sys.executable,'-c',"import sys; import runtime.source_integrity; assert 'mcp' not in sys.modules; assert 'runtime.isolation' not in sys.modules; assert 'runtime.security_scan' not in sys.modules"],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
