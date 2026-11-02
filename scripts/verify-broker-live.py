"""Owner-local prepared-release evidence. Requires paused notes; never stops services."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('owner_releases',ROOT/'scripts/releases.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)
DOCUMENT='\n'.join(f'Synthetic observatory record {i}: chamber {i} contains a clockwork dial calibrated to {i+20} degrees; measurements apply only to this fictional chamber, under dry laboratory conditions.' for i in range(1,31))

CLIENT='''import http.client,socket,json,sys
c=http.client.HTTPConnection('localhost',timeout=30);c.sock=socket.socket(socket.AF_UNIX);c.sock.settimeout(30);c.sock.connect('/run/larpus-broker/inference.sock')
path=sys.argv[1]
if path=='/api/chat':
 from runtime.agents import load_personas,messages_for
 from runtime.inference import active_model
 from runtime.knowledge import EVIDENCE_PROMPT,NO_EVIDENCE_PROMPT
 p=load_personas()['home-assistant'];m=messages_for(p,[{'role':'user','content':'Hello'}]);m[0]['content']+=EVIDENCE_PROMPT+NO_EVIDENCE_PROMPT
 body={'model':active_model(p['model']),'messages':m,'stream':False,'think':False,'keep_alive':-1,'options':{'temperature':p['temperature'],'num_ctx':131072,'num_predict':32,'num_gpu':99}}
 c.request('POST',path,json.dumps(body))
else:c.request('GET',path)
r=c.getresponse();v=json.loads(r.read());c.close()
if path=='/api/chat':v={'done':v.get('done'),'eval_count':v.get('eval_count'),'error':v.get('code')}
print(json.dumps({'http':r.status,'value':v}))
'''

def note_summary(note):
    """Outcome fields only; generated note text never enters the receipt."""
    if not isinstance(note,dict):return {'type':type(note).__name__}
    return {'ok':'ok' in note,'code':note.get('code'),'error':note.get('error'),'http_status':note.get('http_status'),
            'done_reason':note.get('metrics',{}).get('done_reason') if isinstance(note.get('metrics'),dict) else None}

# Readiness spends at most CHAT_PROBES chat-lane requests, CHAT_PROBE_SPACING s apart, so
# readiness plus the one preempting chat stays far below the broker's 12/min chat budget.
# Polling uses the broker's status lane (/api/ps, /broker/state), never chat quota, at rates
# below its 120/min status budget.
CHAT_PROBES=4;CHAT_PROBE_SPACING=10;RESIDENT_WINDOW=30;RESIDENT_POLL=5;STATE_POLL=.75
WAITABLE={(503,'cancellation_unconfirmed'),(429,'inference_budget')}

def broker_state(agent_call):
    state=agent_call('/broker/state')
    if state['http']!=200:raise RuntimeError('Broker state unavailable: '+json.dumps(state['value']))
    return state['value']

def model_resident(agent_call):
    """Non-chat signal: the broker's status lane lists the approved model as loaded."""
    listed=agent_call('/api/ps')
    return listed['http']==200 and bool(listed['value'].get('models'))

def wait_resident(agent_call,clock,sleep,window=RESIDENT_WINDOW):
    """Best effort: give a loading model time on the status lane before any chat probe."""
    deadline=clock()+window
    while not model_resident(agent_call):
        if clock()>=deadline:return False
        sleep(RESIDENT_POLL)
    return True

def probe_outcome(agent_call):
    """One chat-lane probe: 'ready', 'wait' (unconfirmed fence or chat budget hold on an
    unfaulted broker) or 'fail' (fault or any other refusal)."""
    warm=agent_call('/api/chat');attempt={'http':warm['http'],'code':warm['value'].get('error')}
    if warm['http']==200 and warm['value'].get('done') is True:return attempt,'ready'
    state=agent_call('/broker/state')
    if state['http']!=200 or state['value'].get('faulted') or (attempt['http'],attempt['code']) not in WAITABLE:return attempt,'fail'
    return attempt,'wait'

def ready_broker(agent_call,clock,sleep):
    """Readiness handshake: one completed chat proves the broker's first-use idle fence and
    model are ready before the note starts. Bounded chat probes; status-lane waiting."""
    resident=wait_resident(agent_call,clock,sleep);attempts=[]
    for _ in range(CHAT_PROBES):
        attempt,outcome=probe_outcome(agent_call);attempts.append(attempt)
        if outcome=='ready':return {'model_resident':resident,'chat_probes':attempts}
        if outcome=='fail':break
        sleep(CHAT_PROBE_SPACING)
    raise RuntimeError('Broker readiness handshake failed: '+json.dumps({'model_resident':resident,'chat_probes':attempts}))

def idle_state(agent_call):
    before=broker_state(agent_call)
    if before['active'] is not None or before['faulted']:raise RuntimeError('Broker not idle before the synthetic note')
    return before

def wait_for_generation(agent_call,background,clock,sleep,window):
    deadline=clock()+window
    while True:
        state=broker_state(agent_call)
        if state['active']=='notes' and state['received_frame']:return
        if background.done():
            raise RuntimeError('Synthetic note ended before cancellation could be exercised: '+json.dumps(note_summary(background.result())))
        if clock()>=deadline:raise RuntimeError('No active background generation observed')
        sleep(STATE_POLL)

def preempt_running_note(agent_call,note_call,clock,sleep,window):
    with ThreadPoolExecutor(max_workers=1) as pool:
        background=pool.submit(note_call)
        wait_for_generation(agent_call,background,clock,sleep,window)
        started=clock();chat=agent_call('/api/chat');elapsed=round(clock()-started,3)
        note=background.result(timeout=30)
    return chat,note,elapsed

def assert_preempted(chat,note,before,after,elapsed):
    if chat['http']!=200 or chat['value'].get('done') is not True:raise AssertionError('Chat did not complete after preemption')
    if note.get('code')!='background_preempted':raise AssertionError('Running note was not preempted: '+json.dumps(note_summary(note)))
    if not (after['preemptions']>before['preemptions'] and after['confirmed_recoveries']>before['confirmed_recoveries'] and not after['faulted']):
        raise AssertionError('Broker did not record a confirmed preemption and recovery')
    if elapsed>=30:raise AssertionError('Chat after preemption exceeded 30 seconds')

def exercise_preemption(agent_call,note_call,clock=time.monotonic,sleep=time.sleep,window=45):
    """Start the synthetic note only on a ready, idle broker, wait until it is
    generating, then send chat. Passes only if that running note is preempted."""
    readiness=ready_broker(agent_call,clock,sleep)
    before=idle_state(agent_call)
    chat,note,elapsed=preempt_running_note(agent_call,note_call,clock,sleep,window)
    after=broker_state(agent_call)
    assert_preempted(chat,note,before,after,elapsed)
    return {'readiness':readiness,'chat_after_preemption_seconds':elapsed,'chat':chat,'background_code':note.get('code'),
            'background':note_summary(note),'before':before,'after':after}

def verify(args):
    root=release.release_path(args.id);release.validate(root);profile=release.read(root/'deployment.json')
    if profile.get('broker',{}).get('protocol')!=2:raise SystemExit('Prepared scoped broker required')
    command="Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'scripts\\\\study-notes.py generate' } | Select-Object -ExpandProperty ProcessId"
    workers=subprocess.check_output(['powershell.exe','-NoProfile','-Command',command],text=True).strip()
    if workers:raise SystemExit('Pause owner notes writer before this explicit GPU test; no automatic stop performed')
    # No owner sources, credentials or prompts enter this report.
    prompts={}
    import ast
    tree=ast.parse((root/'scripts/study-notes.py').read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FACT_PROMPT' for t in node.targets):prompts['facts']=ast.literal_eval(node.value)
    job={'model':'larpus3.8:27b-q4','messages':[{'role':'system','content':prompts['facts']},{'role':'user','content':'DOCUMENT (synthetic fixture):\n'+DOCUMENT}],'num_predict':6000}
    jobfile=ROOT/'data/broker-live-job.json';jobfile.write_text(json.dumps(job)+'\n',encoding='utf8')
    agent=profile['agent_name'];notes=profile['notes']['container']
    def agent_call(path):return json.loads(release.podman('exec',agent,'python','-c',CLIENT,path,timeout=45))
    def note_call():
        with jobfile.open('rb') as f:
            output=release.wsl('/usr/bin/env','XDG_RUNTIME_DIR=/run/user/1000','/usr/bin/podman','exec','--interactive',notes,'python','-m','runtime.notes_worker',input_file=f,timeout=210)
        return json.loads(output)
    report={'schema':'larpus.broker-live/v1','kind':'owner-local-live','release':args.id,
            'source_fingerprint':profile['source_fingerprint'],'fixture_sha256':hashlib.sha256(DOCUMENT.encode()).hexdigest(),
            'limits':'Owner-run observations, not independent attestation. No reboot, real rollback, filled-context throughput or physical browser test.'}
    report['isolation']=json.loads(release.run(root,sys.executable,'-m','runtime.isolation','check'))
    report.update(exercise_preemption(agent_call,note_call))
    resumed=note_call();report['resumed_notes']={'ok':'ok' in resumed,'metrics':resumed.get('metrics',{})}
    assert 'ok' in resumed and resumed.get('metrics',{}).get('done_reason')=='stop'
    report['pass']=True;args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('id');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    try:verify(args)
    except Exception as exc:
        report={'schema':'larpus.broker-live/v1','kind':'owner-local-live','release':args.id,'pass':False,'failure_type':type(exc).__name__,'failure':str(exc)[:600],
                'limits':'Incomplete run; do not use as successful deployment evidence. Inspect local command output.'}
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
        raise
if __name__=='__main__':main()
