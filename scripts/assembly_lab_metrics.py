"""Stock-envelope experiment statistics; no runtime/model imports."""
import datetime,math,statistics

def summarize(values):
 values=sorted(float(x) for x in values)
 if not values or any(not math.isfinite(x) or x<0 for x in values):raise ValueError('Invalid latency samples')
 def percentile(p):
  x=(len(values)-1)*p;i=int(x)
  return values[i]+(values[min(i+1,len(values)-1)]-values[i])*(x-i)
 return {'n':len(values),'p50_ms':statistics.median(values),'p95_ms':percentile(.95),'p99_ms':percentile(.99),'max_ms':max(values),'at_or_below_1ms_fraction':sum(x<=1 for x in values)/len(values)}

def qualify(candidate,baseline,correct):
 reasons=[]
 if not correct:reasons.append('Correctness checks failed or incomplete')
 if not candidate or set(candidate)!=set(baseline):reasons.append('Missing comparison conditions')
 for condition,c in candidate.items():
  b=baseline.get(condition)
  if c['n']<100:reasons.append(condition+': fewer than 100 samples')
  if c['p95_ms']>1 or c['at_or_below_1ms_fraction']<.95:reasons.append(condition+': repeated 1 ms target missed')
  if b and (c['p50_ms']>b['p50_ms']*.9 or c['p95_ms']>b['p95_ms']):reasons.append(condition+': insufficient improvement over current Assembly')
 return {'passed':not reasons,'reasons':reasons,'criterion':'Each condition: >=100 samples, p95 <=1 ms, >=95% at/below 1 ms, >=10% median improvement, no p95 regression, correctness required.'}

def correlate(samples,phases):
 result=[]
 for phase in phases:
  if not phase.get('finished_utc'):continue
  start=datetime.datetime.fromisoformat(phase['started_utc']);end=datetime.datetime.fromisoformat(phase['finished_utc'])
  selected=[s for s in samples if start<=datetime.datetime.fromisoformat(s['utc'])<end]
  values={};flags={}
  for sample in selected:
   for key,cell in sample['values'].items():
    if not any(x in key for x in ('CPU','Effective Clock','Thermal','Physical Memory','Page File','FCLK','UCLK','Memory Clock','DRAM')):continue
    try:v=float(cell)
    except ValueError:
     if cell in ('Yes','No'):flags.setdefault(key,{}).setdefault(cell,0);flags[key][cell]+=1
     continue
    if math.isfinite(v):values.setdefault(key,[]).append(v)
  sensors={k:{'min':min(v),'median':statistics.median(v),'max':max(v)} for k,v in values.items()}
  result.append({'phase':phase['phase'],'samples':len(selected),'sensors':sensors,'flags':flags})
 return result
