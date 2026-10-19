"""Owner-only fixed release comparison. Dry-run default; raw receipts stay private."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.performance_metrics import summarize

FOCUSED=(
    {'id':'home-selected','persona':'home-assistant','skill':'home-planning','messages':[{'role':'user','content':'I have 60 minutes tonight for cooking and study. Give a realistic short plan.'}]},
    {'id':'cyber-selected','persona':'it-larp-coach','skill':'it-interview','messages':[{'role':'user','content':'Ask one fictional SOC interview question about validating AI alert triage.'}]},
    {'id':'math-selected','persona':'mathematician','skill':'math-differential-equations','messages':[{'role':'user','content':"Explain the solution of y'=y and how a small initial perturbation evolves. Keep it short."}]})

WORKER="""
import sys,json,time
sys.path.insert(0,sys.argv[1])
from runtime.mcp_client import stream_chat
case=json.loads(sys.argv[2]);started=time.perf_counter();chunks=[]
def chunk(text):chunks.append({'seconds':time.perf_counter()-started,'text':text})
try:
    result=stream_chat(case['persona'],case['messages'],case.get('skill'),chunk)
    ok=result.get('status')==200 and bool(chunks)
    row={'ok':ok,'first_text_seconds':chunks[0]['seconds'] if chunks else None,
         'total_seconds':time.perf_counter()-started,'characters':sum(len(c['text']) for c in chunks),
         'stage_ms':result.get('timing_ms',{}),'unknown_citations':len(result.get('citation_check',{}).get('unknown',[])),'result':result,'chunks':chunks}
    if not ok:row['error']='rejected'
except Exception as exc:
    row={'ok':False,'error':type(exc).__name__,'total_seconds':time.perf_counter()-started,'characters':sum(len(c['text']) for c in chunks),'chunks':chunks}
print(json.dumps(row))
"""

def release_id(value):
    if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{32}',value):
        raise ValueError('Invalid release ID')
    return value

def percentiles(values):
    values=sorted(v for v in values if type(v) in (float,int) and math.isfinite(v) and v>=0)
    return {'n':len(values),'median':statistics.median(values) if values else None,
            'p90':values[math.ceil(len(values)*.9)-1] if values else None,
            'p95':values[math.ceil(len(values)*.95)-1] if values else None}

def summarize_rows(rows):
    result=summarize(rows)
    successful=[r for r in rows if r['phase']=='measured' and r['ok']]
    result['first_text_seconds']=percentiles(r.get('first_text_seconds') for r in successful)
    result['chunk_gap_seconds']=percentiles(b['seconds']-a['seconds'] for r in successful for a,b in zip(r.get('chunks',[]),r.get('chunks',[])[1:]))
    return result

def valid_run(rows,expected,before,after):
    return len(rows)==expected and before==after

def identity(root,cases=None):
    result={}
    for name in ('release.json','deployment.json','skills/registry.json','knowledge/manifest.json','config/mcp-approved.json'):
        result[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
    meta=json.loads((root/'release.json').read_text())
    if meta.get('status')!='prepared':
        raise ValueError('Release is not prepared')
    result['source_fingerprint']=meta['source_fingerprint']
    for name in ('config/model-selection.json','config/cpu-retrieval.json','knowledge/embeddings-manifest.json','knowledge/notes-manifest.json','runtime/native/manifest.json'):
        path=root/name
        result[name]=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    code="""import sys,json,hashlib,importlib.metadata
sys.path.insert(0,sys.argv[1])
from runtime.mcp_client import health
from runtime.security_scan import fingerprint
from runtime.agents import load_personas,messages_for
cases=json.loads(sys.argv[2]);personas=load_personas()
prompts={c['id']:hashlib.sha256(messages_for(personas[c['persona']],c['messages'],c.get('skill'))[0]['content'].encode()).hexdigest() for c in cases}
print(json.dumps({'model':health(),'sdk':{p:importlib.metadata.version(p) for p in ('mcp','mcp-types')},'fingerprint':fingerprint(),'instructions':prompts}))
"""
    observation=subprocess.run([sys.executable,'-c',code,str(root),json.dumps(cases or [])],cwd=root,env=worker_environment(),capture_output=True,text=True,check=True,timeout=60)
    result['runtime']=json.loads(observation.stdout)
    if result['runtime']['fingerprint']!=meta['source_fingerprint']:raise ValueError('Prepared source changed')
    result['workload']=workload(root,meta,result['runtime'])
    model=result['runtime']['model']
    if model.get('switching') or model.get('model_processors',{}).get(model.get('active_model'))!='GPU':
        raise ValueError('Model is not ready on GPU')
    return result

def worker_environment():
    env=os.environ.copy()
    env.update(LARPUS_ISOLATION='wsl-podman',PYTHONUTF8='1',PYTHONIOENCODING='utf-8',OTEL_SDK_DISABLED='true')
    return env

def profile_loader(repeats=10):
    import time
    from runtime.skills import load_skills,selected_prompt
    from runtime.agents import load_personas
    results={}
    persona=load_personas()['home-assistant']
    for name,operation in (('full',load_skills),('selected',lambda:selected_prompt(persona,'home-planning'))):
        trials=[]
        for index in range(repeats+1):
            started=time.perf_counter();operation();elapsed=(time.perf_counter()-started)*1000
            trials.append({'phase':'warmup' if index==0 else 'measured','milliseconds':elapsed})
        results[name]={'trials':trials,'summary_ms':percentiles(t['milliseconds'] for t in trials if t['phase']=='measured')}
    return {'platform':sys.platform,'python':sys.version,'scope':'Standalone validation; not a chat-stage measurement','results':results}

def probe(root,case):
    try:
        result=subprocess.run([sys.executable,'-c',WORKER,str(root),json.dumps(case)],cwd=root,env=worker_environment(),capture_output=True,text=True,timeout=960)
    except KeyboardInterrupt:
        return {'ok':False,'error':'interrupted','characters':0,'partial_output':'unavailable'}
    except subprocess.TimeoutExpired:
        return {'ok':False,'error':'worker_timeout','characters':0,'partial_output':'unavailable'}
    if result.returncode:
        return {'ok':False,'error':'worker_exit'}
    try:
        return json.loads(result.stdout)
    except ValueError:
        return {'ok':False,'error':'worker_protocol'}

def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

def run(args,cases):
    roots={label:ROOT/'data/releases'/identifier for label,identifier in (('A',args.baseline),('B',args.candidate))}
    before={key:identity(root,cases) for key,root in roots.items()}
    require_matched(before)
    directory=ROOT/'data/evals/mcp-skills'/uuid.uuid4().hex
    directory.mkdir(parents=True,exist_ok=False)
    manifest={'baseline':args.baseline,'candidate':args.candidate,'before':before,'cases':cases,
              'repeats':args.repeats,'warmups':args.warmups,'valid':False,
              'answer_review':'pending; apply evals/performance.json rubric to retained answers and original supporting passages'}
    write(directory/'manifest.json',manifest)
    rows=[]
    try:
        for round_number in range(args.warmups+args.repeats):
            for case in cases:
                for label in ('A','B') if round_number%2==0 else ('B','A'):
                    row=probe(roots[label],case)
                    row.update(label=label,case=case['id'],round=round_number,phase='warmup' if round_number<args.warmups else 'measured')
                    rows.append(row)
                    with (directory/'raw.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(row)+'\n')
                    print(json.dumps({key:row.get(key) for key in ('label','case','round','ok','first_text_seconds')}),flush=True)
                    if row.get('error')=='interrupted':
                        manifest['interrupted']=True
                        raise KeyboardInterrupt
    finally:
        manifest['after']=after_identities(roots,cases)
        expected=2*len(cases)*(args.warmups+args.repeats)
        manifest['valid']=valid_run(rows,expected,before,manifest['after']) and not manifest.get('interrupted',False)
        manifest['per_case']=case_summaries(rows,cases,roots)
        write(directory/'manifest.json',manifest)
        print(str(directory),flush=True)
    return 0 if manifest['valid'] else 1

def workload(root,meta,runtime):
    names=[name for name in meta['files'] if name.startswith(('agents/','skills/','knowledge/','config/'))]
    names += [name for name in ('runtime/inference.py','runtime/agents.py','runtime/context.py','runtime/inference_broker.py','runtime/broker_scheduler.py','runtime/native/manifest.json','runtime/native/optimized-manifest.json') if name in meta['files']]
    pins={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in names}
    if any(pins[name]!=meta['files'][name] for name in pins):raise ValueError('Workload payload drift')
    return {'pins':pins,'model':runtime['model'],'sdk':runtime['sdk'],'instructions':runtime['instructions']}

def require_matched(observed):
    if observed['A']['workload']!=observed['B']['workload']:
        raise ValueError('A/B model, corpus, options or selected instruction identities differ')

def after_identities(roots,cases):
    try:
        return {key:identity(root,cases) for key,root in roots.items()}
    except Exception:
        return None


def case_summaries(rows,cases,labels):
    return {case['id']:{label:summarize_rows([r for r in rows if r['case']==case['id'] and r['label']==label]) for label in labels} for case in cases}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',required=True,type=release_id)
    parser.add_argument('--candidate',required=True,type=release_id)
    parser.add_argument('--repeats',type=int,choices=range(1,11),default=6)
    parser.add_argument('--warmups',type=int,choices=range(1,4),default=1)
    parser.add_argument('--cases',choices=('focused','existing8'),default='focused')
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args(argv)
    cases=list(FOCUSED) if args.cases=='focused' else json.loads((ROOT/'evals/performance.json').read_text())['cases']
    if not args.run:
        print(json.dumps({'execute':False,'baseline':args.baseline,'candidate':args.candidate,'cases':cases,'repeats':args.repeats,'warmups':args.warmups}))
        return 0
    return run(args,cases)

if __name__=='__main__':raise SystemExit(main())
