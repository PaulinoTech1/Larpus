from copy import deepcopy
import unittest
from scripts import quality_evaluation as quality

class QualityEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.cases=quality.load_cases();self.case=self.cases[0]
        self.result={'status':200,'content':'A source-backed answer.','sources':self.case['sources']}

    def review(self,attempt,kind='human'):
        return {**{k:attempt[k] for k in ('case_id','case_sha256','response_sha256','evidence_sha256')},
                'reviewer_kind':kind,'claims':[{'id':'claim-1','verdict':'supported','evidence_ids':[self.case['sources'][0]['id']]}]}

    def test_family_disjoint_catalogue_covers_critical_regressions(self):
        self.assertGreaterEqual(len(self.cases),24)
        dev={c['family'] for c in self.cases if c['split']=='development'}
        held={c['family'] for c in self.cases if c['split']=='held-out'}
        self.assertFalse(dev & held);self.assertGreaterEqual(len(held),4)
        for case in self.cases:self.assertGreaterEqual(len(case['messages']),3)
        invalid=deepcopy(self.cases);invalid[-1]['family']=invalid[0]['family']
        with self.assertRaises(ValueError):quality.validate_cases(invalid)

    def test_missing_review_is_null_and_failed_answers_stay_in_denominator(self):
        attempts=[quality.attempt(self.case,self.result),quality.attempt(self.cases[1],{'status':503})]
        report=quality.summarize(attempts,[])
        self.assertEqual(report['attempts'],2);self.assertEqual(report['completed'],1)
        self.assertIsNone(report['human_claim_support']);self.assertFalse(report['promotion_eligible'])

    def test_review_is_bound_to_response_fixture_and_evidence(self):
        attempt=quality.attempt(self.case,self.result);review=self.review(attempt)
        report=quality.summarize([attempt],[review])
        self.assertEqual(report['human_claim_support'],1)
        for field in ('case_sha256','response_sha256','evidence_sha256'):
            forged={**review,field:'0'*64}
            with self.subTest(field=field),self.assertRaises(ValueError):quality.summarize([attempt],[forged])
        bad=deepcopy(review);bad['claims'][0]['evidence_ids']=['unknown-source']
        with self.assertRaises(ValueError):quality.summarize([attempt],[bad])

    def test_agent_scores_never_replace_human_review_and_uncertainty_is_explicit(self):
        attempt=quality.attempt(self.case,self.result);review=self.review(attempt,'agent')
        report=quality.summarize([attempt],[review]);self.assertIsNone(report['human_claim_support'])
        self.assertEqual(report['agent_claim_support'],1);self.assertFalse(report['promotion_eligible'])
        review=self.review(attempt);review['claims'][0]['verdict']='uncertain'
        report=quality.summarize([attempt],[review])
        self.assertEqual(report['uncertain_claims'],1);self.assertFalse(report['promotion_eligible'])
        with self.assertRaises(ValueError):quality.summarize([attempt],[review,review])

