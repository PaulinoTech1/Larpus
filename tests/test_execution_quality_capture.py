import unittest
from scripts.benchmark_execution_profiles import QualityCapture


class QualityCaptureTests(unittest.TestCase):
    def test_disabled_retains_no_text(self):
        capture=QualityCapture(None)
        capture.text('A response.')
        self.assertEqual(capture.parts,[])
        self.assertFalse(capture.emit('case','verified',{}))

    def test_explicit_owner_sink_receives_bounded_approved_fields(self):
        records=[]
        capture=QualityCapture(records.append)
        capture.text('Checked reply.')
        capture.emit('case','verified',{'sources':[{'id':'source','preview':'Checked passage.'}],'citation_check':{'status':'identified'}})
        self.assertEqual(records[0]['answer'],'Checked reply.')
        self.assertEqual(records[0]['sources'][0]['id'],'source')
        self.assertNotIn('messages',records[0])

    def test_recording_failure_does_not_change_http_success(self):
        def fail(record):raise OSError('full disk')
        capture=QualityCapture(fail)
        capture.text('Checked reply.')
        self.assertFalse(capture.emit('case','verified',{}))
