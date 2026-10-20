"""CPU-only isolated runner. JSON events are flushed for owner supervision."""
import copy,ctypes,datetime,hashlib,json,signal,sys,threading,time
from pathlib import Path
import numpy as np
sys.path.insert(0,'/lab')
from assembly_lab_metrics import summarize,qualify
from assembly_lab_guard import apply_strict_guard
sys.path.insert(0,'/lab/native')
from check import library,verify
from runtime.retrieval import Engine

STOP=False
def stop(*_):
 global STOP;STOP=True
signal.signal(signal.SIGTERM,stop)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def event(kind,**value):print(json.dumps({'type':kind,'utc':utc(),**value}),flush=True)

class Native:
 def __init__(self,lib,engine,workers,mode):
  self.lib=lib;self.workers=workers;self.mode=mode;self.lock=threading.Lock()
  self.matrix=engine.vectors if mode==1 else engine.pipeline.native.vectors
  self.handle=lib.lab_create(self.matrix.ctypes.data,*self.matrix.shape,workers,mode)
  if not self.handle:raise RuntimeError('Native persistent pool initialization failed')
  self.backing={'mode':mode,'workers':workers,'matrix_bytes':self.matrix.nbytes,'anonymous_huge_kb':0}
  address=lib.lab_matrix(self.handle);inside=False
  for line in Path('/proc/self/smaps').read_text().splitlines():
   if '-' in line.split()[0]:
    a,b=(int(x,16) for x in line.split()[0].split('-'));inside=a<=address<b
   elif inside and line.startswith('AnonHugePages:'):self.backing['anonymous_huge_kb']=int(line.split()[1]);break
 def close(self):
  with self.lock:
   if self.handle:self.lib.lab_destroy(self.handle);self.handle=None
 def score(self,q):
  if q.dtype!=np.float32 or q.shape!=(self.matrix.shape[1],) or not q.flags.c_contiguous or not np.isfinite(q).all():raise ValueError('Invalid candidate query')
  with self.lock:
   if not self.handle:raise RuntimeError('Closed candidate')
   result=np.empty(len(self.matrix),dtype='float32')
   if self.lib.lab_score(self.handle,q.ctypes.data,result.ctypes.data) or not np.isfinite(result).all():raise RuntimeError('Candidate score failed')
   return result

def main():
 config=json.loads(Path('/lab/config.json').read_text());lib=library(Path('/lab/liblab.so'))
 for relative,expected in config['baseline_pins'].items():
  if hashlib.sha256((Path('/app')/relative).read_bytes()).hexdigest()!=expected:raise RuntimeError('Frozen image baseline pin mismatch: '+relative)
 event('phase-start',phase='native-validation');native_checks=verify(lib);event('phase-end',phase='native-validation',checks=native_checks)
 event('phase-start',phase='engine-initialization');engine=Engine('/app/knowledge')
 baseline=engine.pipeline
 if baseline.native is None:raise RuntimeError('Frozen Assembly baseline unavailable')
 event('phase-end',phase='engine-initialization',shape=engine.vectors.shape)
 candidates={};owned=[]
 for mode in (0,1,2):
  for workers in ((4,8) if mode==2 else (2,4,6,8)):
   native=Native(lib,engine,workers,mode);owned.append(native)
   p=copy.copy(baseline);p.native=native;p.ambiguity_fallbacks=0
   apply_strict_guard(p)
   candidates[f'c-pool-{("half","float","aligned-half")[mode]}-{workers}']=p
 pipelines={'numpy':copy.copy(baseline),'current':baseline,**candidates};pipelines['numpy'].requested='numpy'
 report={'config':config,'shape':list(engine.vectors.shape),'native_checks':native_checks,'candidate_guard':'Same empirical margin; NumPy fallback includes duplicate-row cutoff ties. Frozen current guard unchanged.','current_reference_checks':{'queries':0,'set_mismatches_numpy':0,'examples':[]},'candidate_backing':{name:p.native.backing for name,p in candidates.items()},'selection':{},'correctness':{},'records':[],'phases':[],'neighbors':[],'clock':'UTC wall-clock markers; perf_counter_ns latency','numpy_version':np.__version__}
 def score(name,q):
  p=pipelines[name];result=p.score(q,18)
  if name!='numpy' and p.native is None:raise RuntimeError(name+' disabled its native scorer')
  return result
 def phase_start(name):
  phase={'phase':name,'started_utc':utc()};report['phases'].append(phase);event('phase-start',phase=name);return phase
 def phase_end(phase):phase['finished_utc']=utc();event('phase-end',phase=phase['phase'])
 def quota():
  try:return {k:int(v) for k,v in (x.split() for x in Path('/sys/fs/cgroup/cpu.stat').read_text().splitlines())}
  except OSError:return {}
 try:
  phase=phase_start('candidate-correctness')
  checks=config['random_checks'];valid={name:True for name in candidates};ordered=0
  for index,q in enumerate(np.random.default_rng(590019).normal(size=(checks,engine.vectors.shape[1])).astype('float32')):
   if STOP:break
   q/=np.linalg.norm(q);raw=baseline.native.score(q);reference=engine.vectors@q;guarded=score('current',q)
   np.testing.assert_allclose(raw,reference,atol=2e-6,rtol=2e-5)
   expected=baseline.native._top(reference);actual=baseline.native._top(guarded)
   ordered+=actual!=expected
   current_check=report['current_reference_checks'];current_check['queries']+=1
   if set(actual)!=set(expected):
    current_check['set_mismatches_numpy']+=1
    if len(current_check['examples'])<5:
     differing=sorted(set(actual)^set(expected))
     current_check['examples'].append({'query_index':index,'different_rows':differing,'groups':[int(baseline.groups[x]) for x in differing],'vectors_identical':all(np.array_equal(engine.vectors[differing[0]],engine.vectors[x]) for x in differing)})
   for name,p in candidates.items():
    info=report['correctness'].setdefault(name,{'queries':0,'set_mismatches_numpy':0,'set_mismatches_current':0,'max_abs_error':0.,'exact_current_score_mismatches':0})
    try:
     a=p.native.score(q);out=score(name,q)
     np.testing.assert_allclose(a,reference,atol=2e-6,rtol=2e-5)
     info['exact_current_score_mismatches']+=not np.array_equal(a.view('uint32'),raw.view('uint32'))
     info['set_mismatches_numpy']+=set(baseline.native._top(out))!=set(expected)
     info['set_mismatches_current']+=set(baseline.native._top(out))!=set(actual)
     info['max_abs_error']=max(info['max_abs_error'],float(np.max(np.abs(a-reference))));info['queries']+=1
    except (ValueError,RuntimeError,AssertionError) as exc:info['error']=str(exc)[:200];valid[name]=False
   if index%128==0:event('progress',phase='candidate-correctness',queries=index+1)
  for name,info in report['correctness'].items():
   valid[name]&=info['queries']==checks and not any(info[k] for k in ('set_mismatches_numpy','exact_current_score_mismatches'))
  report['current_ordered_mismatches_numpy']=ordered;phase_end(phase)
  if STOP:raise InterruptedError('Owner sensor supervisor requested stop')
  train=[engine.embedder.encode([q],query=True)[0] for q in config['selection_questions']]
  holdout=[engine.embedder.encode([q],query=True)[0] for q in config['holdout_questions']]
  phase=phase_start('candidate-selection');screen={name:[] for name in candidates if valid[name]}
  if not screen:raise RuntimeError('No candidate passed numerical/reference checks')
  for rep in range(config['screen_rounds']+3):
   names=list(screen);names=names[rep%len(names):]+names[:rep%len(names)]
   for q in train:
    for name in names:
     if STOP:raise InterruptedError('Owner sensor supervisor requested stop')
     time.sleep(.015);start=time.perf_counter_ns();score(name,q);elapsed=(time.perf_counter_ns()-start)/1e6
     if rep>=3:screen[name].append(elapsed)
  report['selection']={name:summarize(v) for name,v in screen.items()}
  selected=min(screen,key=lambda n:report['selection'][n]['p50_ms']);report['selected_candidate']=selected
  event('selection',candidate=selected,screen=report['selection']);phase_end(phase)
  modes=['numpy','current',selected];pressure=np.zeros(128*1024*1024,dtype='uint8');round_number=0
  def compare(block,condition,duration):
   nonlocal round_number
   phase=phase_start(block+'/'+condition);deadline=time.monotonic()+duration;counts={m:0 for m in modes}
   while time.monotonic()<deadline and not STOP:
    ci=round_number%len(holdout);q=holdout[ci]
    order=modes[round_number%3:]+modes[:round_number%3]
    for mode in order:
     if STOP:break
     # Pacing and preparation are explicitly outside guarded-score latency.
     time.sleep(config['pace_seconds']);before=quota();prep=time.perf_counter_ns()
     if condition=='warm':score(mode,q)
     elif condition=='pressure':pressure[::64]+=np.uint8(1)
     elif condition=='after-embedding':engine.embedder.encode([config['holdout_questions'][ci]],query=True)
     start=time.perf_counter_ns();result=score(mode,q);end=time.perf_counter_ns();after=quota();counts[mode]+=1
     if counts[mode]>3:
      report['records'].append({'block':block,'condition':condition,'mode':mode,'case':ci,'started_utc':utc(),'score_ms':(end-start)/1e6,'prepare_ms':(start-prep)/1e6,'last_used':pipelines[mode].last_used,'throttled_periods':after.get('nr_throttled',0)-before.get('nr_throttled',0),'throttled_usec':after.get('throttled_usec',0)-before.get('throttled_usec',0)})
    round_number+=1
   phase_end(phase)
  phase=phase_start('settle-idle');deadline=time.monotonic()+config['settle_seconds']
  while time.monotonic()<deadline and not STOP:time.sleep(.2)
  phase_end(phase)
  for block,duration in [('early',config['comparison_seconds']),('warmed-repeat',config['repeat_seconds'])]:
   for condition in ('warm','pressure','after-embedding'):
    if STOP:break
    compare(block,condition,duration/3)
  if STOP:raise InterruptedError('Owner sensor supervisor requested stop')
  phase=phase_start('text-to-references')
  for rep in range(15 if not config['smoke'] else 3):
   for ci,text in enumerate(config['holdout_questions']):
    refs={}
    order=modes[rep%3:]+modes[:rep%3]
    for mode in order:
     engine.pipeline=pipelines[mode];start=time.perf_counter_ns();refs[mode]=engine.neighbors(text,18);elapsed=(time.perf_counter_ns()-start)/1e6
     if rep:report['neighbors'].append({'mode':mode,'case':ci,'ms':elapsed})
    if set(refs[selected])!=set(refs['numpy']):raise RuntimeError('Held-out candidate Engine.neighbors reference sets differ from NumPy')
    if set(refs['current'])!=set(refs['numpy']):report.setdefault('current_neighbors_mismatches',[]).append({'rep':rep,'case':ci})
  phase_end(phase);report['completed']=True
 except Exception as exc:report['completed']=False;report['error']=type(exc).__name__+': '+str(exc)[:500]
 finally:
  for obj in owned:obj.close()
  if baseline.native is not None:baseline.native.close()
 report['summary']={}
 for row in report['records']:
  key=row['block']+'/'+row['condition'];report['summary'].setdefault(key,{})
 for key in report['summary']:
  for mode in ['numpy','current',report.get('selected_candidate')]:
   values=[r['score_ms'] for r in report['records'] if r['block']+'/'+r['condition']==key and r['mode']==mode]
   if values:report['summary'][key][mode]=summarize(values)
 selected=report.get('selected_candidate');candidate={k:v[selected] for k,v in report['summary'].items() if selected in v};current={k:v['current'] for k,v in report['summary'].items() if 'current' in v}
 correct=report.get('completed',False) and selected in report['correctness'] and valid.get(selected,False)
 report['qualification']=qualify(candidate,current,correct)
 fetch={mode:summarize([r['ms'] for r in report['neighbors'] if r['mode']==mode]) for mode in ('current',selected) if any(r['mode']==mode for r in report['neighbors'])}
 report['fetch_qualification']=qualify({'text-to-references':fetch[selected]} if selected in fetch else {},{'text-to-references':fetch['current']} if 'current' in fetch else {},correct)
 if config['smoke']:report['qualification']['passed']=False;report['qualification']['reasons'].append('Smoke run is not acceptance evidence')
 if config['smoke']:report['fetch_qualification']['passed']=False;report['fetch_qualification']['reasons'].append('Smoke run is not acceptance evidence')
 event('result',report=report)

if __name__=='__main__':main()
