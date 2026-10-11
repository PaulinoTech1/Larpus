import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('complexity',ROOT/'scripts/complexity.py')
complexity=importlib.util.module_from_spec(spec);spec.loader.exec_module(complexity)

class ComplexityTests(unittest.TestCase):
    def test_static_inventory_never_executes_source_and_separates_nested_functions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'runtime').mkdir();(root/'scripts').mkdir()
            (root/'runtime/a.py').write_text('import runtime.b\nraise RuntimeError("must not execute")\ndef outer(x):\n    def inner():\n        if x:return 1\n    if x and x>1:return inner()\n',encoding='utf8')
            (root/'runtime/b.py').write_text('',encoding='utf8')
            report=complexity.analyze(root)
        rows={r['function']:r for r in report['functions']}
        self.assertEqual(rows['outer']['decisions'],3)
        self.assertEqual(rows['outer.inner']['decisions'],2)
        self.assertEqual(report['imports'],[{'from':'runtime.a','to':'runtime.b','top_level':True}])

    def test_growth_fails_and_small_new_functions_pass(self):
        report={'functions':[{'key':'f','line':1,'decisions':13,'lines':81}],'modules':[{'module':'m','fan_out':7}]}
        baseline={'version':1,'functions':{},'new_function':{'decisions':12,'lines':80}}
        self.assertEqual({r['metric'] for r in complexity.regressions(report,baseline)},{'decisions','lines','fan_out'})
        report['functions'][0].update(decisions=2,lines=4);report['modules'][0]['fan_out']=1
        self.assertEqual(complexity.regressions(report,baseline),[])

    def test_broken_source_fails_loudly(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'runtime').mkdir();(root/'scripts').mkdir()
            (root/'runtime/bad.py').write_text('def broken(',encoding='utf8')
            with self.assertRaises(SyntaxError):complexity.analyze(root)

    def test_component_ledger_has_valid_links_and_evidence_paths(self):
        catalog=json.loads((ROOT/'config/system-map.json').read_text(encoding='utf8'))
        ids={c['id'] for c in catalog['components']}
        self.assertEqual(len(ids),len(catalog['components']))
        for component in catalog['components']:
            for field in ('purpose','invariant','costs','keep_condition','failure_modes','verification'):self.assertTrue(component[field])
            for path in component['files']+component['verification']:self.assertTrue((ROOT/path).is_file(),path)
        for edge in catalog['interactions']:
            self.assertIn(edge['from'],ids);self.assertIn(edge['to'],ids)
