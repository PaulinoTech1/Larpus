import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('research_refresh',ROOT/'scripts/research-refresh.py')
refresh=importlib.util.module_from_spec(spec);spec.loader.exec_module(refresh)

class RefreshTests(unittest.TestCase):
    def test_cached_checksum_change_is_held_without_overwriting(self):
        with tempfile.TemporaryDirectory() as temporary:
            file=Path(temporary)/'original.pdf';file.write_bytes(b'%PDF-test')
            with self.assertRaisesRegex(ValueError,'checksum changed'):
                refresh.fetch('https://www.usenix.org/system/files/test.pdf',file,pdf=True,expected='0'*64)
            self.assertEqual(file.read_bytes(),b'%PDF-test')

    def test_cached_html_cannot_masquerade_as_pdf(self):
        with tempfile.TemporaryDirectory() as temporary:
            file=Path(temporary)/'original.pdf';file.write_bytes(b'<html>challenge</html>')
            with self.assertRaisesRegex(ValueError,'not a PDF'):
                refresh.fetch('https://www.usenix.org/system/files/test.pdf',file,pdf=True)

    def test_unreviewed_redirect_refused(self):
        with self.assertRaises(ValueError):
            refresh.ReviewedRedirect().redirect_request(None,None,302,'',{},'https://example.org/private.pdf')

    def test_other_publisher_record_refused(self):
        with self.assertRaises(ValueError):
            refresh.vetted_host('https://www.nature.com/articles/unreviewed.pdf')

    def test_archive_traversal_identity_refused(self):
        with self.assertRaises(ValueError):refresh.validate_entry({'id':'../escape','rights':'personal'})

    def test_partial_download_batch_is_not_success(self):
        self.assertEqual(refresh.batch_exit([{'status':'download-or-screening-held'}]),1)
        self.assertEqual(refresh.batch_exit([{'status':'downloaded-pending-admission'}]),0)
