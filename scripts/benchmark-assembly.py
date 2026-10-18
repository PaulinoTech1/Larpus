"""Owner-only isolated Linux scoring comparison; never changes station selection."""
import argparse,json,subprocess,sys,tarfile,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from runtime.isolation import wsl_command
SOURCE='''
import json,time,statistics,sqlite3
import numpy as np
from runtime.retrieval import Engine
engine=Engine('/app/knowledge')
engine.pipeline.select('assembly')
if engine.pipeline.status()['active_id']!='assembly':
 from runtime.native_scoring import NativeScorer
 NativeScorer(engine.vectors)
 raise RuntimeError(engine.pipeline.status())
import ctypes
kernel=engine.pipeline.native.function;kernel_checks=0
for dimension in (1,7,8,31,32,33,383,384,385,768):
 for rows in (1,3,17):
  rng=np.random.default_rng(dimension+rows)
  matrix=rng.normal(size=(rows,dimension)).astype('float16')
  q=rng.normal(size=dimension).astype('float32');q/=np.linalg.norm(q)
  output=np.full(rows+2,777,dtype='float32')
  assert kernel(matrix.ctypes.data,q.ctypes.data,output.ctypes.data+4,rows,dimension)==0
  np.testing.assert_allclose(output[1:-1],matrix.astype('float32')@q,atol=2e-6,rtol=2e-5)
  assert output[0]==777 and output[-1]==777;kernel_checks+=1
assert kernel(None,None,None,0,384)==0
assert kernel(None,None,None,1,384)==-1
cases=CASES
observations=[]
for case in cases:
 question=case['messages'][-1]['content'];q=engine.embedder.encode([question],query=True)[0]
 baseline=engine.vectors@q;actual=engine.pipeline.score(q)
 np.testing.assert_allclose(actual,baseline,atol=2e-6,rtol=2e-5)
 assert set(engine.pipeline.native._top(actual))==set(engine.pipeline.native._top(baseline))
 samples={key:[] for key in ('numpy','assembly')}
 for rep in range(65):
  for mode in (('numpy','assembly') if rep%2 else ('assembly','numpy')):
   engine.pipeline.select(mode);start=time.perf_counter_ns();engine.pipeline.score(q);elapsed=(time.perf_counter_ns()-start)/1e6
   if rep>=5:samples[mode].append(elapsed)
 observations.append({'case':case['id'],'score_ms':samples,'top18_set_equal':True})
 print(json.dumps({'progress':case['id']}),flush=True)
random_checks=0;ordered_mismatches=0;max_abs_error=0
for q in np.random.default_rng(5901).normal(size=(1024,engine.vectors.shape[1])).astype('float32'):
 q/=np.linalg.norm(q);engine.pipeline.select('assembly');actual=engine.pipeline.score(q);reference=engine.vectors@q
 np.testing.assert_allclose(actual,reference,atol=2e-6,rtol=2e-5)
 ordered_mismatches+=engine.pipeline.native._top(actual)!=engine.pipeline.native._top(reference)
 max_abs_error=max(max_abs_error,float(np.max(np.abs(actual-reference))))
 assert set(engine.pipeline.native._top(actual))==set(engine.pipeline.native._top(reference));random_checks+=1
neighbors={mode:[] for mode in ('numpy','assembly')}
for rep in range(4):
 for case in cases:
  ids={}
  for mode in (('numpy','assembly') if rep%2 else ('assembly','numpy')):
   engine.pipeline.select(mode);start=time.perf_counter();ids[mode]=engine.neighbors(case['messages'][-1]['content'],18)
   if rep:neighbors[mode].append((time.perf_counter()-start)*1000)
  assert set(ids['numpy'])==set(ids['assembly'])
result={'ordering_policy':'near-tie reordering allowed; empirical 2e-6 norm-scaled cutoff guard','kernel_checks':kernel_checks,'ordered_mismatches':ordered_mismatches,'max_abs_error':max_abs_error,'shape':engine.vectors.shape,'numpy':np.__version__,'threads':8,'native_workers':4,'random_checks':random_checks,'observations':observations,'neighbors_ms':neighbors,'pipeline':engine.pipeline.status()}
print('RESULT '+json.dumps(result),flush=True)
'''

def execute(*args,**kwargs):
 return subprocess.run(wsl_command(*args),capture_output=True,check=True,timeout=600,**kwargs)

def copy_runtime(directory,linux):
 execute('/bin/mkdir','-p',linux)
 archive=directory/'runtime.tar'
 with tarfile.open(archive,'w') as tar:
  for path in sorted((ROOT/'runtime').rglob('*')):
   if not path.is_file() or '__pycache__' in path.parts:continue
   if path.is_symlink():raise ValueError('Redirected runtime source')
   tar.add(path,arcname=path.relative_to(ROOT).as_posix())
 with archive.open('rb') as stream:execute('/bin/tar','-xf','-','-C',linux,stdin=stream)

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true');args=parser.parse_args()
 if not args.run:print('Plan: separate network-disabled CPU container, four assembly workers vs NumPy, active frozen corpus. Use --run.');return
 active=json.loads((ROOT/'data/releases/active.json').read_text())['id'];profile=json.loads((ROOT/'data/releases'/active/'deployment.json').read_text())
 directory=ROOT/'data/assembly-linux-build'/uuid.uuid4().hex;directory.mkdir(parents=True)
 linux='/home/larpus/native-assembly-build/validation-'+directory.name
 copy_runtime(directory,linux)
 source=SOURCE.replace('cases=CASES','cases='+repr(json.loads((ROOT/'evals/performance.json').read_text())['cases']))
 command=['podman','run','--rm','-i','--pull=never','--network=none','--read-only','--read-only-tmpfs=false','--user=1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=128','--memory=12g','--cpus=8','--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=128m','--volume='+linux+'/runtime:/app/runtime:ro','--env=HOME=/tmp','--env=LARPUS_RETRIEVAL_WORKER=local','--env=TOKENIZERS_PARALLELISM=false']
 for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):command.append('--env='+key+'=8')
 command+=['--entrypoint=python',profile['agent_image'],'-']
 try:result=execute(*command,input=source.encode())
 except subprocess.CalledProcessError as exc:
  (directory/'stderr.txt').write_bytes(exc.stderr)
  raise RuntimeError(exc.stderr.decode(errors='replace')[-3000:]) from None
 (directory/'stdout.txt').write_bytes(result.stdout);(directory/'stderr.txt').write_bytes(result.stderr)
 line=next(line for line in result.stdout.decode().splitlines() if line.startswith('RESULT '))
 receipt=json.loads(line[7:]);receipt.update(release=active,image=profile['agent_image'])
 (directory/'report.json').write_text(json.dumps(receipt,indent=2));print(str(directory/'report.json'))
 import statistics
 print(json.dumps({'median_score_ms':{key:statistics.median(statistics.median(o['score_ms'][key]) for o in receipt['observations']) for key in ('numpy','assembly')},'median_neighbors_ms':{key:statistics.median(values) for key,values in receipt['neighbors_ms'].items()}}))

if __name__=='__main__':main()
