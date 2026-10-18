import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from scripts.notes_append import load


class AppendTests(unittest.TestCase):
    def fixture(self, root):
        directory = root / 'data/notes-append/2025-2026'
        directory.mkdir(parents=True)
        text = 'A reviewed source passage describing a mathematical definition.'
        row = dict(source_id='example', locator='page 1 offset 0', text=text,
                   provenance={'id': 'example', 'published_on': '2025-01-01'})
        row['key'] = hashlib.sha256(('example|page 1 offset 0|' + text).encode()).hexdigest()[:32]
        raw = (json.dumps(row) + '\n').encode()
        (directory / 'windows.jsonl').write_bytes(raw)
        manifest = json.dumps({'windows': 1, 'queue_sha256': hashlib.sha256(raw).hexdigest()}).encode()
        (directory / 'manifest.json').write_bytes(manifest)
        (directory.parent / 'attached.json').write_text(json.dumps({'manifest_sha256': hashlib.sha256(manifest).hexdigest()}))
        return directory, row

    def test_no_attachment_preserves_legacy_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load(Path(tmp)), ([], {}))

    def test_pinned_windows_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, row = self.fixture(root)
            rows, metadata = load(root)
            self.assertEqual(rows, [row])
            self.assertEqual(metadata['example']['published_on'], '2025-01-01')

    def test_changed_queue_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, _ = self.fixture(Path(tmp))
            (directory / 'windows.jsonl').write_text('{}\n')
            with self.assertRaisesRegex(ValueError, 'queue checksum'):
                load(Path(tmp))
