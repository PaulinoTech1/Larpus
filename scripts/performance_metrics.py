"""Numeric performance summaries; no automatic factual-answer scoring."""
from collections import Counter
import math
import statistics

STAGES=('input','retrieval','model_selection','model_first_frame','first_checked_text','inference_total','preflight','mcp_connect','mcp_total')


def numeric(value):
    return type(value) in (int,float) and math.isfinite(value) and value>=0


def distribution(values):
    values=sorted(v for v in values if numeric(v))
    if not values:return {'n':0,'median':None,'p90':None,'min':None,'max':None}
    return {'n':len(values),'median':round(statistics.median(values),3),'p90':round(values[math.ceil(len(values)*0.9)-1],3),
            'min':round(values[0],3),'max':round(values[-1],3)}


def summarize(rows):
    measured=[r for r in rows if r['phase']=='measured'];successful=[r for r in measured if r['ok']]
    return {'attempted':len(measured),'succeeded':len(successful),'success_rate':len(successful)/len(measured) if measured else None,
            'failures':dict(Counter(r.get('error','unknown') for r in measured if not r['ok'])),
            'partial_failures':sum(not r['ok'] and r.get('characters',0)>0 for r in measured),
            'first_text_seconds':distribution(r.get('first_text_seconds') for r in successful),
            'total_seconds':distribution(r.get('total_seconds') for r in successful),
            **timing_summary(successful)}


def timing_summary(successful):
    return {'stages_ms':{stage:distribution(r.get('stage_ms',{}).get(stage) for r in successful) for stage in STAGES},
            'complete_stage_samples':sum(all(stage in r.get('stage_ms',{}) for stage in STAGES) for r in successful),
            'unknown_citation_samples':sum(r.get('unknown_citations',0)>0 for r in successful)}


def compare(previous,current):
    if not previous['valid'] or not current['valid']:return {'comparable':False,'reason':'Run identity changed or run was interrupted.'}
    if previous['protocol']!=current['protocol']:return {'comparable':False,'reason':'Workload, seed, repetitions or warmup protocol changed.'}
    cases={}
    for identifier,result in current['per_case'].items():
        old=previous['per_case'][identifier]['first_text_seconds']['median'];new=result['first_text_seconds']['median']
        cases[identifier]={'median_change_seconds':round(new-old,3) if old is not None and new is not None else None,
                           'median_change_percent':round((new-old)/old*100,2) if old and new is not None else None,
                           'success_rate_before':previous['per_case'][identifier]['success_rate'],'success_rate_after':result['success_rate']}
    return {'comparable':True,'cases':cases,'identity_changes':identity_changes(previous,current),
            'scope':'Same workload/protocol, not identical environments. Descriptive difference; cache, load and environment can differ. Not a causal speedup claim.'}


def identity_changes(previous,current):
    old=previous.get('before',{});new=current.get('before',{})
    return {key:{'before':old.get(key),'after':new.get(key)} for key in sorted(set(old)|set(new)) if old.get(key)!=new.get(key)}


def markdown(report):
    lines=['# LARPUS performance run', '', 'Run: `'+report['id']+'`', 'Valid stable run: '+str(report['valid']),
           '', '| Case | Success / attempts | First text median / p90 (s) | Total median (s) | Complete stage samples |',
           '| --- | --- | --- | --- | --- |']
    for identifier,result in report['per_case'].items():
        first=result['first_text_seconds'];total=result['total_seconds']
        lines.append(f"| {identifier} | {result['succeeded']} / {result['attempted']} | {first['median']} / {first['p90']} | {total['median']} | {result['complete_stage_samples']} |")
    lines+=['','Warmups are excluded above. Percentiles use nearest rank; small samples are not a tail-latency guarantee.',
            'Failed attempts remain in success-rate denominators. Missing timing values are not zero.',
            'Stage timings overlap. API first checked text excludes browser paint and speech.',
            'Answer accuracy is pending rubric review; citation identifier consistency is not factual correctness.',
            '', '## Stage medians (ms)', '']
    for stage,result in report['summary']['stages_ms'].items():lines.append(f"- {stage}: {result['median']} (n={result['n']})")
    if report.get('comparison'):lines+=['','## Comparison','',str(report['comparison'])]
    return '\n'.join(lines)+'\n'
