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
 from runtime.knowledge import EVIDENCE_PROMPT,NO_EVIDENCE_PROMPT
 p=load_personas()['home-assistant'];m=messages_for(p,[{'role':'user','content':'Hello'}]);m[0]['content']+=EVIDENCE_PROMPT+NO_EVIDENCE_PROMPT
 body={'model':p['model'],'messages':m,'stream':False,'think':False,'keep_alive':-1,'options':{'temperature':p['temperature'],'num_ctx':131072,'num_predict':32,'num_gpu':99}}
 c.request('POST',path,json.dumps(body))
else:c.request('GET',path)
r=c.getresponse();v=json.loads(r.read());c.close()
if path=='/api/chat':v={'done':v.get('done'),'eval_count':v.get('eval_count'),'error':v.get('code')}
print(json.dumps({'http':r.status,'value':v}))
'''

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
    job={'model':'qwen3.5:27b-q4_K_M','messages':[{'role':'system','content':prompts['facts']},{'role':'user','content':'DOCUMENT (synthetic fixture):\n'+DOCUMENT}],'num_predict':6000}
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
    before=agent_call('/broker/state')['value']
    with ThreadPoolExecutor(max_workers=1) as pool:
        background=pool.submit(note_call);deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            state=agent_call('/broker/state')['value']
            if state['active']=='notes' and state['received_frame']:break
            if background.done():raise RuntimeError('Synthetic note finished before cancellation could be exercised')
            time.sleep(.25)
        else:raise RuntimeError('No active background generation observed')
        started=time.monotonic();chat=agent_call('/api/chat');report['chat_after_preemption_seconds']=round(time.monotonic()-started,3)
        note=background.result(timeout=30)
    after=agent_call('/broker/state')['value']
    report.update(chat=chat,background_code=note.get('code'),before=before,after=after)
    assert chat['http']==200 and chat['value'].get('done') is True
    assert note.get('code')=='background_preempted'
    assert after['preemptions']>before['preemptions'] and after['confirmed_recoveries']>before['confirmed_recoveries'] and not after['faulted']
    assert report['chat_after_preemption_seconds']<30
    resumed=note_call();report['resumed_notes']={'ok':'ok' in resumed,'metrics':resumed.get('metrics',{})}
    assert 'ok' in resumed and resumed.get('metrics',{}).get('done_reason')=='stop'
    report['pass']=True;args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('id');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    try:verify(args)
    except Exception as exc:
        report={'schema':'larpus.broker-live/v1','kind':'owner-local-live','release':args.id,'pass':False,'failure_type':type(exc).__name__,
                'limits':'Incomplete run; do not use as successful deployment evidence. Inspect local command output.'}
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
        raise
if __name__=='__main__':main()
