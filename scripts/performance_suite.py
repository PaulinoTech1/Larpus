"""Owner-only fixed HTTP performance suite. Default is a plan; --run uses local inference."""
import argparse
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import time
import urllib.request
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts import performance_metrics as metrics,performance_state as station
from scripts.performance_transport import probe

ROOT=Path(__file__).resolve().parents[1]
STORE=ROOT/'data/evals/performance'


def runner_fingerprint():
    digest=hashlib.sha256()
    for name in ('performance_suite.py','performance_metrics.py','performance_state.py','performance_transport.py'):
        digest.update(name.encode());digest.update((ROOT/'scripts'/name).read_bytes())
    return digest.hexdigest()


def catalog():
    raw=(ROOT/'evals/performance.json').read_bytes();value=json.loads(raw);ids=set()
    if value['version']!=1 or not 1<=len(value['cases'])<=32:raise ValueError('Invalid suite catalog')
    for case in value['cases']:
        if not re.fullmatch('[a-z0-9-]{1,64}',case['id']) or case['id'] in ids:raise ValueError('Invalid case ID')
        if case['persona'] not in ('home-assistant','it-larp-coach'):raise ValueError('Unsupported suite persona')
        if not case['review_points'] or not case['messages'] or case['messages'][-1]['role']!='user':raise ValueError('Invalid case')
        ids.add(case['id'])
    return value,hashlib.sha256(raw).hexdigest()


def schedule(cases,repeats,warmups,seed):
    result=[('warmup',r+1,c) for r in range(warmups) for c in cases]
    rng=random.Random(seed)
    for repeat in range(1,repeats+1):
        ordered=list(cases);rng.shuffle(ordered)
        result.extend(('measured',repeat,c) for c in ordered)
    return result


def write_json(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8');temporary.replace(path)


def run_samples(opener,plan,directory,retain):
    rows=[];review=[];previous=None
    with (directory/'observations.jsonl').open('w',encoding='utf-8') as observations:
        for phase,repeat,case in plan:
            started=time.perf_counter()
            gap=None if previous is None else round(started-previous,3)
            try:row,answer=probe(opener,case,retain)
            except KeyboardInterrupt:row,answer={'ok':False,'error':'interrupted','stage_ms':{},'first_text_seconds':None,'total_seconds':None},None
            previous=time.perf_counter()
            row.update(case=case['id'],phase=phase,repeat=repeat,since_previous_seconds=gap,sample_id=f"{phase}-{repeat}-{case['id']}")
            rows.append(row);observations.write(json.dumps(row,allow_nan=False)+'\n');observations.flush()
            if answer is not None:retain_answer(directory,case,row,answer)
            if phase=='measured':review.append({'sample_id':row['sample_id'],'case':case['id'],'released':row['ok'],'reviewer':None,'scores':None,'evidence_notes':None})
            print(json.dumps({k:row.get(k) for k in ('case','phase','repeat','ok','first_text_seconds','error')}),flush=True)
            if row.get('error')=='interrupted':raise KeyboardInterrupt
    return rows,review


def retain_answer(directory,case,row,answer):
    with (directory/'answers.jsonl').open('a',encoding='utf-8') as stream:
        stream.write(json.dumps({'sample_id':row['sample_id'],'case':case,'answer':answer['answer'],'sources':answer['sources']})+'\n')


def review_template(rows):
    return [{'sample_id':r['sample_id'],'case':r['case'],'released':r['ok'],'reviewer':None,'scores':None,'evidence_notes':None} for r in rows if r['phase']=='measured']


def warmup_counts(rows):
    warm=[r for r in rows if r['phase']=='warmup']
    return {'attempted':len(warm),'succeeded':sum(r['ok'] for r in warm)}


def finish(report,rows,review,rubric,directory,opener):
    try:report['after']=station.snapshot(opener)
    except (OSError,ValueError,KeyError):report['after']=None
    expected=len(report['protocol']['case_ids'])*(report['protocol']['repeats']+report['protocol']['warmups'])
    report['valid']=report['before']==report['after'] and len(rows)==expected and not report.get('interrupted',False)
    if 'runner_sha256' in report['protocol']:report['valid']=report['valid'] and runner_fingerprint()==report['protocol']['runner_sha256']
    review=review or review_template(rows)
    report['summary']=metrics.summarize(rows)
    report['per_case']={case:metrics.summarize([r for r in rows if r['case']==case]) for case in report['protocol']['case_ids']}
    report['warmup']=warmup_counts(rows)
    report['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    report['quality']={'status':'pending rubric review','automatic_factual_accuracy_score':None,'measured_samples':len(review)}
    write_json(directory/'review.json',{'run':report['id'],'rubric':rubric,'scope':'Each dimension 0-2; manual rubric score /10 is not an accuracy percentage. Review the retained answer and source passages.','items':review})
    write_json(directory/'report.json',report)
    (directory/'summary.md').write_text(metrics.markdown(report),encoding='utf-8')


def run(repeats=3,warmups=1,seed=5900,retain=False,baseline=None):
    value,digest=catalog();plan=schedule(value['cases'],repeats,warmups,seed)
    previous=json.loads((STORE/baseline/'report.json').read_text()) if baseline else None
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));before=station.snapshot(opener)
    directory=STORE/uuid.uuid4().hex;directory.mkdir(parents=True)
    protocol={'suite_sha256':digest,'runner_sha256':runner_fingerprint(),'repeats':repeats,'warmups':warmups,'seed':seed,'case_ids':[c['id'] for c in value['cases']]}
    if previous and previous['protocol']!=protocol:raise ValueError('Baseline workload, runner or protocol differs')
    report={'version':1,'id':directory.name,'before':before,'protocol':protocol,'environment':station.host_environment(),
            'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'valid':False,'retain_answers':retain,
            'limits':'Fixed HTTP workload. Conditioning is not a cold model test. No model switch, quota change, browser rendering or physical voice test. Failures are not retried.'}
    write_json(directory/'report.json',report);rows=[];review=[]
    try:rows,review=run_samples(opener,plan,directory,retain)
    except KeyboardInterrupt:
        report['interrupted']=True
    finally:
        rows=[json.loads(line) for line in (directory/'observations.jsonl').read_text().splitlines()]
        finish(report,rows,review,value['rubric'],directory,opener)
    if previous:
        report['comparison']=metrics.compare(previous,report)
        write_json(directory/'report.json',report);(directory/'summary.md').write_text(metrics.markdown(report),encoding='utf-8')
    print('Report: '+str(directory/'summary.md'),flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true');parser.add_argument('--repeats',type=int,choices=range(1,11),default=3)
    parser.add_argument('--warmups',type=int,choices=range(3),default=1);parser.add_argument('--seed',type=int,default=5900)
    parser.add_argument('--retain-answers',action='store_true');parser.add_argument('--baseline')
    args=parser.parse_args()
    if args.baseline and not re.fullmatch('[a-f0-9]{32}',args.baseline):parser.error('baseline must be a run ID')
    value,_=catalog();plan=schedule(value['cases'],args.repeats,args.warmups,args.seed)
    print(json.dumps({'planned_requests':len(plan),'phases':dict(Counter(phase for phase,_,_ in plan)),'running':args.run}),flush=True)
    if args.run:
        report=run(args.repeats,args.warmups,args.seed,args.retain_answers,args.baseline)
        return 0 if report['valid'] and report['summary']['succeeded']==report['summary']['attempted'] else 1
    return 0


if __name__=='__main__':raise SystemExit(main())
