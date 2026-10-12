"""Prepare an inert private append batch without changing the running notes queue."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.text_filter import inspect_message, TextHeld


def screened_parts(parser, raw):
    parts, held = [], []
    for locator, text in parser.extracted(raw, 'application/pdf'):
        for offset, part in parser.passages(text):
            if len(part) < 60:
                continue
            try:
                inspect_message(part)
            except TextHeld as exc:
                held.append({'locator': locator, 'offset': offset, 'reason': exc.reason})
            parts.append((locator + ' offset ' + str(offset), part))
    return parts, held


def grouped_windows(parts):
    local, buf, start = [], '', None
    for locator, text in parts:
        if start is None:
            start = locator
        buf += text + '\n'
        if len(buf) >= 4000:
            local.append((start, buf))
            buf, start = '', None
    if buf.strip():
        local.append((start, buf))
    return local


def source_parts(parser, record, raw):
    sid = record["id"]
    metadata = record.get('publisher_metadata', {})
    authors = record.get('authors') or metadata.get('citation_author', [])
    title = (metadata.get('citation_title') or [sid])[0]
    if not authors:
        raise ValueError('Missing publisher authors: ' + sid)
    parts, held = screened_parts(parser, raw)
    source = {key: record[key] for key in ('id', 'source_url', 'roles', 'sha256', 'rights', 'published_on', 'revised_on') if key in record}
    source.update(title=title, authors=authors, passages=len(parts))
    return source, parts, held


def prepare():
    folder = ROOT / 'data/research-refresh/2025-2026'
    receipt = folder / 'manifest.json'
    records = json.loads(receipt.read_text(encoding='utf-8'))['records']
    spec = importlib.util.spec_from_file_location('owner_extract', ROOT / 'scripts/prepare-knowledge.py')
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    output = ROOT / 'data/notes-append/2025-2026'
    output.mkdir(parents=True, exist_ok=True)
    windows, sources, excluded = [], [], []
    for record in records:
        sid = record['id']
        if record.get('status') != 'downloaded-pending-admission' or record.get('screening_status') != 'screened':
            excluded.append({'id': sid, 'reason': record.get('screening_status', record['status'])})
            continue
        raw = (folder / sid / 'original.pdf').read_bytes()
        if hashlib.sha256(raw).hexdigest() != record['sha256']:
            raise ValueError('Original checksum mismatch: ' + sid)
        source, parts, held = source_parts(parser, record, raw)
        title = source['title']
        if held:
            excluded.append({'id': sid, 'reason': 'index-segmentation-held', 'held': held})
            continue
        local = grouped_windows(parts)
        for locator, text in local:
            key = hashlib.sha256((sid + '|' + locator + '|' + text).encode()).hexdigest()[:32]
            windows.append({'key': key, 'source_id': sid, 'title': title, 'url': record['source_url'], 'locator': locator, 'text': text, 'provenance': source})
        source['windows'] = len(local)
        sources.append(source)
    windows.sort(key=lambda w: (w['provenance'].get('revised_on', w['provenance'].get('published_on', '9999')), w['source_id']))
    if len({w['key'] for w in windows}) != len(windows):
        raise ValueError('Duplicate append keys')
    queue = ''.join(json.dumps(w, ensure_ascii=False) + '\n' for w in windows).encode('utf-8')
    manifest = {'version': 1, 'status': 'prepared-not-attached', 'queue_sha256': hashlib.sha256(queue).hexdigest(), 'download_manifest_sha256': hashlib.sha256(receipt.read_bytes()).hexdigest(), 'base_index_sha256': hashlib.sha256((ROOT / 'knowledge/approved.sqlite').read_bytes()).hexdigest(), 'sources': sources, 'windows': len(windows), 'excluded': excluded, 'activation': 'Requires a separately validated queue reader or candidate index; current writer does not consume this file.'}
    for name, data in [('windows.jsonl', queue), ('manifest.json', (json.dumps(manifest, indent=2) + '\n').encode())]:
        target = output / name
        temp = target.with_suffix(target.suffix + '.tmp')
        temp.write_bytes(data)
        temp.replace(target)
    print(json.dumps({'status': manifest['status'], 'sources': len(sources), 'windows': len(windows), 'excluded': len(excluded)}))


if __name__ == '__main__':
    prepare()
