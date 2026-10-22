"""Owner-only MTRAGEval-inspired accounting; live C runs require --run-c."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import performance_state as station
from runtime.capability_trials import save

CATALOG=ROOT/'evals/mtrageval-local.json'
STORE=ROOT/'data/evals/mtrageval'
CLASSES={'answerable','unanswerable','underspecified','non-standalone','unclear'}
TASKS={'A','B','C'}
MAX_LINE=400000


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest()


def catalog(path=CATALOG):
    value=json.loads(Path(path).read_text(encoding='utf-8'))
    return catalog_from_value(value)


def catalog_from_value(value):
    if type(value) is not dict or value.get('version')!=1 or not isinstance(value.get('cases'),list) or not 1<=len(value['cases'])<=100:
        raise ValueError('Invalid MTRAGEval local catalog')
    ids=set()
    for case in value['cases']:
        if type(case) is not dict or set(case)!={'id','family','class','persona','messages','gold_source_ids','fixed_evidence','review_points'}:
            raise ValueError('Invalid case fields')
        if any(type(case[key]) is not str or not re.fullmatch('[a-z0-9-]{1,80}',case[key]) for key in ('id','family')):
            raise ValueError('Invalid case identity')
        if case['id'] in ids or type(case['class']) is not str or case['class'] not in CLASSES or type(case['persona']) is not str or case['persona'] not in {'home-assistant','it-larp-coach'}:
            raise ValueError('Duplicate or unsupported case')
        ids.add(case['id'])
        messages=case['messages']
        if not isinstance(messages,list) or not 3<=len(messages)<=15 or len(messages)%2!=1:
            raise ValueError('Invalid conversation length')
        for n,message in enumerate(messages):
            if type(message) is not dict or set(message)!={'role','content'} or message['role']!=('user' if n%2==0 else 'assistant') or type(message['content']) is not str or not 1<=len(message['content'])<=8000:
                raise ValueError('Invalid conversation turn')
        gold=case['gold_source_ids']
        if not isinstance(gold,list) or len(gold)>10 or len(gold)!=len(set(gold)) or any(type(x) is not str or not re.fullmatch('[a-z0-9-]{3,100}',x) for x in gold):
            raise ValueError('Invalid gold evidence')
        fixed=case['fixed_evidence']
        if (not isinstance(fixed,list) or len(fixed)>3 or
                any(type(x) is not dict or set(x)!={'id','locator'} or x['id'] not in gold or
                    type(x['locator']) is not str or not 1<=len(x['locator'])<=200 for x in fixed) or
                len({(x['id'],x['locator']) for x in fixed})!=len(fixed)):
            raise ValueError('Invalid fixed evidence selection')
        if not isinstance(case['review_points'],list) or not case['review_points'] or any(type(x) is not str or not 1<=len(x)<=500 for x in case['review_points']):
            raise ValueError('Invalid review points')
    return value


def prepare(value):
    return {'version':1,'id':uuid.uuid4().hex,'catalog_sha256':digest(value),'cases':[c['id'] for c in value['cases']],
            'arms':{},'records':[], 'status':'deferred',
            'scope':'Local adaptation of MTRAGEval, not an official benchmark result. A and B require independent task receipts; C uses the existing checked HTTP path. Reviews are unset.'}


def checked_record(record,case_ids):
    keys={'task','case','arm','repeat','status','sources','first_text_seconds','total_seconds','prompt_tokens','output_tokens','review'}
    if type(record) is not dict or set(record)!=keys or any(type(record[k]) is not str for k in ('task','case','arm','status')) or record['task'] not in TASKS or record['case'] not in case_ids or record['arm'] not in {'baseline','candidate'} or type(record['repeat']) is not int or not 1<=record['repeat']<=10 or record['status'] not in {'complete','held','failed'}:
        raise ValueError('Invalid task record')
    if not isinstance(record['sources'],list) or len(record['sources'])>30 or len(record['sources'])!=len(set(s for s in record['sources'] if type(s) is str)) or any(type(s) is not str or not re.fullmatch('[a-z0-9-]{3,100}',s) for s in record['sources']):
        raise ValueError('Invalid retrieved IDs')
    for key in ('first_text_seconds','total_seconds'):
        number=record[key]
        if number is not None and (type(number) not in (int,float) or not math.isfinite(number) or number<0):raise ValueError('Invalid latency')
    for key in ('prompt_tokens','output_tokens'):
        number=record[key]
        if number is not None and (type(number) is not int or not 0<=number<=131072):raise ValueError('Invalid token count')
    review=record['review']
    if review is not None and (type(review) is not dict or set(review)!={'reviewer','answer_correct','evidence_supported','note'} or type(review['reviewer']) is not str or not review['reviewer'].strip() or type(review['note']) is not str or not review['note'].strip() or any(type(review[k]) is not bool for k in ('answer_correct','evidence_supported'))):
        raise ValueError('Invalid manual review')
    if review is not None and record['status']!='complete':raise ValueError('Cannot review incomplete answer')
    return record


def validate_run(run,value):
    if type(run) is not dict or run.get('version')!=1 or run.get('catalog_sha256')!=digest(value) or run.get('cases')!=[c['id'] for c in value['cases']] or not isinstance(run.get('records'),list) or len(run['records'])>3000 or not isinstance(run.get('arms'),dict):
        raise ValueError('Catalog or run changed')
    if set(run['arms'])-{'baseline','candidate'}:raise ValueError('Invalid arm')
    seen=set();case_ids=set(run['cases'])
    for record in run['records']:
        checked_record(record,case_ids)
        key=(record['arm'],record['task'],record['case'],record['repeat'])
        if key in seen:raise ValueError('Duplicate task record')
        seen.add(key)
    return run


def summarize(run,value):
    validate_run(run,value)
    cases={c['id']:c for c in value['cases']};summary={}
    for arm in ('baseline','candidate'):
        summary[arm]={}
        for task in ('A','B','C'):
            rows=[r for r in run['records'] if r['arm']==arm and r['task']==task]
            completed=[r for r in rows if r['status']=='complete']
            reviewed=[r for r in completed if r['review'] is not None]
            hits=[set(cases[r['case']]['gold_source_ids']).issubset(r['sources']) for r in completed if cases[r['case']]['gold_source_ids']]
            summary[arm][task]={'attempts':len(rows),'completed':len(completed),'failed_or_held':len(rows)-len(completed),
                'human_reviewed':len(reviewed),'answer_correct':sum(r['review']['answer_correct'] for r in reviewed),
                'evidence_supported':sum(r['review']['evidence_supported'] for r in reviewed),
                'gold_source_complete_hits':sum(hits),'gold_source_scored':len(hits),
                'prompt_tokens':distribution([r['prompt_tokens'] for r in completed]),
                'first_text_seconds':distribution([r['first_text_seconds'] for r in completed]),
                'total_seconds':distribution([r['total_seconds'] for r in completed])}
    expected=set(cases)
    coverage=all({r['case'] for r in run['records'] if r['arm']==arm and r['task']==task}==expected for arm in ('baseline','candidate') for task in ('A','B','C'))
    schedules=all({(r['case'],r['repeat']) for r in run['records'] if r['arm']=='baseline' and r['task']==task}==
                  {(r['case'],r['repeat']) for r in run['records'] if r['arm']=='candidate' and r['task']==task} for task in ('A','B','C'))
    stable=all(run['arms'].get(arm,{}).get('stable') is True for arm in ('baseline','candidate'))
    old=run['arms'].get('baseline',{}).get('before',{})
    new=run['arms'].get('candidate',{}).get('before',{})
    matched_station=bool(old and new) and all(old.get(key)==new.get(key) for key in
        ('source_fingerprint','context','retrieval','database_sha256','embedding_manifest_sha256','notes_manifest_sha256'))
    distinct_model=bool(old and new and old.get('model_weight_sha256') and new.get('model_weight_sha256') and
        old['model_weight_sha256']!=new['model_weight_sha256'])
    imports=run.get('imports',[])
    fingerprints=all(imported['source_fingerprint']==run['arms'].get(imported['arm'],{}).get('before',{}).get('source_fingerprint') and
        (imported['task']=='A' or imported['model_weight_sha256']==run['arms'].get(imported['arm'],{}).get('before',{}).get('model_weight_sha256')) for imported in imports)
    fixed={imported['arm']:imported['fixed_evidence_sha256'] for imported in imports if imported['task']=='B'}
    matched_evidence=set(fixed)=={'baseline','candidate'} and fixed['baseline']==fixed['candidate']
    summary['comparison_ready']=coverage and schedules and stable and matched_station and distinct_model and fingerprints and matched_evidence and all(
        summary[arm][task]['attempts'] and summary[arm][task]['human_reviewed']==summary[arm][task]['completed']
        and not summary[arm][task]['failed_or_held'] for arm in ('baseline','candidate') for task in ('A','B','C'))
    summary['limits']='Descriptive only; candidate must have a distinct recorded model weight and matched source/context/retrieval pins. B needs fixed supplied evidence without retrieval. C source IDs are not an independent A result. Human review is required; no automatic promotion.'
    return summary


def distribution(numbers):
    values=sorted(n for n in numbers if n is not None)
    if not values:return None
    return {'samples':len(values),'median':values[len(values)//2] if len(values)%2 else (values[len(values)//2-1]+values[len(values)//2])/2,
            'p95_nearest_rank':values[math.ceil(len(values)*.95)-1],'max':values[-1]}


def probe_case(opener,case):
    """One existing checked local HTTP stream, with no retry or direct-model path."""
    payload=json.dumps({'persona':case['persona'],'messages':case['messages']}).encode()
    request=urllib.request.Request('http://127.0.0.1:8080/api/chat/stream',payload,{'Content-Type':'application/json'})
    started=time.perf_counter();state={'ok':False,'first_text_seconds':None,'total_seconds':None,'context':None,'error':None}
    chunks=[];sources=[];characters=0
    try:
        with opener.open(request,timeout=180) as response:
            if getattr(response,'status',200)!=200:raise ValueError('Unexpected HTTP status')
            while True:
                line=response.readline(MAX_LINE+1)
                if not line or len(line)>MAX_LINE or time.perf_counter()-started>180:raise ValueError('Missing or oversized completion')
                event=json.loads(line)
                if event.get('type')=='error':state['error']='stream_rejected';break
                if event.get('type')=='text':
                    content=event.get('content')
                    if type(content) is not str:raise ValueError('Invalid text event')
                    if content and state['first_text_seconds'] is None:state['first_text_seconds']=round(time.perf_counter()-started,3)
                    characters+=len(content)
                    if characters>65536:raise ValueError('Oversized response')
                    chunks.append(content)
                    continue
                if event.get('type')!='done':raise ValueError('Invalid stream event')
                sources=event.get('sources',[])
                if not isinstance(sources,list) or any(not isinstance(s,dict) or type(s.get('id')) is not str for s in sources):raise ValueError('Invalid source receipt')
                context=event.get('context')
                if isinstance(context,dict):
                    state['context']={k:context[k] for k in ('prompt_tokens','output_tokens') if type(context.get(k)) is int and 0<=context[k]<=131072}
                state['ok']=bool(''.join(chunks).strip())
                if not state['ok']:state['error']='empty_answer'
                break
    except urllib.error.HTTPError:state['error']='http_rejected'
    except OSError:state['error']='transport_error'
    except (ValueError,KeyError,TypeError):state['error']='invalid_protocol'
    state['total_seconds']=round(time.perf_counter()-started,3)
    return state,{'answer':''.join(chunks),'sources':sources} if state['ok'] else None


def record_c(run,value,arm,repeats,opener):
    validate_run(run,value)
    if arm in run['arms']:raise ValueError('Arm already recorded; create a new run for retries')
    before=station.snapshot(opener);run['arms'][arm]={'before':before,'after':None,'stable':False,'task':'C'}
    save(STORE/run['id']/'run.json',run)
    for repeat in range(1,repeats+1):
        for case in value['cases']:
            row,answer=probe_case(opener,case)
            context=row.get('context') if isinstance(row.get('context'),dict) else {}
            record={'task':'C','case':case['id'],'arm':arm,'repeat':repeat,'status':'complete' if row['ok'] else 'failed',
                    'sources':[s['id'] for s in answer['sources']] if answer else [],
                    'first_text_seconds':row.get('first_text_seconds'),'total_seconds':row.get('total_seconds'),
                    'prompt_tokens':context.get('prompt_tokens'),'output_tokens':context.get('output_tokens'),'review':None}
            checked_record(record,set(run['cases']))
            if answer:save(STORE/run['id']/f"{arm}-{repeat}-{case['id']}.json",{'answer':answer,'record_sha256':digest(record)})
            run['records'].append(record)
            save(STORE/run['id']/'run.json',run)
    try:run['arms'][arm]['after']=station.snapshot(opener)
    finally:
        run['arms'][arm]['stable']=run['arms'][arm]['before']==run['arms'][arm]['after']
        save(STORE/run['id']/'run.json',run)
    return run


def import_task(run,value,receipt,*,executed_locally=False):
    validate_run(run,value)
    if type(receipt) is not dict or set(receipt)!={'task','arm','method','source_fingerprint','model_weight_sha256','fixed_evidence_sha256','retrieval_disabled','records'}:
        raise ValueError('Invalid task receipt')
    task=receipt['task'];arm=receipt['arm']
    if type(task) is not str or task not in {'A','B'} or type(arm) is not str or arm not in {'baseline','candidate'} or type(receipt['method']) is not str or not receipt['method'].strip() or type(receipt['source_fingerprint']) is not str or not re.fullmatch('[a-f0-9]{64}',receipt['source_fingerprint']):
        raise ValueError('Invalid task identity')
    if type(receipt['retrieval_disabled']) is not bool or receipt['retrieval_disabled']!=(task=='B'):
        raise ValueError('B requires fixed supplied evidence without retrieval')
    model_hash=receipt['model_weight_sha256'];evidence_hash=receipt['fixed_evidence_sha256']
    if task=='B':
        if any(type(x) is not str or not re.fullmatch('[a-f0-9]{64}',x) for x in (model_hash,evidence_hash)):
            raise ValueError('B requires model and fixed-evidence hashes')
    elif model_hash is not None or evidence_hash is not None:
        raise ValueError('A has no generation model or fixed-evidence packet')
    if not isinstance(receipt['records'],list) or not receipt['records'] or len(receipt['records'])>1000:
        raise ValueError('Invalid task records')
    if {r.get('case') for r in receipt['records'] if isinstance(r,dict)}!=set(run['cases']):
        raise ValueError('Task receipt must cover every case')
    if (arm,task) in {(r['arm'],r['task']) for r in run['records']}:
        raise ValueError('Task already recorded; use a new run for retries')
    ids=set(run['cases']);records=receipt['records']
    for record in records:
        checked_record(record,ids)
        if record['task']!=task or record['arm']!=arm:raise ValueError('Mixed task receipt')
    trial={**run,'records':run['records']+records}
    validate_run(trial,value)
    run['records']=trial['records']
    run.setdefault('imports',[]).append({'task':task,'arm':arm,'method':receipt['method'],
        'source_fingerprint':receipt['source_fingerprint'],'model_weight_sha256':model_hash,
        'fixed_evidence_sha256':evidence_hash,'receipt_sha256':digest(receipt),
        'claim':('Executed by the owner-only sealed-agent A/B probe; station pins checked before and after' if executed_locally else
                 'Operator-supplied task receipt; this harness did not independently execute or verify it')})
    return run


def probe_ab(profile,task,case):
    """One bounded owner request to the active sealed agent, outside public MCP."""
    from runtime.isolation import agent_name,wsl_command
    request={'task':task,'persona':case['persona'],'messages':case['messages'],
             'fixed_selectors':case['fixed_evidence'] if task=='B' else None}
    command=wsl_command('podman','exec','--interactive',agent_name(profile),'python','-m','runtime.rag_eval')
    try:
        result=subprocess.run(command,input=json.dumps(request).encode(),capture_output=True,
                              timeout=930 if task=='B' else 120)
        if result.returncode or len(result.stdout)>200000:
            return {'status':'failed','seconds':None,'error':'sealed_agent_probe_failed'}
        reply=json.loads(result.stdout)
        if type(reply) is not dict or type(reply.get('status')) is not int or type(reply.get('seconds')) not in (int,float):
            raise ValueError('Invalid probe response')
        if reply['status']!=200:
            return {'status':'held','seconds':reply['seconds'],'error':'sealed_agent_held'}
        if task=='A':
            if type(reply.get('passages')) is not list or len(reply['passages'])>3 or any(
                    type(p) is not dict or set(p)!={'id','locator'} or
                    type(p['id']) is not str or not re.fullmatch('[a-z0-9-]{3,100}',p['id']) or
                    type(p['locator']) is not str or not 1<=len(p['locator'])<=200 for p in reply['passages']):
                raise ValueError('Invalid retrieval probe')
        elif (type(reply.get('answer')) is not str or not reply['answer'].strip() or
              len(reply['answer'])>65536 or type(reply.get('sources')) is not list or len(reply['sources'])>3 or
              any(type(p) is not dict or set(p)!={'id','locator','preview'} or
                  type(p['id']) is not str or not re.fullmatch('[a-z0-9-]{3,100}',p['id']) or
                  type(p['locator']) is not str or not 1<=len(p['locator'])<=200 or
                  type(p['preview']) is not str or len(p['preview'])>8000 for p in reply['sources'])):
            raise ValueError('Invalid generation probe')
        return reply
    except (OSError,ValueError,TypeError,subprocess.TimeoutExpired):
        return {'status':'failed','seconds':None,'error':'sealed_agent_probe_invalid'}


def record_ab(run,value,arm,task,repeats,opener):
    validate_run(run,value)
    if task not in ('A','B') or arm not in run['arms'] or not run['arms'][arm]['stable']:
        raise ValueError('Record a stable C arm before A/B')
    if any(r['arm']==arm and r['task']==task for r in run['records']):
        raise ValueError('Task already recorded; create a new run for retries')
    before=station.snapshot(opener)
    if before!=run['arms'][arm]['before']:
        raise ValueError('Station differs from the recorded C arm')
    release=ROOT/'data/releases'/before['release']
    if not (release/'runtime/rag_eval.py').is_file():
        raise ValueError('Active sealed release lacks the A/B evaluator')
    profile=json.loads((release/'deployment.json').read_text(encoding='utf-8'))
    if profile.get('source_fingerprint')!=before['source_fingerprint']:
        raise ValueError('Sealed agent source fingerprint differs')
    records=[];details=[]
    for repeat in range(1,repeats+1):
        for case in value['cases']:
            reply=probe_ab(profile,task,case)
            complete=reply.get('status')==200
            passages=reply.get('passages',[]) if task=='A' else reply.get('sources',[])
            ids=list(dict.fromkeys(p['id'] for p in passages)) if complete else []
            context=reply.get('context') if complete and task=='B' else None
            context=context if isinstance(context,dict) else {}
            row={'task':task,'case':case['id'],'arm':arm,'repeat':repeat,
                 'status':'complete' if complete else reply['status'],
                 'sources':ids,'first_text_seconds':None,'total_seconds':reply.get('seconds'),
                 'prompt_tokens':context.get('prompt_tokens') if task=='B' else None,
                 'output_tokens':context.get('output_tokens') if task=='B' else None,'review':None}
            checked_record(row,set(run['cases']))
            records.append(row)
            details.append({'case':case['id'],'repeat':repeat,'passages':passages,
                            'answer':reply.get('answer') if complete and task=='B' else None,
                            'error':reply.get('error') if not complete else None})
            save(STORE/run['id']/f'{arm}-{task}-attempt.json',{'state':'in_progress','records':records,'details':details})
    after=station.snapshot(opener)
    if before!=after:
        save(STORE/run['id']/f'{arm}-{task}-unstable.json',{'before':before,'after':after,'records':records})
        raise ValueError('Station changed during A/B; incomplete receipt retained privately')
    receipt={'task':task,'arm':arm,'method':'owner-only sealed-agent capability probe',
             'source_fingerprint':before['source_fingerprint'],
             'model_weight_sha256':before['model_weight_sha256'] if task=='B' else None,
             'fixed_evidence_sha256':digest({'database_sha256':before['database_sha256'],
                 'cases':[(c['id'],c['fixed_evidence']) for c in value['cases']]}) if task=='B' else None,
             'retrieval_disabled':task=='B','records':records}
    # Save complete private details before adding the summary to the run.
    save(STORE/run['id']/f'{arm}-{task}-details.json',{'receipt_sha256':digest(receipt),'details':details})
    import_task(run,value,receipt,executed_locally=True)
    save(STORE/run['id']/'run.json',run)
    return run


def review_record(run,value,arm,task,case,repeat,reviewer,note,correct,supported):
    validate_run(run,value)
    matches=[r for r in run['records'] if (r['arm'],r['task'],r['case'],r['repeat'])==(arm,task,case,repeat)]
    if len(matches)!=1 or matches[0]['status']!='complete' or matches[0]['review'] is not None:
        raise ValueError('Review requires one complete, unreviewed record')
    matches[0]['review']={'reviewer':reviewer,'answer_correct':correct,'evidence_supported':supported,'note':note}
    validate_run(run,value)
    return run


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('validate');sub.add_parser('prepare')
    report=sub.add_parser('report');report.add_argument('run_id')
    imported=sub.add_parser('import-task');imported.add_argument('run_id');imported.add_argument('receipt')
    reviewed=sub.add_parser('review');reviewed.add_argument('run_id');reviewed.add_argument('--arm',choices=('baseline','candidate'),required=True)
    reviewed.add_argument('--task',choices=('A','B','C'),required=True);reviewed.add_argument('--case',required=True);reviewed.add_argument('--repeat',type=int,required=True)
    reviewed.add_argument('--reviewer',required=True);reviewed.add_argument('--note',required=True)
    reviewed.add_argument('--correct',choices=('yes','no'),required=True);reviewed.add_argument('--supported',choices=('yes','no'),required=True)
    live=sub.add_parser('run-c');live.add_argument('run_id');live.add_argument('--arm',choices=('baseline','candidate'),required=True);live.add_argument('--repeats',type=int,choices=range(1,11),default=3)
    for command in ('run-a','run-b'):
        selected=sub.add_parser(command);selected.add_argument('run_id')
        selected.add_argument('--arm',choices=('baseline','candidate'),required=True)
        selected.add_argument('--repeats',type=int,choices=range(1,11),default=3)
        selected.add_argument('--tuning-finished',action='store_true');selected.add_argument('--quiet-window',action='store_true')
    live.add_argument('--tuning-finished',action='store_true');live.add_argument('--quiet-window',action='store_true')
    args=parser.parse_args(argv);value=catalog()
    if args.command=='validate':print(json.dumps({'cases':len(value['cases']),'catalog_sha256':digest(value),'live_requests':0}));return 0
    if args.command=='prepare':
        run=prepare(value);directory=STORE/run['id'];directory.mkdir(parents=True,exist_ok=False);save(directory/'run.json',run)
        print(json.dumps({'run':run['id'],'state':'deferred','path':str(directory/'run.json')}));return 0
    if not re.fullmatch('[a-f0-9]{32}',args.run_id):parser.error('Invalid run ID')
    path=STORE/args.run_id/'run.json';run=validate_run(json.loads(path.read_text(encoding='utf-8')),value)
    if args.command=='report':print(json.dumps(summarize(run,value),indent=2));return 0
    if args.command=='review':
        review_record(run,value,args.arm,args.task,args.case,args.repeat,args.reviewer,args.note,args.correct=='yes',args.supported=='yes')
        save(path,run);print(json.dumps({'run':run['id'],'reviewed':args.case,'task':args.task,'arm':args.arm}));return 0
    if args.command=='import-task':
        receipt=json.loads(Path(args.receipt).read_text(encoding='utf-8'))
        import_task(run,value,receipt);save(path,run)
        print(json.dumps({'run':run['id'],'task':receipt['task'],'arm':receipt['arm'],'records':len(receipt['records'])}));return 0
    if not args.tuning_finished or not args.quiet_window:
        parser.error('Live A/B/C requires --tuning-finished and --quiet-window owner attestations')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    if args.command=='run-c':record_c(run,value,args.arm,args.repeats,opener)
    else:record_ab(run,value,args.arm,args.command[-1].upper(),args.repeats,opener)
    task=args.command[-1].upper()
    print(json.dumps({'run':run['id'],'arm':args.arm,'summary':summarize(run,value)[args.arm][task]}));return 0


if __name__=='__main__':raise SystemExit(main())
