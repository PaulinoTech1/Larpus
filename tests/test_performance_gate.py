import unittest
from scripts import performance_gate as gate
from scripts import quality_evaluation as quality

class PerformanceGateTests(unittest.TestCase):
    def rows(self,failed=False):
        return [{'case':'case-a','round':0,'ok':not failed,'first_seconds':1.,'total_seconds':2.,'max_gap_seconds':.1,'characters':10}]

    def test_unreviewed_quality_blocks_apparent_latency_win(self):
        result=gate.assess(self.rows(),self.rows(),[],[])
        self.assertFalse(result['eligible']);self.assertIn('quality-review',result['reasons'])

    def test_failed_attempts_and_unmatched_schedules_are_not_dropped(self):
        result=gate.assess(self.rows(),self.rows(True),[],[])
        self.assertEqual(result['candidate']['attempts'],1);self.assertEqual(result['candidate']['failures'],1)
        self.assertIn('candidate-failures',result['reasons'])
        other=self.rows();other[0]['round']=1
        with self.assertRaises(ValueError):gate.assess(self.rows(),other,[],[])

    def test_partial_catalogue_or_forged_quality_binding_cannot_unlock(self):
        case=quality.load_cases()[0]
        attempt=quality.attempt(case,{'status':200,'content':'Reviewed answer','sources':case['sources']})
        review={**{key:attempt[key] for key in quality.BOUND},'reviewer_kind':'human',
                'claims':[{'id':'claim-1','verdict':'supported','evidence_ids':[case['sources'][0]['id']]}]}
        result=gate.assess(self.rows(),self.rows(),[attempt],[review])
        self.assertIn('catalogue-coverage',result['reasons']);self.assertFalse(result['eligible'])
        attempt['case_sha256']='0'*64;review['case_sha256']='0'*64
        with self.assertRaises(ValueError):gate.assess(self.rows(),self.rows(),[attempt],[review])

    def test_one_pacing_sample_cannot_represent_one_hundred_answers(self):
        attempts=[];reviews=[]
        for case in quality.load_cases():
            row=quality.attempt(case,{'status':200,'content':'Reviewed synthetic answer','sources':case['sources']})
            attempts.append(row)
            reviews.append({**{key:row[key] for key in quality.BOUND},'reviewer_kind':'human',
                'claims':[{'id':'claim-1','verdict':'supported','evidence_ids':[case['sources'][0]['id']]}]})
        baseline=[{**self.rows()[0],'case':'case-'+str(i)} for i in range(100)]
        candidate=[dict(row) for row in baseline]
        for row in candidate[1:]:row.pop('max_gap_seconds')
        result=gate.assess(baseline,candidate,attempts,reviews)
        self.assertFalse(result['eligible']);self.assertIn('incomplete-pacing',result['reasons'])

