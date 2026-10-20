"""Owner-local secure HTTP measurements. Never a direct-model bypass client."""
import argparse
from contextlib import nullcontext
import hashlib
import json
import math
from pathlib import Path
import random
import re
import statistics
import sys
import time
import urllib.request
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
PROFILES=('verified','ultra-fast','diagnostic')
NUMERIC=('first_seconds','total_seconds','max_gap_seconds','characters')
FIELDS=set(NUMERIC)|{'ok','case','profile','round','session','warmup','stage_ms','failure','telemetry','quality_recorded'}

def validate_url(value):
    parsed=urlsplit(value)
    if parsed.scheme!='http' or parsed.netloc!='127.0.0.1:8080' or parsed.path or parsed.query or parsed.fragment:
        raise ValueError('Only the existing owner-loopback gateway is supported')
    return value

def schedule(cases,rounds,seed):
    generator=random.Random(seed)
    rows=[]
    for repeat in range(rounds):
        ordered=list(cases)
        generator.shuffle(ordered)
        for case in ordered:
            profiles=list(PROFILES)
            generator.shuffle(profiles)
            rows.extend({'case':case['id'],'profile':profile,'round':repeat} for profile in profiles)
    return rows

def validated_rows(rows):
    for row in rows:
        if type(row) is not dict or set(row)-FIELDS or type(row.get('ok')) is not bool:
            raise ValueError('Invalid numeric benchmark row')
        for key in NUMERIC:
            if key in row and (type(row[key]) not in (int,float) or not math.isfinite(row[key]) or row[key]<0):
                raise ValueError('Invalid numeric measurement')
    return rows

def percentile(values,fraction):
    ordered=sorted(values)
    index=(len(ordered)-1)*fraction
    lower=int(index)
    return ordered[lower]+(ordered[math.ceil(index)]-ordered[lower])*(index-lower)

def metrics(values):
    if not values:return None
    return {'mean':statistics.mean(values),'median':statistics.median(values),
            'p95':percentile(values,.95),'p99':percentile(values,.99),
            'stddev':statistics.stdev(values) if len(values)>1 else 0.,
            'min':min(values),'max':max(values),'samples':len(values)}

def summarize(rows):
    measured=[r for r in validated_rows(rows) if not r.get('warmup',False)]
    successes=[r for r in measured if r['ok']]
    return {'attempts':len(measured),'successes':len(successes),'failures':len(measured)-len(successes),
            **{key:metrics([r[key] for r in successes if key in r]) for key in NUMERIC},
            'resources':resource_summary(successes),
            'quality':'unreviewed','task_success':None,
            'scope':'HTTP first approved text, excludes browser paint and voice; p99 is descriptive'}

def resource_summary(rows):
    traces=[r['telemetry'] for r in rows if isinstance(r.get('telemetry'),dict)]
    cpu=[item['host_cpu_percent'] for item in traces if type(item.get('host_cpu_percent')) in (int,float)]
    gpu=[item['gpu_after'] for item in traces if isinstance(item.get('gpu_after'),dict)]
    return {'host_cpu_percent':metrics(cpu),
            'gpu_boundary':{key:metrics([item[key] for item in gpu]) for key in ('temperature_c','power_w','clock_mhz','utilization_percent')},
            'scope':'host/boundary only; no CPU temperature or container attribution'}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('Benchmark redirects prohibited')

class ComparisonChanged(ValueError):
    """Inputs differ from the declared comparison; abort rather than pool."""

class QualityCapture:
    """Explicit owner review artifact, separate from ordinary numeric traces."""
    def __init__(self,sink):self.sink=sink;self.parts=[];self.size=0
    def text(self,text):
        if self.sink is None:return
        self.size+=len(text.encode('utf-8'))
        if self.size>65536:raise ValueError('Oversized review answer')
        self.parts.append(text)
    def emit(self,case,profile,event):
        if self.sink is None:return False
        record={'case':case,'profile':profile,'answer':''.join(self.parts),
                'sources':event.get('sources',[]),'citation_check':event.get('citation_check',{})}
        if len(json.dumps(record).encode())>400000:return False
        try:self.sink(record);return True
        except OSError:return False

def check_receipt(receipt,profile,expected):
    if not isinstance(receipt,dict):raise ComparisonChanged('Missing served identity')
    actual={key:receipt.get(key) for key in ('source_fingerprint','model')}
    if actual!=expected or receipt.get('profile')!=profile:raise ComparisonChanged('Served execution changed')

def probe(opener,url,case,profile,expected,review=None):
    execution={'profile':profile,'interaction':case.get('interaction','conversation')}
    if profile=='diagnostic':execution['base']='verified'
    body=json.dumps({'persona':case['persona'],'messages':case['messages'],'execution':execution}).encode()
    request=urllib.request.Request(url+'/api/chat/stream',body,{'Content-Type':'application/json'})
    started=time.perf_counter()
    first=last=None
    gaps=[]
    characters=0
    complete=False
    stages={}
    capture=QualityCapture(review);final={}
    with opener.open(request,timeout=200) as response:
        while True:
            line=response.readline(400001)
            if not line:break
            if len(line)>400000:raise ValueError('Oversized benchmark event')
            event=json.loads(line)
            if event.get('type')=='error':raise ValueError('Secure gateway held reply')
            if event.get('type')=='text' and event.get('content'):
                now=time.perf_counter()
                if first is None:first=now-started
                if last is not None:gaps.append(now-last)
                last=now
                characters+=len(event['content'])
                capture.text(event['content'])
            if event.get('type')=='done':
                if complete:raise ValueError('Duplicate completion')
                complete=True
                check_receipt(event.get('execution'),profile,expected)
                stages=numeric_stages(event.get('timing_ms',{}))
                final=event
    require_complete(complete,first)
    elapsed=time.perf_counter()-started
    return {'ok':True,'first_seconds':first,'total_seconds':elapsed,
            'max_gap_seconds':max(gaps,default=0.),'characters':characters,'stage_ms':stages,
            'telemetry':None,'quality_recorded':capture.emit(case['id'],profile,final)}

def require_complete(complete,first):
    if not complete or first is None:raise ValueError('Incomplete benchmark response')

def numeric_stages(value):
    names=('input','retrieval','model_selection','model_first_frame','first_checked_text',
           'inference_total','preflight','mcp_connect','mcp_total')
    return {key:item for key,item in value.items() if key in names and type(item) in (int,float) and math.isfinite(item) and item>=0}

def pinned_inputs(identifier=None):
    active=json.loads((ROOT/'data/releases/active.json').read_text(encoding='utf-8'))['id']
    if not isinstance(active,str) or not re.fullmatch('[a-f0-9]{32}',active):raise ValueError('Invalid selected release')
    measured=active if identifier is None else identifier
    if not isinstance(measured,str) or not re.fullmatch('[a-f0-9]{32}',measured):raise ValueError('Invalid measured release')
    served=ROOT/'data/releases'/measured
    deployment=json.loads((served/'deployment.json').read_text(encoding='utf-8'))
    names=('deployment.json','config/model-selection.json','config/inference-broker.json',
           'config/broker-prompts.json','config/isolation.json','config/cpu-retrieval.json',
           'knowledge/manifest.json','config/dlp.json','skills/registry.json','release-state/security/summary.json')
    return {'selected_release':active,'measured_release':measured,'source_fingerprint':deployment['source_fingerprint'],
            **{name:hashlib.sha256((served/name).read_bytes()).hexdigest() for name in names if (served/name).is_file()}}

def served_model(opener,url):
    with opener.open(url+'/api/model-selection',timeout=30) as response:
        raw=response.read(65537)
    if len(raw)>65536:raise ComparisonChanged('Oversized model state')
    state=json.loads(raw)
    if state.get('phase')!='ready':raise ComparisonChanged('Model is switching')
    selected=next(item for item in state['models'] if item['id']==state['active_id'])
    if selected['tag'] not in ('qwen3.5:27b-q4_K_M','larpus3.8:27b-q4'):raise ComparisonChanged('Unapproved model state')
    return selected['tag']

def pipeline_identity(value):
    ids=('numpy','assembly','assembly-optimized')
    if value.get('active_id') not in ids or value.get('requested_id') not in ids or type(value.get('workers')) is not int:
        raise ValueError('Invalid pipeline state')
    return value['active_id'],value['requested_id'],value['workers']

def served_pipeline(opener,url):
    with opener.open(url+'/api/retrieval-pipeline',timeout=30) as response:
        raw=response.read(65537)
    if len(raw)>65536:raise ComparisonChanged('Oversized pipeline state')
    return list(pipeline_identity(json.loads(raw)))

def comparison_controls(opener,url):
    return {'model':served_model(opener,url),'pipeline':served_pipeline(opener,url)}

def output_directory(value):
    directory=Path(value).resolve()
    expected=(ROOT/'data/execution-profiles').resolve()
    if not directory.is_relative_to(expected) or directory==expected:
        raise ValueError('Use a new child directory under E: project data/execution-profiles')
    return directory

def write_report(directory,manifest,rows):
    report={profile:summarize([r for r in rows if r['profile']==profile]) for profile in PROFILES}
    (directory/'report.json').write_text(json.dumps({'manifest':manifest,'profiles':report},indent=2),encoding='utf-8')
    lines=['# Secure execution benchmark','', 'Quality and task success require independent rubric review. Resource mode: '+str(manifest.get('telemetry','unknown'))+'.','']
    for profile,summary in report.items():
        lines.extend([f'## {profile}','',json.dumps(summary,indent=2),''])
    (directory/'report.md').write_text('\n'.join(lines),encoding='utf-8')

def session_input(directory):
    directory=Path(directory)
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    path=directory/'rows.jsonl'
    if path.stat().st_size>20_000_000:raise ValueError('Oversized measurement file')
    rows=validated_rows([json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()])
    if any(row.get('session')!=manifest['session'] for row in rows):raise ValueError('Session mismatch')
    return manifest,rows

def combine_sessions(directories):
    if len(directories)!=2:raise ValueError('Exactly two sessions required')
    first,left=session_input(directories[0])
    second,right=session_input(directories[1])
    if {first['session'],second['session']}!={1,2}:raise ValueError('Distinct sessions required')
    for key in ('pins','workload_sha256','schedule','seed','diagnostic_base','run','served_model','controls'):
        if first[key]!=second[key]:raise ValueError('Mismatched comparison inputs')
    if first.get('telemetry')!=second.get('telemetry'):raise ValueError('Mismatched telemetry mode')
    if first.get('review_records')!=second.get('review_records'):raise ValueError('Mismatched review capture mode')
    rows=left+right
    check_complete_samples(rows,first['schedule'])
    return {**first,'session':None,'sessions':[1,2]},rows

def check_complete_samples(rows,planned):
    measured=[r for r in rows if not r.get('warmup',False)]
    identities={(r['case'],r['profile'],r['round']) for r in measured}
    if len(identities)!=len(measured):raise ValueError('Duplicate measurements')
    expected={(r['case'],r['profile'],r['round']) for r in planned}
    if not expected or identities!=expected:raise ValueError('Measurements do not match manifest schedule')
    if any(r['round']%2!=r['session']-1 for r in measured):raise ValueError('Wrong session partition')
    check_sample_counts(measured)

def check_sample_counts(measured):
    counts=[sum(row['profile']==profile for row in measured) for profile in PROFILES]
    if min(counts)<100 or len(set(counts))!=1:raise ValueError('Need at least 100 matched attempts per profile')

def run_session(args,directory,cases,manifest):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    manifest['controls']=comparison_controls(opener,args.url)
    manifest['served_model']=manifest['controls']['model']
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    expected={'source_fingerprint':manifest['pins']['source_fingerprint'],'model':manifest['served_model']}
    rows=[]
    # Partition complete matched triplets across separate sessions.
    rows_plan=[row for row in manifest['schedule'] if row['round']%2==args.session-1]
    warmups=[dict(row,warmup=True) for row in schedule(cases[:1],1,args.seed+args.session)]
    by_id={case['id']:case for case in cases}
    review_file=(directory/'quality-records.jsonl').open('x',encoding='utf-8') if args.review_records else nullcontext(None)
    with (directory/'rows.jsonl').open('x',encoding='utf-8') as stream,review_file as quality:
        for item in warmups+rows_plan:
            if pinned_inputs(args.release_id)!=manifest['pins']:raise ValueError('Pinned inputs changed; stop comparison')
            if comparison_controls(opener,args.url)!=manifest['controls']:raise ComparisonChanged('Model or pipeline changed')
            started=time.monotonic()
            review=(lambda value:write_quality(quality,{**item,'session':args.session,**value})) if quality else None
            try:row=measured_probe(args,opener,by_id[item['case']],item['profile'],expected,review)
            except ComparisonChanged:raise
            except Exception:row={'ok':False,'failure':'request_failed'}
            row.update(item,session=args.session)
            stream.write(json.dumps(row)+'\n');stream.flush()
            rows.append(row)
            print(json.dumps({'completed':len(rows),'planned':len(warmups)+len(rows_plan),'ok':row['ok']}),flush=True)
            # Start spacing stays above the existing 12/minute chat ceiling;
            # actual reserved-token budgets may require longer pauses.
            time.sleep(max(0,args.interval-(time.monotonic()-started)))
    write_report(directory,manifest,rows)

def write_quality(stream,record):
    stream.write(json.dumps(record,ensure_ascii=True)+'\n');stream.flush()

def measured_probe(args,opener,case,profile,expected,review=None):
    if not args.telemetry:return probe(opener,args.url,case,profile,expected,review)
    from scripts.execution_telemetry import snapshot,comparison
    started=time.perf_counter();before=snapshot();overhead=time.perf_counter()-started
    row=probe(opener,args.url,case,profile,expected,review)
    started=time.perf_counter();after=snapshot();overhead+=time.perf_counter()-started
    row['telemetry']=comparison(before,after,overhead)
    return row

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--url',default='http://127.0.0.1:8080',type=validate_url)
    parser.add_argument('--session',type=int,choices=(1,2),required=True)
    parser.add_argument('--seed',type=int,default=5900)
    parser.add_argument('--interval',type=float,default=16.)
    parser.add_argument('--run',action='store_true',help='Operate already prepared owner gateway; does not start or activate services')
    parser.add_argument('--combine',nargs=2,metavar=('SESSION_ONE','SESSION_TWO'))
    parser.add_argument('--telemetry',action='store_true',help='Read stock host counters/GPU boundary snapshots; compare logging on/off separately')
    parser.add_argument('--release-id',help='Explicit prepared candidate to measure; never changes active selection; served receipt must match')
    parser.add_argument('--review-records',action='store_true',help='Save completed screened answers/references in owner-local ignored output for rubric review; never ordinary diagnostics')
    args=parser.parse_args()
    if not math.isfinite(args.interval) or args.interval<16:parser.error('Use at least 16-second start spacing; do not change broker quotas')
    directory=output_directory(args.output)
    if directory.exists():parser.error('Output must be new; original receipts are never overwritten')
    if args.combine:
        if args.run:parser.error('Combine is offline')
        manifest,rows=combine_sessions(args.combine)
        directory.mkdir(parents=True)
        write_report(directory,manifest,rows)
        return
    corpus=ROOT/'evals/execution-profiles.json'
    cases=json.loads(corpus.read_text(encoding='utf-8'))['cases']
    manifest={'schema':'larpus.execution-benchmark/v1','session':args.session,'seed':args.seed,
              'pins':pinned_inputs(args.release_id),'workload_sha256':hashlib.sha256(corpus.read_bytes()).hexdigest(),
              'schedule':schedule(cases,5,args.seed),'diagnostic_base':'verified',
              'cache':'uncontrolled-warm-order-balanced','history':'fixed-case','queue':'sequential',
              'telemetry':'boundary snapshots' if args.telemetry else 'not collected','quality':'pending independent rubric review','controls':None,'review_records':args.review_records,
              'activation':'not performed by this command','run':args.run}
    directory.mkdir(parents=True)
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    if args.run:run_session(args,directory,cases,manifest)
    else:print('Manifest only; no requests or service changes.')

if __name__=='__main__':main()
