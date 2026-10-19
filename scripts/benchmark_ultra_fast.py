"""Ultra Fast: owner-only raw-model benchmark; dry-run by default, never a LAN mode."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.benchmark_mcp_skills import percentiles
from scripts.ultra_fast_station import Station
from scripts import releases
from runtime.isolation import wsl_command

CASE_IDS=('home-greeting','home-norms','home-stability-pushback','cyber-soc')
PREPARE="""import json,sys,time
from runtime.agents import load_personas,messages_for
from runtime.knowledge import augment
from runtime.retrieval_worker import call
from runtime.context import OUTPUT_LIMIT
deadline=time.monotonic()+60
while True:
 try:
  if call({'action':'status'},2).get('ready') is True:break
 except OSError:pass
 if time.monotonic()>deadline:raise RuntimeError('Retrieval worker not ready')
 time.sleep(.5)
c=json.loads(sys.argv[1]);p=load_personas()[c['persona']]
m,e=augment(messages_for(p,c['messages']),c['persona'])
print(json.dumps({'messages':m,'evidence':e,'temperature':p['temperature'],'output_limit':OUTPUT_LIMIT}))
"""


def cases():
    value=json.loads((ROOT/'evals/performance.json').read_text())
    return [c for c in value['cases'] if c['id'] in CASE_IDS]


def payload(tag,context,temperature,messages,limit):
    return {'model':tag,'messages':messages,'stream':True,'think':False,'keep_alive':-1,
            'options':{'temperature':temperature,'num_ctx':context,'num_predict':limit,'num_gpu':99}}


def schedule(catalog,repeats):
    return [('warmup' if r==0 else 'measured',c,v,r) for r in range(repeats+1) for c in catalog
            for v in (('raw','prepared') if r%2==0 else ('prepared','raw'))]


def summarize(rows):
    result={}
    for variant in ('raw','prepared'):
        subset=[r for r in rows if r['phase']=='measured' and r['variant']==variant]
        good=[r for r in subset if r['ok']]
        result[variant]={'attempted':len(subset),'succeeded':len(good)}
        for key in ('first_text_seconds','total_seconds','owner_elapsed_seconds','tokens_per_second'):
            result[variant][key]=percentiles(r.get(key) for r in good)
    return result


def valid(rows,expected,before,after):
    return len(rows)==expected and before==after and all(r['ok'] for r in rows)


def direct(station,value):
    args=['run','-i','--rm','--pull=never','--pod=larpus-offline','--read-only','--read-only-tmpfs=false',
          '--user=1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=32','--memory=256m','--cpus=1',
          '--log-driver=none','--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=32m','--entrypoint=python',station.profile['agent_image'],
          '-c',(ROOT/'scripts/ultra_fast_worker.py').read_text()]
    started=time.perf_counter()
    try:
        result=subprocess.run(wsl_command('podman',*args),input=json.dumps(value),capture_output=True,text=True,encoding='utf8',timeout=210,check=True)
        row=json.loads(result.stdout)
    except KeyboardInterrupt:row={'ok':False,'error':'interrupted','first_text_seconds':None}
    except (subprocess.SubprocessError,ValueError):row={'ok':False,'error':'owner_worker_failed','first_text_seconds':None}
    row['owner_elapsed_seconds']=time.perf_counter()-started
    return row


def prepare(station,catalog,directory):
    result={}
    for case in catalog:
        observed=json.loads(releases.podman('exec',station.profile['agent_name'],'python','-c',PREPARE,json.dumps(case),timeout=100))
        result[case['id']]=observed
    (directory/'prepared-prompts.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    return result


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf8')


def run(repeats):
    directory=ROOT/'data/evals/ultra-fast'/uuid.uuid4().hex;directory.mkdir(parents=True)
    catalog=cases();plan=schedule(catalog,repeats);rows=[]
    report={'name':'Ultra Fast owner benchmark','valid':False,'repeats':repeats,'expected':len(plan),
            'timing_scope':'Inside offline client: HTTP request to first nonempty unscreened model text; excludes client/container launch and prompt preparation.',
            'bypassed':['per-request isolation/integrity preflight','MCP','broker scheduling/budgets','input/output screening','sentence release gate'],
            'retained':['offline container boundary','owner-only fixed endpoint','setup/model identity checks outside timing','fixed resource limits'],
            'limits':'Raw drops persona/evidence; prepared assembles it once outside timing. Neither is normal end-to-end latency or proof of quality preservation.'}
    station=Station()
    try:
        with releases.exclusive(),station:
            report['release']=station.state['id'];report['model']=station.model;report['selection']=station.before
            prepared=prepare(station,catalog,directory)
            report['prompt_sha256']={k:hashlib.sha256(json.dumps(v['messages'],sort_keys=True).encode()).hexdigest() for k,v in prepared.items()}
            for phase,case,variant,round_no in plan:
                data=prepared[case['id']]
                messages=case['messages'] if variant=='raw' else data['messages']
                value=payload(station.model['name'],station.model['context_length'],data['temperature'],messages,data['output_limit'])
                row=direct(station,value);row.update(phase=phase,case=case['id'],variant=variant,round=round_no)
                rows.append(row)
                with (directory/'raw.jsonl').open('a',encoding='utf8') as stream:stream.write(json.dumps(row)+'\n')
                print(json.dumps({k:row.get(k) for k in ('phase','case','variant','round','ok','first_text_seconds')}),flush=True)
                if row.get('error')=='interrupted':raise KeyboardInterrupt
            after=station.backend.read();station.backend.verify(after['active_id'])
            report['valid']=valid(rows,len(plan),station.before,after)
    except BaseException as exc:
        report['error_type']=type(exc).__name__
        raise
    finally:
        report['cleanup']=station.cleanup;report['summary']=summarize(rows)
        report['valid']=report['valid'] and station.cleanup.get('restored',False)
        write(directory/'report.json',report);print('Report: '+str(directory/'report.json'),flush=True)
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    parser.add_argument('--repeats',type=int,choices=(2,4,6,8),default=4);args=parser.parse_args(argv)
    print(json.dumps({'mode':'Ultra Fast owner benchmark','running':args.run,'calls':len(schedule(cases(),args.repeats))}),flush=True)
    if args.run:return 0 if run(args.repeats)['valid'] else 1
    return 0


if __name__=='__main__':raise SystemExit(main())
