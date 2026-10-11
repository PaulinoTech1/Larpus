"""Prepare now; explicitly run later from a prepared sealed release, after notes."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime import capability_trials as trials


@contextmanager
def locked(path):
    with Path(str(path)+'.lock').open('a+b') as f:
        f.seek(0)
        if not f.read(1):
            f.write(b'0'); f.flush()
        f.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            f.seek(0)
            if os.name == 'nt':
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)


def note_gate():
    if os.name != 'nt':
        raise ValueError('Live trials require the owner Windows station')
    # Fixed owner-side probe; no credentials, process command lines or agent tools.
    script = r"""
$ErrorActionPreference='Stop'
$et=[TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTime]::UtcNow,'Eastern Standard Time')
$workers=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^python(w)?(\.exe)?$' -and $_.CommandLine -match 'study-notes\.py\s+(generate|answers|publish)'})
$task=Get-ScheduledTask -TaskName 'LARPUS Study Notes' -ErrorAction Stop
@{night=($et.Hour -ge 20 -or $et.Hour -lt 10);busy=($workers.Count -gt 0 -or $task.State -eq 'Running')} | ConvertTo-Json -Compress
"""
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                            capture_output=True, text=True, timeout=30, check=True)
    state = json.loads(result.stdout)
    if type(state.get('night')) is not bool or type(state.get('busy')) is not bool:
        raise ValueError('Unable to verify note-generation state')
    if state['night'] or state['busy']:
        raise ValueError('Live trials deferred: nightly window or study-note work is active')


def environment(root):
    from runtime.isolation import mode
    from scripts.releases import payload
    meta = trials.read(root/'release.json')
    if meta.get('status') != 'prepared' or mode() != 'wsl-podman' or payload(root) != meta.get('files'):
        raise ValueError('Run only from a verified prepared frozen release using sealed MCP')
    names = ('knowledge/manifest.json', 'knowledge/embeddings-manifest.json',
             'knowledge/notes-manifest.json', 'config/models.json')
    return {'release': meta['id'], 'source_fingerprint': meta['source_fingerprint'],
            'pins': {n: hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names}}


def execute(path, notes_finished, bank_reviewed, root=ROOT):
    if not notes_finished or not bank_reviewed:
        raise ValueError('Deferred: explicit --notes-finished and --bank-reviewed confirmations are required')
    with locked(path):
        plan = trials.validate(trials.read(path))
        if plan['state'] == 'complete':
            raise ValueError('Completed run retained; prepare a separate repeat with a new output filename')
        note_gate()
        env = environment(root)
        if plan['environment'] is not None and plan['environment'] != env:
            raise ValueError('Runtime/source pins changed; cannot mix environments in a resumed run')
        from runtime.agents import load_personas
        trials.bank(plan['bank'], load_personas())
        from runtime.mcp_client import chat
        plan.update(state='running', environment=env)
        if plan['authorization'] is None:
            plan['authorization'] = {'notes_finished_attested': True, 'bank_reviewed_attested': True, 'at': trials.now()}
        trials.save(path, plan)
        seen = {(r['case'], r['arm']) for r in plan['results']}
        for i, case in enumerate(plan['bank']['cases']):
            # Alternate AB/BA to reduce fixed order effects; each call is stateless.
            for arm in (('baseline', 'candidate') if i % 2 == 0 else ('candidate', 'baseline')):
                if (case['id'], arm) in seen:
                    continue
                note_gate()
                if environment(root) != env:
                    raise ValueError('Runtime changed during trial; progress retained')
                content = trials.PREFIX + json.dumps({'question': case['prompt'],
                          'profile': plan['profiles'][arm], 'mode': 'trial'})
                started = time.monotonic()
                # No rubric, answer key, journal prose or earlier answers reach inference.
                answer = chat(plan['bank']['persona'], [{'role': 'user', 'content': content}], plan['bank']['skill'])
                row = {'case': case['id'], 'arm': arm, 'status': answer.get('status', 502),
                       'answer': answer.get('content', ''), 'sources': answer.get('sources', []),
                       'citation_check': answer.get('citation_check'), 'seconds': round(time.monotonic()-started, 3),
                       'review': None}
                plan['results'].append(row)
                trials.validate(plan)
                trials.save(path, plan)
                print(case['id']+' / '+arm+' / '+str(row['status']), flush=True)
        plan['state'] = 'complete'
        trials.save(path, plan)
    return plan


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    check = sub.add_parser('validate'); check.add_argument('--bank', type=Path, default=ROOT/'evals/capability-linear-algebra.json')
    prep = sub.add_parser('prepare'); prep.add_argument('--bank', type=Path, default=ROOT/'evals/capability-linear-algebra.json')
    prep.add_argument('--journal', type=Path); prep.add_argument('--baseline', default='v0'); prep.add_argument('--candidate', default='method:worked-example'); prep.add_argument('--output', type=Path, required=True)
    run = sub.add_parser('run'); run.add_argument('path', type=Path); run.add_argument('--notes-finished', action='store_true'); run.add_argument('--bank-reviewed', action='store_true')
    score = sub.add_parser('score'); score.add_argument('path', type=Path); score.add_argument('--case', required=True); score.add_argument('--arm', choices=('baseline','candidate'), required=True); score.add_argument('--scores', type=int, nargs=4, required=True, metavar=('CORRECT','REASON','TEACH','GROUND')); score.add_argument('--reviewer', required=True); score.add_argument('--note', required=True)
    comp = sub.add_parser('compare'); comp.add_argument('path', type=Path)
    a = p.parse_args()
    try:
        if a.action in ('validate', 'prepare'):
            from runtime.agents import load_personas
            catalog = trials.bank(trials.read(a.bank), load_personas())
            if a.action == 'validate':
                print(json.dumps({'cases': len(catalog['cases']), 'review': catalog.get('review_status'), 'live': False})); return
            journal = trials.read(a.journal) if a.journal else {}
            plan = trials.prepare(catalog, journal, a.baseline, a.candidate)
            a.output.parent.mkdir(parents=True, exist_ok=True)
            with locked(a.output):
                if a.output.exists():
                    raise ValueError('Output exists; choose a new filename to retain prior trials')
                trials.save(a.output, plan)
            print(json.dumps({'path': str(a.output), 'state': plan['state'], 'cases': len(catalog['cases']), 'live': False})); return
        if a.action == 'run':
            execute(a.path, a.notes_finished, a.bank_reviewed)
        elif a.action == 'score':
            with locked(a.path):
                plan = trials.validate(trials.read(a.path))
                row = next((r for r in plan['results'] if r['case'] == a.case and r['arm'] == a.arm), None)
                if not row or row['review'] is not None:
                    raise ValueError('Choose an unscored completed response; existing reviews are retained')
                row['review'] = {'scores': dict(zip(('correctness','reasoning','teaching','grounding'), a.scores)), 'reviewer': a.reviewer, 'note': a.note, 'at': trials.now()}
                trials.validate(plan); trials.save(a.path, plan)
        print(json.dumps(trials.compare(trials.read(a.path)), indent=2))
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        p.exit(1, 'Capability trial: '+str(exc)+'\n')


if __name__ == '__main__':
    main()
