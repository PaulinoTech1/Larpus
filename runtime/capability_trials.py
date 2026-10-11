"""Owner-side capability comparison artifacts. Never imported by inference."""
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from runtime.teaching import OPTIONS, PREFIX, unpack


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    path = Path(path)
    if path.stat().st_size > 2_000_000:
        raise ValueError('Trial artifact exceeds limit')
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    """Atomic replacement for resumable progress; caller owns the run lock."""
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix=path.name+'.', suffix='.tmp', delete=False) as f:
        temporary = Path(f.name)
        json.dump(value, f, indent=2, ensure_ascii=True)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    temporary.replace(path)


def bank(value, personas):
    if not isinstance(value, dict) or value.get('version') != 1 or not isinstance(value.get('cases'), list) or not 4 <= len(value['cases']) <= 50:
        raise ValueError('Invalid capability bank')
    persona = personas.get(value.get('persona'))
    if not persona or value.get('skill') not in (None, *persona.get('skills', [])):
        raise ValueError('Unknown bank role or skill')
    ids = set()
    for c in value['cases']:
        if (not isinstance(c, dict) or not isinstance(c.get('id'), str) or not c['id'] or c['id'] in ids
                or c.get('split') not in ('practice', 'held-out')
                or not isinstance(c.get('prompt'), str) or not 1 <= len(c['prompt']) <= 2000
                or not isinstance(c.get('reference'), dict)
                or not all(isinstance(c['reference'].get(k), str) and c['reference'][k] for k in ('source_id', 'locator'))
                or set(c.get('rubric', {})) != {'correctness', 'reasoning', 'teaching', 'grounding'}
                or any(not isinstance(v, str) or not v.strip() or len(v) > 1000 for v in c['rubric'].values())):
            raise ValueError('Invalid capability case')
        ids.add(c['id'])
    if {c['split'] for c in value['cases']} != {'practice', 'held-out'}:
        raise ValueError('Both practice and held-out cases are required')
    return value


def profile(journal, scope, selector):
    if not isinstance(journal, dict) or journal and (journal.get('version') != 1 or not isinstance(journal.get('profiles'), list) or not isinstance(journal.get('experiments'), list)):
        raise ValueError('Invalid teaching journal export')
    p = next((p for p in journal.get('profiles', []) if p.get('scope') == scope), None)
    if selector == 'v0':
        settings = {k: v[0] for k, v in OPTIONS.items()}
    elif selector.startswith('method:') and selector[7:] in OPTIONS['method']:
        settings = {k: v[0] for k, v in OPTIONS.items()}
        settings['method'] = selector[7:]
    elif selector.startswith('v') and selector[1:].isdigit():
        n = int(selector[1:])
        if not p or not 1 <= n <= len(p['versions']):
            raise ValueError('Profile version not found')
        settings = p['versions'][n-1]['settings']
    elif selector.startswith('trial:') and selector[6:].isdigit():
        e = next((e for e in journal.get('experiments', []) if e.get('scope') == scope and e.get('id') == int(selector[6:])), None)
        if not e:
            raise ValueError('Trial profile not found')
        settings = e['settings']
    else:
        raise ValueError('Use v0, vNUMBER, trial:NUMBER or method:METHOD')
    # Share the actual runtime's enum validator, not an alternate prompt schema.
    unpack(PREFIX + json.dumps({'question': 'Validation', 'profile': settings, 'mode': 'trial'}))
    return dict(settings)


def prepare(catalog, journal, baseline, candidate):
    scope = catalog['persona'] + '|' + (catalog['skill'] or '')
    profiles = {name: profile(journal, scope, selected) for name, selected in [('baseline', baseline), ('candidate', candidate)]}
    if profiles['baseline'] == profiles['candidate']:
        raise ValueError('Baseline and candidate must differ')
    identity = {'bank': catalog, 'profiles': profiles}
    return {'version': 1, 'id': digest(identity)[:24], 'created': now(),
            'state': 'deferred', **identity, 'plan_sha256': digest(identity),
            'selectors': {'baseline': baseline, 'candidate': candidate},
            'authorization': None, 'environment': None, 'results': [],
            'notice': 'Live execution deferred until owner confirms notes finished and bank reviewed. No automatic promotion.'}


def validate(plan):
    if (not isinstance(plan, dict) or not {'bank','profiles','results','environment','authorization','id','plan_sha256'}.issubset(plan)
            or plan.get('version') != 1 or plan.get('state') not in ('deferred', 'running', 'complete')
            or digest({'bank': plan['bank'], 'profiles': plan['profiles']}) != plan.get('plan_sha256')
            or plan.get('id') != plan['plan_sha256'][:24]):
        raise ValueError('Trial plan changed or invalid')
    if set(plan['profiles']) != {'baseline', 'candidate'}:
        raise ValueError('Invalid comparison arms')
    for settings in plan['profiles'].values():
        unpack(PREFIX + json.dumps({'question': 'Validation', 'profile': settings, 'mode': 'trial'}))
    if not isinstance(plan['results'], list) or len(plan['results']) > 100:
        raise ValueError('Invalid result inventory')
    valid_ids = {c['id'] for c in plan['bank']['cases']}
    seen = set()
    for r in plan['results']:
        if not isinstance(r, dict):
            raise ValueError('Invalid trial result')
        key = r.get('case'), r.get('arm')
        if key[0] not in valid_ids or key[1] not in plan['profiles'] or key in seen:
            raise ValueError('Invalid or duplicate trial result')
        seen.add(key)
        if (type(r.get('status')) is not int or not isinstance(r.get('answer'), str)
                or len(r['answer']) > 65536 or not isinstance(r.get('sources'), list)
                or not isinstance(r.get('seconds'), (int, float)) or not math.isfinite(r['seconds']) or r['seconds'] < 0):
            raise ValueError('Invalid trial response')
        if r.get('review') is not None:
            review(r['review'])
            if r['status'] != 200 or not r['answer'].strip():
                raise ValueError('Cannot score an unreleased answer')
    if plan['state'] == 'complete' and len(seen) != 2 * len(valid_ids):
        raise ValueError('Incomplete comparison cannot be marked complete')
    return plan


def review(value):
    if (not isinstance(value, dict) or set(value) != {'scores', 'reviewer', 'note', 'at'}
            or not isinstance(value['scores'], dict) or set(value['scores']) != {'correctness', 'reasoning', 'teaching', 'grounding'}
            or any(type(v) is not int or not 0 <= v <= 2 for v in value['scores'].values())
            or any(not isinstance(value.get(k), str) or not 1 <= len(value[k].strip()) <= 1000 for k in ('reviewer', 'note', 'at'))):
        raise ValueError('Manual review needs four 0-2 scores, reviewer and evidence note')


def compare(plan):
    validate(plan)
    summary = {'plan': plan['id'], 'state': plan['state'], 'splits': {},
               'limitations': 'Paired descriptive scores only; manual ratings are not independent learning outcomes. No automatic winner or profile promotion.'}
    results = {(r['case'], r['arm']): r for r in plan['results']}
    for split in ('practice', 'held-out'):
        cases = [c for c in plan['bank']['cases'] if c['split'] == split]
        paired = [(results.get((c['id'], 'baseline')), results.get((c['id'], 'candidate'))) for c in cases]
        scored = [(a, b) for a, b in paired if a and b and a.get('review') and b.get('review')]
        summary['splits'][split] = {'cases': len(cases), 'scored_pairs': len(scored),
            'failed_or_held_responses': sum(r is not None and (r['status'] != 200 or not r['answer'].strip()) for pair in paired for r in pair),
            'mean_candidate_minus_baseline': {k: round(sum(b['review']['scores'][k]-a['review']['scores'][k] for a, b in scored)/len(scored), 3) for k in ('correctness', 'reasoning', 'teaching', 'grounding')} if scored else None}
    return summary
