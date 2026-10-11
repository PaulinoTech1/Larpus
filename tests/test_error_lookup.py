import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('error_lookup',Path(__file__).resolve().parents[1]/'scripts/errors.py')
errors=importlib.util.module_from_spec(spec);spec.loader.exec_module(errors)

class LookupTests(unittest.TestCase):
    def test_exact_and_linked_records_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);logs=root/'data/releases';logs.mkdir(parents=True)
            record={'schema':'larpus.diagnostic/v1','error_id':'a'*16,'causes':[]}
            linked={**record,'error_id':'b'*16,'causes':[{'related_error_id':'a'*16}]}
            (logs/'test.gateway.log').write_text('unstructured '+'a'*16+'\n'+json.dumps(record)+'\n'+json.dumps(linked)+'\n')
            self.assertEqual(len(errors.lookup('a'*16,root)),2)
            self.assertEqual(errors.lookup('c'*16,root),[])

    def test_path_or_invalid_id_rejected(self):
        with self.assertRaises(ValueError):errors.lookup('../private')
