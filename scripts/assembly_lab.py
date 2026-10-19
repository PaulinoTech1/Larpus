"""Owner-only E: stock-envelope lab. No activation, model start, tuning or pulls."""
import argparse,datetime,hashlib,json,os,runpy,shutil,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.assembly_lab_sensors import Sensors
from scripts.assembly_lab_metrics import correlate,summarize,qualify

SELECTION=['Explain the triangle inequality for vector distances.','Describe safe SOC alert enrichment.','Compare memory locality and arithmetic throughput.','Explain the role of a validation dataset.']
HOLDOUT=['How does a norm bound the error between two approximate solutions?',
 'What evidence should an analyst preserve before rejecting an AI-generated incident summary?',
 'Why can a working set that crosses cache capacity change latency without changing instruction count?',
 'How should a penetration tester scope and verify an automated finding?',
 'Explain the difference between cryptographic diffusion and stability of a differential equation.',
 'What tests reveal whether retrieval optimizations change the selected source references?',
 'How do numerical precision and nearly equal similarity scores affect ranking?',
 'How should an organization document model limitations and retain human decision authority?']

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def e_path(path):
 p=Path(path).resolve()
 if p.drive.upper()!='E:':raise ValueError('All suite paths must resolve to E:')
 return p
def wsl_running():
 p=subprocess.run(['wsl.exe','--list','--running','--quiet'],capture_output=True,check=True)
 return 'Larpus' in p.stdout.decode('utf-16-le').replace('\x00','').split()
def registered_on_e():
 import winreg
 with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Lxss') as root:
  for i in range(winreg.QueryInfoKey(root)[0]):
   with winreg.OpenKey(root,winreg.EnumKey(root,i)) as key:
    if winreg.QueryValueEx(key,'DistributionName')[0]=='Larpus':
     return str(e_path(Path(winreg.QueryValueEx(key,'BasePath')[0])/'ext4.vhdx'))
 raise RuntimeError('Larpus distribution not found')

def write_report(directory,report):
 lines=['# Stock-envelope Assembly lab','',f"Status: {'completed' if report.get('completed') else 'held/aborted'}. Candidate: `{report.get('selected_candidate','none')}`.",'', 'These are full-index guarded scoring timings, not chat or text-to-reference fetch latency. Warm-up and preparation are outside scoring; raw samples retain preparation/quota/fallback fields. No reduced index or result memoization is used.','', '| Block / condition | Backend | n | p50 ms | p95 ms | p99 ms | <=1 ms |','|---|---|---:|---:|---:|---:|---:|']
 for condition,modes in report.get('summary',{}).items():
  for mode,s in modes.items():lines.append(f"| {condition} | {mode} | {s['n']} | {s['p50_ms']:.3f} | {s['p95_ms']:.3f} | {s['p99_ms']:.3f} | {s['at_or_below_1ms_fraction']:.1%} |")
 lines+=['', 'Guarded-score qualification: **'+str(report.get('qualification',{}).get('passed',False))+'**.']
 lines += ['- '+x for x in report.get('qualification',{}).get('reasons',[])]
 if report.get('error'):lines+=['', 'Error: '+report['error']]
 lines+=['','## Actual text-to-reference fetch','']
 neighbors=report.get('neighbors',[])
 for mode in dict.fromkeys(r['mode'] for r in neighbors):
  s=summarize([r['ms'] for r in neighbors if r['mode']==mode]);lines += [f"- {mode}: n={s['n']}, p50={s['p50_ms']:.3f} ms, p95={s['p95_ms']:.3f} ms, <=1 ms {s['at_or_below_1ms_fraction']:.1%}."]
 lines+=['', 'Complete-fetch qualification: **'+str(report.get('fetch_qualification',{}).get('passed',False))+'**.']
 lines+=['','## Scope and retained evidence','', 'Source/fixture/library/image pins: `manifest.json`. Per-call samples, correctness, selection split, quota counters and phase timestamps: `report.json`. HWiNFO captured samples and phase correlations: `sensors.json` and `sensor-phases.json`. Sensor correlation is at phase resolution, not individual millisecond-call attribution.', '', 'Candidates use sleeping native C workers with the deployed binary16 assembly or lossless float32 assembly; an aligned-half variant requests huge pages, with actual backing reported separately. Candidates preserve full row order and strengthen the empirical guard to fall back to NumPy at duplicate-row cutoff ties as well. The frozen current guard remains unchanged. Near-tie ordering can differ; candidate top-reference-set mismatches against NumPy are failures. Current reference-set mismatches are retained separately. Native pool input/output/sentinel and ownership checks are included. A finite test suite does not prove universal equivalence.', '', 'Existing CPU settings and approximately 142 W PPT envelope are retained. No BIOS, voltage, power-plan, PPT/TDC/EDC or affinity writes occur. The supervisor conservatively stops at 85 C, any CPU thermal flag, stale HWiNFO data, or observed/inferred PPT above 145 W. These are test guardrails, not CPU specifications or a guarantee about unrelated host workloads.', '', 'The selected candidate is chosen on separate selection questions. Held-out questions are used for acceptance. The 1 ms criterion requires >=100 measured calls in every early/warmed condition, p95 <=1 ms, >=95% calls <=1 ms, >=10% median gain over current Assembly and no p95 regression. A smoke run cannot qualify.', '', 'The immutable production release, model, CPU voice, nightly task and station selection are not changed. All owned files/compiler caches reside on E: or the Larpus virtual disk verified on E:. Windows may perform unrelated OS writes on C:. No application update is activated.','']
 (directory/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--run',action='store_true');parser.add_argument('--smoke',action='store_true')
 parser.add_argument('--minutes',type=int,default=20,choices=range(20,31))
 parser.add_argument('--hwinfo',type=Path,default=ROOT/'larpus-sensors.csv')
 parser.add_argument('--utc-offset-minutes',type=int,default=-240)
 args=parser.parse_args()
 if not args.run:
  print('Plan: E:-only CPU test container; 5 min settle, 10+ min interleaved full-index comparisons, 5 min warmed repeat; HWiNFO required. No station/model start or power changes. Use --run; --smoke is correctness/transport only.');return
 if os.name!='nt':raise SystemExit('Owner Windows adapter required')
 e_path(ROOT);disk=registered_on_e();sensors=Sensors(e_path(args.hwinfo),args.utc_offset_minutes)
 sample=sensors.latest();reason=sensors.safety(sample)
 if reason:raise RuntimeError(reason+'; no WSL/test load started')
 releases=runpy.run_path(str(ROOT/'scripts/releases.py'));active=releases['read'](ROOT/'data/releases/active.json')
 if releases['running'](active):raise RuntimeError('Station is running; this closed-station lab refuses to interrupt it')
 baseline=ROOT/'data/releases'/active['id'];meta=releases['read'](baseline/'release.json');profile=releases['read'](baseline/'deployment.json')
 if meta.get('status')!='prepared':raise RuntimeError('Frozen baseline is not prepared')
 for relative in ('runtime/native/score_half.S','runtime/native/liblarpus_score.so','runtime/native_scoring.py','runtime/scoring_pipeline.py'):
  if sha(baseline/relative)!=meta['files'][relative]:raise RuntimeError('Frozen baseline drift: '+relative)
 directory=e_path(ROOT/'data/assembly-linux-build/stock-lab'/uuid.uuid4().hex);directory.mkdir(parents=True)
 (directory/'tmp').mkdir();env=os.environ.copy();env.update(TEMP=str(directory/'tmp'),TMP=str(directory/'tmp'),PYTHONDONTWRITEBYTECODE='1')
 was_running=wsl_running();name='larpus-assembly-lab-'+directory.name;linux='/home/larpus/native-assembly-build/stock-lab-'+directory.name
 def execute(*cmd,input=None,timeout=180):
  p=subprocess.run(['wsl.exe','-d','Larpus','-u','larpus','--exec',*cmd],input=input,capture_output=True,timeout=timeout,env=env)
  if p.returncode:
   with (directory/'command-errors.jsonl').open('a') as log:log.write(json.dumps({'utc':utc(),'command':cmd,'stderr':p.stderr.decode(errors='replace')[-4000:],'returncode':p.returncode})+'\n')
   raise RuntimeError(p.stderr.decode(errors='replace')[-2000:])
  return p.stdout
 def podman(*cmd,**kw):return execute('/usr/bin/env','XDG_RUNTIME_DIR=/run/user/1000','/usr/bin/podman',*cmd,**kw)
 manifest={'started_utc':utc(),'release':active['id'],'image':profile['agent_image'],'wsl_disk':disk,'wsl_was_running':was_running,'native_cpu_limit':8,'wsl_config':Path.home().joinpath('.wslconfig').read_text(),'sensor_source':str(args.hwinfo),'sensor_offset_minutes':args.utc_offset_minutes,'source_sha256':{},'no_power_setting_writes':True,'no_production_activation':True}
 samples=[];process=None;report={};own_container=False;safe_to_terminate=not was_running
 status={'state':'running','phase':'build','directory':str(directory),'started_utc':utc()}
 def save_status():
  temp=directory/'status.tmp';temp.write_text(json.dumps(status,indent=2));temp.replace(directory/'status.json')
 save_status()
 try:
  if json.loads(podman('ps','--format','json')):safe_to_terminate=False;raise RuntimeError('Larpus has running containers; refusing interference')
  if profile['agent_image'].removeprefix('sha256:')!=json.loads(podman('image','inspect',profile['agent_image']))[0]['Id'].removeprefix('sha256:'):raise RuntimeError('Baseline image identity mismatch')
  execute('/bin/mkdir','-p',linux+'/native',linux+'/cache',linux+'/tmp')
  sources={'native/pool.c':ROOT/'scripts/assembly_lab_native/pool.c','native/score_float.S':ROOT/'scripts/assembly_lab_native/score_float.S','native/score_half.S':baseline/'runtime/native/score_half.S','native/check.py':ROOT/'scripts/assembly_lab_native/check.py','assembly_lab_runner.py':ROOT/'scripts/assembly_lab_runner.py','assembly_lab_metrics.py':ROOT/'scripts/assembly_lab_metrics.py','assembly_lab_guard.py':ROOT/'scripts/assembly_lab_guard.py'}
  for relative,path in sources.items():
   before=sha(path);content=path.read_bytes();execute('/usr/bin/tee',linux+'/'+relative,input=content)
   if before!=sha(path) or before!=hashlib.sha256(content).hexdigest():raise RuntimeError('Experiment source changed during capture')
   target=directory/relative;target.parent.mkdir(exist_ok=True);target.write_bytes(content);manifest['source_sha256'][relative]=before
  config={'smoke':args.smoke,'baseline_pins':{k:meta['files'][k] for k in ('runtime/native_scoring.py','runtime/scoring_pipeline.py','runtime/native/liblarpus_score.so')},'random_checks':64 if args.smoke else 1024,'screen_rounds':4 if args.smoke else 16,'settle_seconds':1 if args.smoke else 300,'comparison_seconds':15 if args.smoke else args.minutes*60-600,'repeat_seconds':15 if args.smoke else 300,'pace_seconds':.01 if args.smoke else .1,'selection_questions':SELECTION,'holdout_questions':HOLDOUT}
  (directory/'config.json').write_text(json.dumps(config,indent=2));execute('/usr/bin/tee',linux+'/config.json',input=json.dumps(config).encode())
  print('Building private C/assembly candidate on E:; station/model/voice remain stopped.',flush=True)
  build=execute('/usr/bin/env','TMPDIR='+linux+'/tmp','ZIG_GLOBAL_CACHE_DIR='+linux+'/cache','ZIG_LOCAL_CACHE_DIR='+linux+'/cache/local','/home/larpus/native-assembly-build/zig-0.17.0/zig','cc','-target','x86_64-linux-gnu','-mcpu=znver3','-O3','-fPIC','-shared','-pthread','-Wl,--build-id=none,-z,now,-z,relro,-z,noexecstack',linux+'/native/pool.c',linux+'/native/score_float.S',linux+'/native/score_half.S','-o',linux+'/liblab.so',timeout=300)
  (directory/'build.stdout').write_bytes(build)
  binary=execute('/bin/cat',linux+'/liblab.so');(directory/'liblab.so').write_bytes(binary);manifest['library_sha256']=hashlib.sha256(binary).hexdigest()
  command=['wsl.exe','-d','Larpus','-u','larpus','--exec','/usr/bin/env','XDG_RUNTIME_DIR=/run/user/1000','/usr/bin/podman','run','--rm','-i','--name',name,'--pull=never','--network=none','--read-only','--read-only-tmpfs=false','--user=1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=128','--memory=12g','--cpus=8','--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=128m','--volume='+linux+':/lab:ro','--env=HOME=/tmp','--env=PYTHONDONTWRITEBYTECODE=1','--env=LARPUS_RETRIEVAL_WORKER=local','--env=TOKENIZERS_PARALLELISM=false']
  for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):command+=['--env='+key+'=8']
  command+=['--entrypoint=python',profile['agent_image'],'-u','-c',"import runpy;runpy.run_path('/lab/assembly_lab_runner.py',run_name='__main__')"]
  manifest['command']=command;manifest['power_plan_readback']=subprocess.run(['powercfg','/getactivescheme'],capture_output=True,text=True).stdout
  manifest['compiler_version']=execute('/home/larpus/native-assembly-build/zig-0.17.0/zig','version').decode().strip()
  manifest['compiler_sha256']=execute('/usr/bin/sha256sum','/home/larpus/native-assembly-build/zig-0.17.0/zig').decode().split()[0]
  (directory/'manifest.json').write_text(json.dumps(manifest,indent=2));last_sample=None;stop_reason=None;stop_sent=None
  with (directory/'stdout.jsonl').open('wb') as stdout,(directory/'stderr.txt').open('wb') as stderr:
   process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,env=env);own_container=True
   print('Run artifacts: '+str(directory),flush=True)
   deadline=time.monotonic()+args.minutes*60+600;last_phase=None
   while process.poll() is None:
    try:
     sample=sensors.latest();reason=sensors.safety(sample)
     if sample['utc']!=last_sample:samples.append(sample);last_sample=sample['utc']
    except (OSError,ValueError) as exc:reason='Sensor read failed: '+str(exc)
    if time.monotonic()>deadline:reason='Experiment exceeded its wall-clock deadline'
    with (directory/'stdout.jsonl').open('rb') as progress:
     progress.seek(0,2);progress.seek(max(0,progress.tell()-128*1024));lines=progress.read().split(b'\n')[:-1]
    for line in reversed(lines):
     try:latest=json.loads(line)
     except (ValueError,UnicodeDecodeError):continue
     if latest.get('phase'):status['phase']=latest['phase'];break
    status.update(sensor_utc=last_sample,updated_utc=utc())
    if status['phase']!=last_phase:print('Phase: '+status['phase'],flush=True);last_phase=status['phase']
    save_status()
    if reason and stop_sent is None:
     stop_reason=reason;stop_sent=time.monotonic();podman('kill','--signal','SIGTERM',name);print('Test stopping: '+reason,flush=True)
    if stop_sent is not None and time.monotonic()-stop_sent>20:podman('stop','--time','5',name);break
    time.sleep(1)
  for line in (directory/'stdout.jsonl').read_text().splitlines():
   obj=json.loads(line)
   if obj.get('type')=='result':report=obj['report']
  if not report:raise RuntimeError('Runner produced no complete result; inspect stderr.txt')
  if stop_reason:report['supervisor_stop']=stop_reason;report['completed']=False;report['qualification']['passed']=False;report['qualification']['reasons'].append(stop_reason)
  report['returncode']=process.poll();report['production_started']=False
  (directory/'report.json').write_text(json.dumps(report,indent=2));(directory/'sensors.json').write_text(json.dumps(samples))
  joined=correlate(samples,report.get('phases',[]));(directory/'sensor-phases.json').write_text(json.dumps(joined,indent=2));write_report(directory,report)
  status.update(state='completed' if report.get('completed') else 'held',finished_utc=utc());save_status()
  print(json.dumps({'report':str(directory/'REPORT.md'),'completed':report.get('completed'),'candidate':report.get('selected_candidate'),'qualification':report.get('qualification')}),flush=True)
 except Exception as exc:
  status.update(state='held',error=type(exc).__name__+': '+str(exc),finished_utc=utc());save_status()
  (directory/'sensors.json').write_text(json.dumps(samples))
  if not report:
   report={'completed':False,'error':status['error'],'qualification':{'passed':False,'reasons':['Run did not complete']}}
   (directory/'report.json').write_text(json.dumps(report,indent=2));write_report(directory,report)
  raise
 finally:
  if process is not None and process.poll() is None and own_container:
   try:podman('stop','--time','5',name)
   except Exception:pass
   process.wait(timeout=30)
  if safe_to_terminate:
   remaining=json.loads(podman('ps','--format','json'))
   if not remaining:subprocess.run(['wsl.exe','--terminate','Larpus'],check=True,capture_output=True,timeout=60)
  manifest['finished_utc']=utc();manifest['production_started']=False
  (directory/'manifest.json').write_text(json.dumps(manifest,indent=2))
 if not report.get('completed'):raise SystemExit(2)

if __name__=='__main__':main()
