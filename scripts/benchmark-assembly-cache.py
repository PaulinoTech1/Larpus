"""Owner-only paced/cache-pressure scorer comparison. Never changes the station."""
import argparse,hashlib,json,re,runpy,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

SOURCE='''
import json,time,copy
from pathlib import Path
import numpy as np
from runtime.retrieval import Engine
engine=Engine('/app/knowledge');new=engine.pipeline.native;assert new is not None
namespace={};exec(OLD_CODE,namespace)
old=object.__new__(namespace['NativeScorer']);old.__dict__=dict(new.__dict__)
previous=copy.copy(engine.pipeline);previous.native=old
modes=['numpy','deployed','cached-dispatch']
def call(mode,q):
 if mode=='numpy':return engine.vectors@q
 return (previous if mode=='deployed' else engine.pipeline).score(q,18)
cases=CASES
queries=[engine.embedder.encode([c['messages'][-1]['content']],query=True)[0] for c in cases]
checks=0;max_abs_error=0
for q in np.random.default_rng(5902).normal(size=(1024,engine.vectors.shape[1])).astype('float32'):
 q/=np.linalg.norm(q);a=call('cached-dispatch',q);saved=a.copy();b=call('deployed',q)
 np.testing.assert_array_equal(a,b);np.testing.assert_array_equal(a,saved)
 reference=engine.vectors@q;np.testing.assert_allclose(a,reference,atol=2e-6,rtol=2e-5)
 assert set(new._top(a))==set(new._top(reference));checks+=1
 max_abs_error=max(max_abs_error,float(np.max(np.abs(a-reference))))
pressure=np.empty(128*1024*1024,dtype='uint8');pressure.fill(0)
records=[]
def quota():
 try:return {k:int(v) for k,v in (line.split() for line in Path('/sys/fs/cgroup/cpu.stat').read_text().splitlines())}
 except OSError:return {}
for condition,repetitions in (('stress-embedding',20),('warm',16),('pressure',12),('after-embedding',20),('after-reranking',6)):
 for ci,(case,q) in enumerate(zip(cases,queries)):
  for rep in range(repetitions+2):
   order=modes[(rep+ci)%3:]+modes[:(rep+ci)%3]
   for mode in order:
    if condition!='stress-embedding':time.sleep(.1)
    quota_before=quota()
    prep=time.perf_counter_ns()
    if condition=='warm':call(mode,q)
    elif condition=='pressure':pressure[::64]+=np.uint8(1)
    elif condition in ('after-embedding','stress-embedding'):engine.embedder.encode([case['messages'][-1]['content']],query=True)
    else:engine.rerank(case['messages'][-1]['content'],['A norm measures vector magnitude. Verify the original event before escalating an alert.']*4)
    start=time.perf_counter_ns();scores=call(mode,q);finish=time.perf_counter_ns()
    quota_after=quota()
    if rep>=2:records.append({'case':case['id'],'condition':condition,'mode':mode,'rep':rep-2,'prepare_ms':(start-prep)/1e6,'score_ms':(finish-start)/1e6,'total_ms':(finish-prep)/1e6,'throttled_periods':quota_after.get('nr_throttled',0)-quota_before.get('nr_throttled',0),'throttled_usec':quota_after.get('throttled_usec',0)-quota_before.get('throttled_usec',0)})
  print(json.dumps({'condition':condition,'case':case['id']}),flush=True)
summary={}
for condition in ('stress-embedding','warm','pressure','after-embedding','after-reranking'):
 summary[condition]={}
 for mode in modes:
  rows=[r for r in records if r['condition']==condition and r['mode']==mode]
  summary[condition][mode]={field:{'median':float(np.median([r[field] for r in rows])),'p95':float(np.percentile([r[field] for r in rows],95))} for field in ('prepare_ms','score_ms','total_ms')}
  summary[condition][mode]['quota_events']=sum(r['throttled_periods'] for r in rows)
print('RESULT '+json.dumps({'summary':summary,'records':records,'random_queries':checks,'bitwise_equal_to_deployed':True,'max_abs_error_numpy':max_abs_error,'cpu_quota':Path('/sys/fs/cgroup/cpu.max').read_text().strip(),'quota_counters_available':bool(quota()),'cache_counters_collected':False,'query_ids':[c['id'] for c in cases],'pressure_bytes':pressure.nbytes,'scope':'Eight fixtures, rotated interleaving, two excluded conditioning rounds. Non-stress conditions have 100 ms idle before preparation, outside all timers, to distinguish paced calls from saturated throughput. CPU quota counters cover preparation plus scoring; pressure is a proxy, no hardware cache counters. Same matrix, kernel, pool, ONNX settings and quota for both scorers.'}),flush=True)
'''

def baseline_source(baseline):
 if not re.fullmatch('[a-f0-9]{32}',baseline):raise ValueError('Invalid baseline release ID')
 frozen=ROOT/'data/releases'/baseline
 if frozen.is_symlink() or frozen.resolve()!=(ROOT/'data/releases').resolve()/baseline:raise ValueError('Redirected baseline')
 meta=json.loads((frozen/'release.json').read_text())
 if meta.get('status')!='prepared':raise ValueError('Baseline must have completed preparation')
 old_path=frozen/'runtime/native_scoring.py';old_code=old_path.read_text(encoding='utf-8')
 digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
 if digest(old_path)!=meta['files']['runtime/native_scoring.py']:raise ValueError('Frozen baseline changed')
 kernel='runtime/native/liblarpus_score.so'
 if digest(ROOT/kernel)!=meta['files'][kernel]:raise ValueError('Wrapper comparison requires an unchanged native kernel')
 return old_code,meta,digest

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--run',action='store_true')
 parser.add_argument('--baseline',help='Prepared frozen release ID; defaults to active')
 args=parser.parse_args()
 if not args.run:
  print('Plan: isolated eight-CPU comparison of NumPy, frozen scorer, and checkout scorer; warm, pressure, embedding and reranking conditions with paced and saturation samples. Use --run.');return
 active=json.loads((ROOT/'data/releases/active.json').read_text())['id'];baseline=args.baseline or active
 old_code,meta,digest=baseline_source(baseline)
 kernel='runtime/native/liblarpus_score.so'
 candidate=digest(ROOT/'runtime/native_scoring.py')
 scope=runpy.run_path(str(ROOT/'scripts/benchmark-assembly.py'));execute=scope['execute']
 directory=ROOT/'data/assembly-linux-build'/('cache-final-'+uuid.uuid4().hex);directory.mkdir()
 linux='/home/larpus/native-assembly-build/'+directory.name;scope['copy_runtime'](directory,linux)
 if digest(ROOT/'runtime/native_scoring.py')!=candidate:raise ValueError('Candidate changed during copy')
 cases=json.loads((ROOT/'evals/performance.json').read_text())['cases']
 source=SOURCE.replace('OLD_CODE',repr(old_code)).replace('cases=CASES','cases='+repr(cases))
 (directory/'runner.py').write_text(source,encoding='utf-8')
 profile=json.loads((ROOT/'data/releases'/active/'deployment.json').read_text())
 command=['podman','run','--rm','-i','--pull=never','--network=none','--read-only','--read-only-tmpfs=false','--user=1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=128','--memory=12g','--cpus=8','--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=128m','--volume='+linux+'/runtime:/app/runtime:ro','--env=HOME=/tmp','--env=LARPUS_RETRIEVAL_WORKER=local','--env=TOKENIZERS_PARALLELISM=false']
 for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):command.append('--env='+key+'=8')
 command+=['--entrypoint=python',profile['agent_image'],'-']
 try:result=execute(*command,input=source.encode())
 except Exception as exc:
  (directory/'stderr.txt').write_bytes(getattr(exc,'stderr',b'') or b'');raise
 (directory/'stdout.txt').write_bytes(result.stdout);(directory/'stderr.txt').write_bytes(result.stderr)
 report=json.loads(next(line[7:] for line in result.stdout.decode().splitlines() if line.startswith('RESULT ')))
 report.update(active_release=active,baseline_release=baseline,image=profile['agent_image'],candidate_sha256=candidate,baseline_sha256=meta['files']['runtime/native_scoring.py'],kernel_sha256=meta['files'][kernel])
 (directory/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(str(directory/'report.json'))
 print(json.dumps({c:{m:v['score_ms'] for m,v in modes.items()} for c,modes in report['summary'].items()}))

if __name__=='__main__':main()
