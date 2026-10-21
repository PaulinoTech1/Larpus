import unittest
from runtime.execution_trace import Trace

class ExecutionTraceTests(unittest.TestCase):
    def test_exclusive_stages_never_sum_overlapping_measurements(self):
        from runtime.execution_trace import exclusive_stages
        events={'input':10.,'retrieval':30.,'model_selection':35.,'model_first_text':45.,'first_approved':50.,'complete':80.,'gate_total':12.}
        result=exclusive_stages(events)
        self.assertEqual(sum(result.values()),80.)
        self.assertEqual(result['retrieval'],20.)
        self.assertEqual(result['generation_to_approved'],15.)
        self.assertNotIn('gate_total',result)
        self.assertEqual(exclusive_stages({'input':10.,'retrieval':9.}),{})
        self.assertEqual(exclusive_stages({'input':float('nan')}),{})
        self.assertEqual(exclusive_stages({'input':True}),{})

    def test_relative_bounded_numeric_marks(self):
        values=iter([1.,1.1,1.2])
        trace=Trace(True,lambda:next(values));trace.mark('input');trace.mark('retrieval')
        self.assertEqual(trace.snapshot(),{'input':100.,'retrieval':200.})
        with self.assertRaises(ValueError):trace.mark('C:/private/prompt')
    def test_disabled_has_no_clock_work(self):
        def clock():raise AssertionError('disabled trace clock')
        trace=Trace(False,clock);trace.mark('input');self.assertEqual(trace.snapshot(),{})
    def test_failed_clock_is_non_authoritative(self):
        trace=Trace(True,lambda:(_ for _ in ()).throw(OSError('private message')))
        trace.mark('input');self.assertEqual(trace.snapshot(),{})
    def test_screening_runs_once_and_tracks_duration_without_payload(self):
        values=iter([0.,1.,1.5])
        trace=Trace(True,lambda:next(values))
        calls=[]
        self.assertEqual(trace.screen(lambda text:calls.append(text) or {'status':422},'private'),{'status':422})
        self.assertEqual(calls,['private'])
        self.assertEqual(trace.snapshot()['gate_total'],500.)
        self.assertNotIn('private',str(trace.snapshot()))
    def test_approved_gap_uses_local_clock(self):
        values=iter([0.,1.,1.2])
        trace=Trace(True,lambda:next(values));trace.approved();trace.approved()
        self.assertEqual(trace.snapshot()['approved_gap_max'],200.)
