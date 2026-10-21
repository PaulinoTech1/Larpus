"""Offline measurement admission, never deployment authority or inferred quality parity."""
from scripts.benchmark_execution_profiles import summarize,validated_rows
from scripts import quality_evaluation as quality

def _schedule(rows):
    validated_rows(rows)
    keys=[(row.get('case'),row.get('round')) for row in rows if not row.get('warmup',False)]
    if len(keys)!=len(set(keys)):raise ValueError('Duplicate measured schedule entry')
    return set(keys)

def _quality(attempts,reviews):
    cases={c['id']:c for c in quality.load_cases()}
    for attempt in attempts:
        case=cases.get(attempt['case_id'])
        if case is None or attempt['case_sha256']!=quality.digest(case):raise ValueError('Quality fixture changed')
    report=quality.summarize(attempts,reviews);reasons=[]
    if set(cases)!={row['case_id'] for row in attempts}:reasons.append('catalogue-coverage')
    if not report['human_review_complete'] or report['human_claim_support']!=1:reasons.append('quality-review')
    if report['uncertain_claims']:reasons.append('uncertain-claims')
    return report,reasons

def assess(baseline,candidate,attempts,reviews):
    if _schedule(baseline)!=_schedule(candidate):raise ValueError('Unmatched comparison schedule')
    quality_report,reasons=_quality(attempts,reviews)
    old,new=summarize(baseline),summarize(candidate)
    if new['failures']:reasons.append('candidate-failures')
    if old['failures']:reasons.append('baseline-failures')
    if new['attempts']<100:reasons.append('insufficient-attempts')
    reasons.extend(_timings(old,new))
    return {'eligible':not reasons,'reasons':reasons,'baseline':old,'candidate':new,'quality':quality_report,
            'promotion_eligible':False,'scope':'offline timing screen; measured-answer quality parity and rollout remain separate'}

def _timings(old,new):
    reasons=[];first=new.get('first_seconds')
    if first is None or first['samples']!=new['successes']:return ['incomplete-first-text-measurements']
    if first['mean']>5 or first['p95']>5:reasons.append('five-second-target')
    old_gap,new_gap=old.get('max_gap_seconds'),new.get('max_gap_seconds')
    if old_gap is None or new_gap is None:reasons.append('missing-pacing')
    elif old_gap['samples']!=old['successes'] or new_gap['samples']!=new['successes']:reasons.append('incomplete-pacing')
    elif new_gap['p95']>old_gap['p95']*1.10:reasons.append('pacing-regression')
    return reasons
