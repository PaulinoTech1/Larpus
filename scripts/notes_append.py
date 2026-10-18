"""Owner-side, pinned supplemental windows for the existing study-note writer."""
import hashlib
import json
from runtime.provenance import date_value
from runtime.text_filter import inspect_message
from runtime.reference_review import inspect_reference


def load(root):
    pointer = root / 'data/notes-append/attached.json'
    if not pointer.exists():
        return [], {}
    pin = json.loads(pointer.read_text(encoding='utf8'))
    directory = root / 'data/notes-append/2025-2026'
    manifest_bytes = (directory / 'manifest.json').read_bytes()
    if hashlib.sha256(manifest_bytes).hexdigest() != pin['manifest_sha256']:
        raise ValueError('Append manifest checksum mismatch')
    manifest = json.loads(manifest_bytes)
    raw = (directory / 'windows.jsonl').read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest['queue_sha256']:
        raise ValueError('Append queue checksum mismatch')
    rows = [json.loads(line) for line in raw.decode('utf8').splitlines()]
    if len(rows) != manifest['windows'] or len({r['key'] for r in rows}) != len(rows):
        raise ValueError('Append queue count or duplicate-key mismatch')
    for row in rows:
        validate(row)
    return rows, {r['source_id']: r['provenance'] for r in rows}


def validate(row):
    sid, loc, text = row['source_id'], row['locator'], row['text']
    key = hashlib.sha256((sid + '|' + loc + '|' + text).encode()).hexdigest()[:32]
    if row['key'] != key or row['provenance']['id'] != sid:
        raise ValueError('Append window identity mismatch')
    date_value(row['provenance'].get('published_on'))
    date_value(row['provenance'].get('revised_on'))
    inspect_reference(text, sid)


def source_metadata(appended, existing, sid):
    item = appended.get(sid)
    if item is None:
        return existing.get(sid, {'id': sid, 'document_authors_status': 'unknown'})
    return {**item, 'document_authors': item['authors'],
            'document_authors_status': 'reviewed publisher metadata'}
