"""Correctness and warm-scoring check for the selectable Assembly optimized module.

Runs in the frozen agent image with the checkout runtime mounted over it.
Does not start the gateway, model, or voice. Artifacts stay under
data/assembly-linux-build/optimized-verify/ on E:.
"""
import hashlib,io,json,math,statistics,subprocess,sys,tarfile,threading,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HOLDOUT=['How does a norm bound the error between two approximate solutions?',
 'What evidence should an analyst preserve before rejecting an AI-generated incident summary?',
 'Why can a working set that crosses cache capacity change latency without changing instruction count?',
 'How should a penetration tester scope and verify an automated finding?',
 'Explain the difference between cryptographic diffusion and stability of a differential equation.',
 'What tests reveal whether retrieval optimizations change the selected source references?',
 'How do numerical precision and nearly equal similarity scores affect ranking?',
 'How should an organization document model limitations and retain human decision authority?']
MODES=('numpy','assembly','assembly-optimized')

def summarize(values):
 values=sorted(float(x) for x in values)
 if not values or any(not math.isfinite(x) or x<0 for x in values):raise ValueError('Invalid latency samples')
 def percentile(p):
  x=(len(values)-1)*p;i=int(x)
  return values[i]+(values[min(i+1,len(values)-1)]-values[i])*(x-i)
 return {'n':len(values),'p50_ms':statistics.median(values),'p95_ms':percentile(.95),'p99_ms':percentile(.99),'max_ms':max(values),'at_or_below_1ms_fraction':sum(x<=1 for x in values)/len(values)}

def _rss():
 return int(next(line.split()[1] for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('VmRSS:')))

def _correctness(pipeline,optimized,report,event):
 import numpy as np
 def tops(scores):return set(pipeline.native._top(scores))
 for index,query in enumerate(np.random.default_rng(590019).normal(size=(1024,pipeline.vectors.shape[1])).astype(np.float32)):
  query/=np.linalg.norm(query);raw=pipeline.native.score(query);opt=optimized.score(query);reference=pipeline.vectors@query
  report['bit_mismatches']+=not np.array_equal(opt.view(np.uint32),raw.view(np.uint32))
  report['max_abs_error']=max(report['max_abs_error'],float(np.max(np.abs(opt-reference))))
  np.testing.assert_allclose(opt,reference,atol=2e-6,rtol=2e-5)
  expected=tops(reference);pipeline.select('assembly-optimized');guarded=tops(pipeline.score(query,18))
  pipeline.select('assembly');original=tops(pipeline.score(query,18))
  report['optimized_set_mismatches']+=guarded!=expected;report['original_set_mismatches']+=original!=expected;report['queries']+=1
  if (guarded!=expected or original!=expected) and len(report['examples'])<5:
   report['examples'].append({'query_index':index,'optimized_matches_numpy':guarded==expected,'original_matches_numpy':original==expected,'rows':sorted(expected^guarded^original)[:8]})
  if index%128==0:event('progress',phase='correctness',queries=index+1)

def _neighbor_sets(engine,pipeline,report):
 for text in HOLDOUT:
  sets={}
  for mode in MODES:pipeline.select(mode);sets[mode]=engine.neighbors(text,18)
  report['neighbors'].append({'optimized_matches_numpy':sets['assembly-optimized']==sets['numpy'],'original_matches_numpy':sets['assembly']==sets['numpy']})
 report['neighbor_optimized_mismatches']=sum(not row['optimized_matches_numpy'] for row in report['neighbors'])
 report['neighbor_original_mismatches']=sum(not row['original_matches_numpy'] for row in report['neighbors'])

def inside():
 import os
 os.environ['LARPUS_RETRIEVAL_WORKER']='local';os.environ['TOKENIZERS_PARALLELISM']='false'
 sys.path.insert(0,'/app')
 import numpy as np
 from runtime.knowledge import DIRECTORY
 from runtime.retrieval import Engine
 def event(kind,**value):print(json.dumps({'type':kind,**value}),flush=True)
 engine=Engine(DIRECTORY);pipeline=engine.pipeline;status=pipeline.status();optimized=pipeline.optimized
 if status['active_id']!='assembly-optimized' or optimized is None or pipeline.native is None:
  event('result',report={'passed':False,'status':status,'error':'Assembly optimized did not stay loaded'});return 2
 event('loaded',shape=list(engine.vectors.shape),matrix_bytes=optimized.matrix_bytes,reserved_bytes=optimized.reserved_bytes,huge_bytes=optimized.huge_bytes,rss_kb=_rss())
 report={'passed':False,'shape':list(engine.vectors.shape),'matrix_bytes':optimized.matrix_bytes,'reserved_bytes':optimized.reserved_bytes,'huge_bytes':optimized.huge_bytes,'queries':0,'bit_mismatches':0,'optimized_set_mismatches':0,'original_set_mismatches':0,'max_abs_error':0.0,'examples':[],'neighbors':[],'summary':{}}
 _correctness(pipeline,optimized,report,event)
 holdout=[np.ascontiguousarray(engine.embedder.encode([text],query=True)[0],dtype=np.float32) for text in HOLDOUT]
 def block(name,count):
  event('progress',phase=name,samples=0)
  for rep in range(5):
   for mode in MODES[rep%3:]+MODES[:rep%3]:
    pipeline.select(mode);time.sleep(.1);pipeline.score(holdout[rep%len(holdout)],18)
    if pipeline._backend(mode) is None and mode!='numpy':raise RuntimeError(mode+' disabled during warmup')
  samples={mode:[] for mode in MODES};before=pipeline.ambiguity_fallbacks
  for rep in range(count):
   query=holdout[rep%len(holdout)]
   for mode in MODES[rep%3:]+MODES[:rep%3]:
    pipeline.select(mode);time.sleep(.1);started=time.perf_counter_ns();pipeline.score(query,18);elapsed=(time.perf_counter_ns()-started)/1e6
    if pipeline._backend(mode) is None and mode!='numpy':raise RuntimeError(mode+' disabled during measurement')
    samples[mode].append(elapsed)
  report['summary'][name]={mode:summarize(values) for mode,values in samples.items()}
  report['summary'][name]['ambiguity_fallbacks']=pipeline.ambiguity_fallbacks-before
  numpy_p50=report['summary'][name]['numpy']['p50_ms'];opt_p50=report['summary'][name]['assembly-optimized']['p50_ms']
  report['summary'][name]['optimized_faster_than_numpy']=0 if numpy_p50==0 else (numpy_p50-opt_p50)/numpy_p50
 block('early-warm',300);time.sleep(60);block('repeat-warm',300);_neighbor_sets(engine,pipeline,report)
 report['passed']=report['queries']==1024 and not report['bit_mismatches'] and not report['optimized_set_mismatches'] and not report['neighbor_optimized_mismatches'] and optimized.huge_bytes>=optimized.reserved_bytes
 pipeline.close();event('result',report=report);return 0 if report['passed'] else 2

def _execute(*cmd,input=None,timeout=180):
 result=subprocess.run(['wsl.exe','-d','Larpus','-u','larpus','--exec',*cmd],input=input,capture_output=True,timeout=timeout)
 if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-2000:])
 return result.stdout

def _report(directory,report):
 lines=['# Assembly optimized module check','',f"Passed: **{report.get('passed')}**.",'',f"Matrix payload {report.get('matrix_bytes')} bytes; aligned reservation {report.get('reserved_bytes')} bytes; anonymous huge pages {report.get('huge_bytes')} bytes.",'',f"Random queries {report.get('queries')}. Bit mismatches versus Assembly original: {report.get('bit_mismatches')}. Optimized reference-set mismatches versus NumPy: {report.get('optimized_set_mismatches')}. Original mismatches versus NumPy: {report.get('original_set_mismatches')}. Maximum absolute score error {report.get('max_abs_error')}.",'','| Block | Backend | n | p50 ms | p95 ms | p99 ms | faster than NumPy |','|---|---|---:|---:|---:|---:|---:|']
 for name,block in report.get('summary',{}).items():
  for mode in MODES:
   row=block[mode];faster='' if mode=='numpy' else f"{(block['numpy']['p50_ms']-row['p50_ms'])/block['numpy']['p50_ms']:.1%}"
   lines.append(f"| {name} | {mode} | {row['n']} | {row['p50_ms']:.3f} | {row['p95_ms']:.3f} | {row['p99_ms']:.3f} | {faster} |")
  lines.append(f"| {name} | ambiguity fallbacks | {block['ambiguity_fallbacks']} |  |  |  |  |")
 lines+=['',f"Held-out neighbor mismatches versus NumPy: optimized {report.get('neighbor_optimized_mismatches')}, original {report.get('neighbor_original_mismatches')}.",'','Scoring excludes the 100 ms pace, five warmup rounds, and query embedding. This is guarded full-index scoring, not chat latency. The station was not started.','']
 (directory/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')

def _station():
 sys.path.insert(0,str(ROOT))
 from scripts.assembly_lab import e_path,registered_on_e
 from scripts.releases import read,running
 if os_drive_rejected(ROOT):raise SystemExit('Checkout must resolve to E:')
 e_path(ROOT);active=read(ROOT/'data/releases/active.json')
 if running(active):raise SystemExit('Station is running; refusing to start a scoring load')
 if json.loads(_podman('ps','--format','json')):raise SystemExit('Containers are running; refusing to interfere')
 profile=read(ROOT/'data/releases'/active['id']/'deployment.json');image=profile['agent_image']
 seen=json.loads(_podman('image','inspect',image))[0]['Id'].removeprefix('sha256:')
 if seen!=image.removeprefix('sha256:'):raise SystemExit('Frozen image identity mismatch')
 return registered_on_e(),active,image

def _podman(*args):return _execute('/usr/bin/env','XDG_RUNTIME_DIR=/run/user/1000','/usr/bin/podman',*args)

def _pack(linux):
 payload=io.BytesIO()
 with tarfile.open(fileobj=payload,mode='w') as archive:
  for path in (ROOT/'runtime').rglob('*'):
   if path.is_file() and '__pycache__' not in path.parts and path.suffix!='.pyc':archive.add(path,arcname='runtime/'+path.relative_to(ROOT/'runtime').as_posix())
  archive.add(Path(__file__),arcname='verify_optimized_pipeline.py')
 _execute('/bin/tar','-xf','-', '-C',linux,input=payload.getvalue(),timeout=180);_execute('/bin/chmod','-R','a+rX',linux)
 digest=_execute('/usr/bin/sha256sum',linux+'/runtime/native/liblarpus_pool.so').decode().split()[0]
 if digest!=json.loads((ROOT/'runtime/native/optimized-manifest.json').read_text(encoding='utf-8'))['sha256']:raise SystemExit('Copied pool library does not match its pin')
 return digest

def owner():
 disk,active,image=_station()
 directory=e_path_directory();linux='/home/larpus/native-assembly-build/optimized-verify-'+directory.name;name='larpus-opt-'+directory.name
 _execute('/bin/mkdir','-p',linux);digest=_pack(linux)
 command=['wsl.exe','-d','Larpus','-u','larpus','--exec','/usr/bin/env','XDG_RUNTIME_DIR=/run/user/1000','/usr/bin/podman','run','--rm','-i','--name',name,'--pull=never','--network=none','--read-only','--read-only-tmpfs=false','--user=1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=128','--memory=12g','--cpus=8','--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=128m','--volume='+linux+':/opt/verify:ro','--volume='+linux+'/runtime:/app/runtime:ro','--workdir=/app','--env=HOME=/tmp','--env=PYTHONDONTWRITEBYTECODE=1','--env=LARPUS_RETRIEVAL_WORKER=local','--env=TOKENIZERS_PARALLELISM=false','--env=OMP_NUM_THREADS=8','--env=OPENBLAS_NUM_THREADS=8','--env=MKL_NUM_THREADS=8','--entrypoint=python',image,'-u','/opt/verify/verify_optimized_pipeline.py','--inside']
 (directory/'manifest.json').write_text(json.dumps({'release':active['id'],'image':image,'wsl_disk':disk,'library_sha256':digest,'production_started':False,'command':command},indent=2),encoding='utf-8')
 print('Run artifacts: '+str(directory),flush=True);captured=[]
 try:
  with (directory/'stdout.jsonl').open('wb') as stdout,(directory/'stderr.txt').open('wb') as stderr:
   process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=stderr);_follow(process,name,captured,stdout)
  _finish(directory,process,captured)
 finally:
  from scripts.releases import read,running
  if running(read(ROOT/'data/releases/active.json')):print('WARNING: gateway became running',flush=True)

def _follow(process,name,captured,stdout):
 def relay():
  for line in process.stdout:stdout.write(line);stdout.flush();captured.append(line)
 relay_thread=threading.Thread(target=relay,daemon=True);relay_thread.start();deadline=time.monotonic()+900;shown=0
 while process.poll() is None:
  if time.monotonic()>deadline:_podman('stop','--time','5',name);raise TimeoutError('Optimized verification exceeded 15 minutes')
  for raw in captured[shown:]:
   obj=json.loads(raw)
   if obj.get('type')=='progress':print(obj['phase'],obj.get('queries',obj.get('samples','')),flush=True)
   elif obj.get('type')=='loaded':print('loaded',obj['huge_bytes'],'huge bytes',flush=True)
  shown=len(captured);time.sleep(2)
 process.wait(timeout=30);relay_thread.join(timeout=30)

def _finish(directory,process,captured):
 report=None
 for raw in captured:
  obj=json.loads(raw)
  if obj.get('type')=='result':report=obj['report']
 if process.returncode not in (0,2) or not report:raise RuntimeError('Verifier exited '+str(process.returncode)+'; see stderr.txt')
 (directory/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');_report(directory,report)
 print(json.dumps({'report':str(directory/'REPORT.md'),'passed':report['passed'],'repeat_faster':report['summary']['repeat-warm']['optimized_faster_than_numpy']}),flush=True)
 if not report['passed']:raise SystemExit(2)

def e_path_directory():
 sys.path.insert(0,str(ROOT))
 from scripts.assembly_lab import e_path
 directory=e_path(ROOT/'data/assembly-linux-build/optimized-verify'/uuid.uuid4().hex);directory.mkdir(parents=True);return directory

def os_drive_rejected(path):return Path(path).resolve().drive.upper()!='E:'

if __name__=='__main__':raise SystemExit(inside() if '--inside' in sys.argv else owner())
