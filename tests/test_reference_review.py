import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from runtime import reference_review as review
from runtime.text_filter import TextHeld, inspect_message


class ReviewTests(unittest.TestCase):
    def test_exact_owner_reference_only(self):
        text='Mathematical notation \x01 in a reviewed reference.'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'config').mkdir();(root/'runtime').mkdir()
            (root/'config/reference-reviews.json').write_text(json.dumps({'sources':{'math':{'text_sha256':[hashlib.sha256(text.encode()).hexdigest()]}}}))
            with patch.object(review,'__file__',str(root/'runtime/reference_review.py')):
                self.assertEqual(review.inspect_reference(text,'math'),text)
                with self.assertRaises(TextHeld):review.inspect_reference(text+' changed','math')
                with self.assertRaises(TextHeld):review.inspect_reference(text,'other')
                with self.assertRaises(TextHeld):inspect_message(text)

    def test_scanner_unavailable_cannot_be_approved(self):
        with patch.object(review,'inspect_message',side_effect=TextHeld('scan_unavailable',unavailable=True)):
            with self.assertRaises(TextHeld):review.inspect_reference('Example','math')

    def test_incomplete_scan_retains_failure_metadata(self):
        failure=TextHeld('unicode_carrier_or_incomplete_scan',scan_complete=False)
        with patch.object(review,'inspect_message',side_effect=failure):
            with self.assertRaises(TextHeld) as caught:review.inspect_reference('Example','math')
        self.assertIs(caught.exception,failure)
        self.assertIs(caught.exception.scan_complete,False)
