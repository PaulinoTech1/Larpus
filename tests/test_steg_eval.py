import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('steg_eval',ROOT/'scripts/evaluate-stegdetect.py')
evaluation=importlib.util.module_from_spec(spec);spec.loader.exec_module(evaluation)

class EvaluationTests(unittest.TestCase):
    def test_confusion_matrix_and_denominators(self):
        rows=[{'carrier_label':label,'stegdetect':actual} for label,actual in [(True,True),(True,False),(False,True),(False,False),(True,None)]]
        m=evaluation.metrics(rows,'stegdetect')
        self.assertEqual([m[k] for k in ('TP','FN','FP','TN','inconclusive')],[1,1,1,1,1])
        self.assertEqual(m['detection_rate'],0.5)
        self.assertEqual(m['false_positive_rate'],0.5)
        self.assertEqual(m['positive_denominator'],2)

    def test_empty_denominators_are_unknown(self):
        m=evaluation.metrics([],'stegdetect')
        self.assertIsNone(m['false_positive_rate']);self.assertIsNone(m['detection_rate'])

    def test_scan_failure_is_not_true_positive(self):
        with patch.object(evaluation.gate,'inspect_text',side_effect=RuntimeError('SECRET')):
            carrier,held,reason=evaluation.observe('SECRET')
        self.assertIsNone(carrier);self.assertIsNone(held)

    def test_second_scan_incomplete_never_earns_credit(self):
        from types import SimpleNamespace
        complete=SimpleNamespace(status='complete',scan_complete=True,action='allow',candidate_text='hello')
        incomplete=SimpleNamespace(status='incomplete',scan_complete=False,action='block',candidate_text=None)
        with patch.object(evaluation.gate,'inspect_text',side_effect=[complete,incomplete]):
            carrier,held,reason=evaluation.observe('hello')
        self.assertFalse(carrier);self.assertIsNone(held)

    def test_unicode_fixtures_have_actual_codepoints(self):
        corpus,digest=evaluation.load(ROOT/'evals/stegdetect.json')
        cases={c['id']:c['text'] for c in corpus['cases']}
        for key,char in [('accent','\u00e9'),('cjk','\u4e16'),('emoji','\U0001f469'),('arabic','\u0645'),('fullwidth','\uff49')]:
            self.assertIn(char,cases[key])

    def test_duplicate_and_nonboolean_labels_rejected(self):
        corpus,digest=evaluation.load(ROOT/'evals/stegdetect.json')
        case=dict(corpus['cases'][0]);ids={case['id']}
        with self.assertRaises(ValueError):evaluation.validate_case(case,ids,corpus['families'])
        case['carrier']='yes'
        with self.assertRaises(ValueError):evaluation.validate_case(case,set(),corpus['families'])

    def test_metadata_cannot_leak_sample_text(self):
        corpus,digest=evaluation.load(ROOT/'evals/stegdetect.json')
        corpus['evidence']='PRIVATE_SAMPLE_SENTINEL'
        with self.assertRaises(ValueError):evaluation.validate_catalog(corpus)

    def test_report_has_no_raw_samples_and_missing_families_visible(self):
        corpus={'cases':[{'id':'safe','family':'plain','text':'PRIVATE_SAMPLE_SENTINEL','carrier':False,'hold':False}],
                'families':['plain','untested'],'evidence':'synthetic'}
        report=evaluation.evaluate(corpus,'digest')
        self.assertNotIn('PRIVATE_SAMPLE_SENTINEL',json.dumps(report))
        self.assertEqual(report['untested_families'],['untested'])
        self.assertFalse(report['production_claim_supported'])
