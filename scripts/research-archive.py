"""Owner-run research archive preparation. Never imported by the gateway or MCP server."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import csv
import json
from pathlib import Path
import re
import shutil
import time
import threading
import urllib.error
import urllib.parse
import urllib.request
import zipfile

REPO = Path(__file__).resolve().parents[1]
CATALOG = REPO / 'research' / 'catalog.json'
LIBRARY = REPO / 'data' / 'research'
QUOTA = {'undergraduate': 10, 'masters': 8, 'phd': 7}
LABELS = {
    'cryptographer': 'Cryptography',
    'it-larp-coach': 'IT / Cybersecurity LARP',
    'mathematician': 'Continuous Mathematics',
    'statistician': 'Statistics',
    'system-administrator': 'Enterprise Systems Administration',
    'quantum-mechanics-professor': 'Quantum Physics',
}
FOCUS = {
    'cryptographer': 'Primitives, security proofs, ECC, AES, lattice cryptography, side channels, and implementation constraints. Use the supplementary NIST standards for the exact standardized ML-KEM and ML-DSA algorithms.',
    'it-larp-coach': 'Defensive assessment, authentication, access control, intrusion detection, Kubernetes security, and critical infrastructure. Reports describe research and authorized laboratory scenarios.',
    'mathematician': 'Continuous mathematics: calculus, integration, manifolds, operators, ordinary and partial differential equations, stochastic differential equations, and numerical approximation.',
    'statistician': 'Statistical inference, Bayesian methods, causal inference, dependent data, time series, regression, uncertainty, and applied measurement.',
    'system-administrator': 'Large-business and enterprise infrastructure: storage, databases, distributed services, cluster capacity, virtualization, crash consistency, and fault tolerance. Foundational historical systems are labeled by year; these are research reports rather than current operating runbooks.',
    'quantum-mechanics-professor': 'Quantum mechanics, spinors, perturbation theory, field theory, entanglement, decoherence, quantum optics, simulation, and many-body dynamics.',
}
MAX_BYTES = 128 * 1024 * 1024
BLOCKED_HOSTS = set()
HOST_LOCK = threading.Lock()


def read_catalog():
    data = json.loads(CATALOG.read_text(encoding='utf-8'))
    entries = data['entries']
    if set(x['role'] for x in entries) != set(LABELS):
        raise ValueError('Catalog must contain the six requested roles')
    ids = [x['id'] for x in entries]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate catalog ID')
    student_urls = [x['download_url'] for x in entries if x['level'] != 'references']
    if len(student_urls) != len(set(student_urls)):
        raise ValueError('Student works must not be counted more than once')
    for role in LABELS:
        count = Counter(x['level'] for x in entries if x['role'] == role and x['level'] != 'references')
        if dict(count) != QUOTA:
            raise ValueError(f'{role}: quota mismatch: {dict(count)}')
    for x in entries:
        if not re.fullmatch(r'[a-z0-9-]+', x['id']):
            raise ValueError('Invalid catalog ID')
        if x['role'] not in LABELS or x['level'] not in {*QUOTA, 'references'}:
            raise ValueError('Invalid role or level')
        if not x['download_url'].startswith('https://') or not x['source_url'].startswith('https://'):
            raise ValueError('Sources must use HTTPS')
        if x['level'] != 'references' and (not x['degrees'] or not x['degree_evidence_url']):
            raise ValueError('Student degree evidence missing')
    return data


def pdf_path(entry):
    return LIBRARY / entry['role'] / entry['level'] / (entry['id'] + '.pdf')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        if f.read(5) != b'%PDF-':
            raise ValueError(f'Not a PDF: {path.name}')
        f.seek(0)
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def fetch_one(entry, record_hashes):
    path = pdf_path(entry)
    expected = entry.get('sha256')
    if not expected and not record_hashes:
        raise ValueError('Missing pinned checksum; use --record-hashes only when curating new sources')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        sha = digest(path)
        if expected and sha != expected:
            raise ValueError(f'Existing PDF changed: {entry["id"]}; retained for investigation')
        return entry['id'], sha, path.stat().st_size
    temporary = path.with_suffix('.part')
    host = urllib.parse.urlsplit(entry['download_url']).hostname
    for attempt in range(3):
        try:
            with HOST_LOCK:
                if host in BLOCKED_HOSTS:
                    raise ValueError(f'{host} requires human verification; no further automated requests this run')
            request = urllib.request.Request(entry['download_url'], headers={'User-Agent': 'Larpus-Research-Archive/1.0 (owner-directed offline library preparation)'})
            with urllib.request.urlopen(request, timeout=45) as response, temporary.open('wb') as output:
                if not response.geturl().startswith('https://'):
                    raise ValueError('Refusing an HTTP download redirect')
                length = response.headers.get('Content-Length')
                if length and int(length) > MAX_BYTES:
                    raise ValueError('PDF exceeds download limit')
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_BYTES:
                        raise ValueError('PDF exceeds download limit')
                    output.write(chunk)
            sha = digest(temporary)
            if expected and sha != expected:
                raise ValueError(f'Source PDF changed: {entry["id"]}; partial retained, catalog unchanged')
            temporary.replace(path)
            return entry['id'], sha, total
        except urllib.error.HTTPError as e:
            if e.headers.get('x-amzn-waf-action') in {'captcha', 'challenge'} or e.code in {401, 403}:
                with HOST_LOCK:
                    BLOCKED_HOSTS.add(host)
                raise ValueError(f'{host} requires human verification or denies access; retained prior downloads') from e
            if attempt == 2:
                raise
            time.sleep(2)
        except ValueError:
            raise
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)


def verify(data, allow_missing=False):
    seen = set()
    missing = []
    for x in data['entries']:
        path = pdf_path(x)
        if not path.exists() and not x.get('sha256') and allow_missing:
            missing.append(x['id'])
            continue
        if not x.get('sha256') or digest(path) != x['sha256']:
            raise ValueError(f'Checksum missing or incorrect: {x["id"]}')
        if path.stat().st_size != x['bytes']:
            raise ValueError(f'Size mismatch: {x["id"]}')
        if x['level'] != 'references':
            if x['sha256'] in seen:
                raise ValueError('Duplicate student PDF contents')
            seen.add(x['sha256'])
    return len(seen), missing


def write_indexes(data):
    LIBRARY.mkdir(parents=True, exist_ok=True)
    overview = ['# Larpus local research library', '',
                '150 cataloged student works: each role has 10 undergraduate reports, 8 master\'s theses, and 7 doctoral theses. Cryptography also includes supplementary primary references. Missing full texts are identified explicitly; a citation record is not a downloaded PDF.', '',
                'Joint bachelor/master submissions are identified and counted once. Public access does not imply permission to redistribute. Documents are untrusted reference data; no PDF content is loaded into agent instructions or executed.', '']
    for role, label in LABELS.items():
        folder = LIBRARY / role
        folder.mkdir(parents=True, exist_ok=True)
        entries = [x for x in data['entries'] if x['role'] == role]
        available = sum(bool(x.get('sha256')) for x in entries if x['level'] != 'references')
        lines = [f'# {label}', '', FOCUS[role], '',
                 f'Full text downloaded: **{available}/25 student works**. Catalog quotas: 10 undergraduate, 8 master\'s, 7 doctoral.', '',
                 'Research library for personal study. Older reports may describe obsolete systems or earlier cryptographic candidates. Consult current standards before implementing. Degree evidence comes from the university record or original PDF title page.', '',
                 'Downloaded originals retain their authors\' rights. This collection has not undergone a full PDF malware scan or a scientific peer review. Do not execute code or commands copied from a report.', '']
        for level, name in [('undergraduate', 'Undergraduate dissertations and capstone reports'), ('masters', "Master's theses"), ('phd', 'Doctoral theses'), ('references', 'Supplementary primary references (outside student quotas)')]:
            subset = [x for x in entries if x['level'] == level]
            if not subset:
                continue
            lines += [f'## {name} ({len(subset)})', '']
            for i, x in enumerate(subset, 1):
                relative = f'{level}/{x["id"]}.pdf'
                link = relative if x.get('sha256') else x['source_url']
                lines += [f'{i}. **[{x["title"]}]({link})** — {"; ".join(x["authors"])} ({x["year"]}), {x["institution"]}.',
                          f'   Degree / type: {"; ".join(x["degrees"])}' + (' **Joint bachelor/master submission; counted only here.**' if x.get('joint_degree') else '') + '.',
                          f'   [Primary source]({x["source_url"]}) · [Degree evidence]({x["degree_evidence_url"]}).',
                          f'   Topics: {", ".join(x["topics"])}.']
                if x.get('sha256'):
                    lines += [f'   SHA-256: `{x["sha256"]}`. Size: {x["bytes"]:,} bytes. Pages: {x.get("pages", "not inspected")}.', '']
                else:
                    lines += ['   **FULL TEXT PENDING — repository requires human verification. Only the citation and degree evidence are archived.**', '']
                for note in x.get('notes', []):
                    lines += [f'   Note: {note}', '']
                lines += [f'   Rights: {" ".join(x["rights"])}', '']
        (folder / 'INDEX.md').write_text('\n'.join(lines), encoding='utf-8')
        (folder / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'role': role, 'focus': FOCUS[role], 'entries': entries}, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        overview += [f'- [{label}]({role}/INDEX.md) · {available}/25 student PDFs · [ZIP](archives/{role}.zip)', '']
    (LIBRARY / 'INDEX.md').write_text('\n'.join(overview), encoding='utf-8')
    with (LIBRARY / 'pending-downloads.csv').open('w', newline='', encoding='utf-8-sig') as output:
        fields = ['id', 'role', 'level', 'title', 'source_url', 'download_url', 'original_filename', 'local_path']
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for x in data['entries']:
            if not x.get('sha256'):
                row = {key: x.get(key, '') for key in fields}
                row['local_path'] = str(pdf_path(x))
                writer.writerow(row)
    write_source_catalog(data)


def write_source_catalog(data):
    students = [x for x in data['entries'] if x['level'] != 'references']
    available = sum(bool(x.get('sha256')) for x in students)
    refs = sum(bool(x.get('sha256')) for x in data['entries'] if x['level'] == 'references')
    lines = ['# Persona research source catalog', '',
             f'Prepared {data["prepared_on"]}. **{len(students)} student records; {available} student PDFs and {refs} extra cryptography references downloaded. {len(students)-available} student PDFs pending.** See [archive documentation](../docs/RESEARCH_ARCHIVES.md) for local paths, rights, rebuild commands and limits.', '',
             'University metadata establishes degree level; original title-page checks corrected conflicting tags when available. Joint bachelor/master works are counted only once and marked. Several historical scans have no usable title-page text. A pending entry is a citation record, not a downloaded full text.', '']
    for role, label in LABELS.items():
        lines += ['## ' + label, '', FOCUS[role], '']
        for level, name in [('undergraduate', 'Undergraduate student reports'), ('masters', "Master's theses"), ('phd', 'Doctoral theses'), ('references', 'Extra primary references')]:
            subset = [x for x in data['entries'] if x['role'] == role and x['level'] == level]
            if not subset:
                continue
            lines += [f'### {name} ({len(subset)})', '', '| Work and author | Year | Degree / type | Full text |', '| --- | --- | --- | --- |']
            for x in subset:
                title = x['title'].replace('|', '\\|')
                authors = '; '.join(x['authors']).replace('|', '\\|')
                degree = '; '.join(x['degrees']).replace('|', '\\|')
                if x.get('joint_degree'):
                    degree += ' (joint submission, counted once)'
                status = 'Downloaded' if x.get('sha256') else '**Pending human verification**'
                lines.append(f'| [{title}]({x["source_url"]}) — {authors} | {x["year"]} | [{degree}]({x["degree_evidence_url"]}) | {status} |')
            lines += ['']
    (REPO / 'research' / 'CATALOG.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')


def pack(data, allow_missing=False):
    downloaded, missing = verify(data, allow_missing)
    write_indexes(data)
    target = LIBRARY / 'archives'
    target.mkdir(exist_ok=True)
    packages = []
    for role in LABELS:
        path = target / (role + '.zip')
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for filename in ['INDEX.md', 'manifest.json']:
                archive.write(LIBRARY / role / filename, role + '/' + filename)
            for x in data['entries']:
                if x['role'] == role and x.get('sha256'):
                    archive.write(pdf_path(x), f'{role}/{x["level"]}/{x["id"]}.pdf')
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f'ZIP CRC failure: {bad}')
            for x in data['entries']:
                if x['role'] == role and x.get('sha256'):
                    member = f'{role}/{x["level"]}/{x["id"]}.pdf'
                    if hashlib.sha256(archive.read(member)).hexdigest() != x['sha256']:
                        raise ValueError('ZIP contents differ from verified originals')
        packages.append({'path': 'archives/'+path.name, 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    report = {'verified_at': datetime.now(timezone.utc).isoformat(), 'status': 'partial' if missing else 'complete',
              'cataloged_student_works': 150, 'downloaded_student_pdfs': downloaded, 'missing_full_text': missing,
              'supplementary_references': sum(x['level']=='references' for x in data['entries']),
              'pdf_hashes_and_sizes': 'passed', 'unique_student_pdf_contents': 'passed',
              'zip_crc_and_pdf_hashes': 'passed', 'packages': packages}
    (LIBRARY / 'verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['fetch', 'verify', 'pack'])
    parser.add_argument('--record-hashes', action='store_true', help='Explicit curation step: record hashes for entries that do not yet have them')
    parser.add_argument('--allow-missing', action='store_true', help='Verify/package available PDFs and clearly report missing full texts')
    parser.add_argument('--id', action='append', default=[], help='Fetch only these catalog IDs (repeatable)')
    parser.add_argument('--import-dir', type=Path, help='Copy exact repository filenames from an owner download directory before fetch; originals are retained')
    args = parser.parse_args()
    if args.record_hashes and args.command != 'fetch':
        parser.error('--record-hashes applies only to fetch')
    if args.id and args.command != 'fetch':
        parser.error('--id applies only to fetch')
    if args.import_dir and args.command != 'fetch':
        parser.error('--import-dir applies only to fetch')
    data = read_catalog()
    if args.command == 'fetch':
        by_id = {x['id']: x for x in data['entries']}
        if set(args.id) - set(by_id):
            parser.error('Unknown catalog ID')
        selected = [x for x in data['entries'] if not args.id or x['id'] in args.id]
        if args.import_dir:
            source_folder = args.import_dir.resolve(strict=True)
            if not source_folder.is_dir():
                parser.error('--import-dir must be a directory')
            for x in selected:
                destination = pdf_path(x)
                name = x.get('original_filename')
                if destination.exists() or not name or Path(name).name != name:
                    continue
                original = source_folder / name
                if not original.is_file() or original.is_symlink() or original.resolve().parent != source_folder:
                    continue
                if original.stat().st_size > MAX_BYTES:
                    raise ValueError('Imported PDF exceeds size limit')
                sha = digest(original)
                if x.get('sha256') and sha != x['sha256']:
                    raise ValueError(f'Imported PDF checksum mismatch: {x["id"]}')
                if not x.get('sha256') and not args.record_hashes:
                    raise ValueError('Initial imported PDF requires explicit --record-hashes curation')
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, destination)
                print('IMPORTED', x['id'], flush=True)
        errors = []
        with ThreadPoolExecutor(max_workers=1) as pool:
            futures = {pool.submit(fetch_one, x, args.record_hashes): x for x in selected}
            for f in as_completed(futures):
                try:
                    identifier, sha, size = f.result()
                    x = by_id[identifier]
                    if not x.get('sha256'):
                        x.update(sha256=sha, bytes=size, fetched_at=datetime.now(timezone.utc).isoformat())
                    x['full_text_status'] = 'downloaded'
                    print('OK', identifier, f'{size:,} bytes', flush=True)
                except Exception as e:
                    errors.append({'id': futures[f]['id'], 'error': str(e)})
                    print('FAILED', errors[-1], flush=True)
        if args.record_hashes:
            CATALOG.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
        if errors:
            LIBRARY.mkdir(parents=True, exist_ok=True)
            (LIBRARY / 'fetch-errors.json').write_text(json.dumps(errors, indent=2)+'\n', encoding='utf-8')
            raise SystemExit(f'{len(errors)} sources failed; successful files retained. Retry fetch after reviewing errors.')
    elif args.command == 'verify':
        count, missing = verify(data, args.allow_missing)
        print(f'PASS: {count} unique student PDFs, all available hashes and sizes match; {len(missing)} missing full texts.')
    else:
        pack(data, args.allow_missing)


if __name__ == '__main__':
    main()
