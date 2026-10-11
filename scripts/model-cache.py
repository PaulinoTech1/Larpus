"""Owner-only cache maintenance; never exposed as an agent or HTTP tool."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('owner_releases',ROOT/'scripts/releases.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
STATE=ROOT/'data/model-cache'
CANDIDATE='larpus-model-cache-candidate'
# Target context comes from the reviewed model configuration, not a hardcoded value.
TARGET=json.loads((ROOT/'config/models.json').read_text(encoding='utf-8'))['num_ctx']
BACKUP='larpus-model-cache-previous'

def create(profile,cache):
    driver=profile['gpu_driver'];image=profile['model_image']
    if not re.fullmatch(r'[a-f0-9]{64}',image) or not re.fullmatch(r'/usr/lib/wsl/drivers/nv_[a-z0-9]+\.inf_amd64_[a-f0-9]{16}',driver):raise ValueError('Invalid cached image/driver pin')
    args=['create','--pull=never','--name',CANDIDATE,'--pod','larpus-offline','--read-only','--read-only-tmpfs=false','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=256','--memory=32g','--memory-swap=32g','--cpus=16','--log-driver=none','--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=1g','--device=/dev/dxg','--mount=type=bind,src=/usr/lib/wsl/lib,dst=/usr/lib/wsl/lib,ro','--mount=type=bind,src='+driver+',dst='+driver+',ro','--mount=type=bind,src=/home/larpus/models,dst=/models,ro']
    env={'HOME':'/tmp','OLLAMA_HOST':'127.0.0.1:11434','OLLAMA_MODELS':'/models','OLLAMA_NO_CLOUD':'1','OLLAMA_NOPRUNE':'1','LD_LIBRARY_PATH':'/usr/lib/wsl/lib','OLLAMA_NUM_PARALLEL':'1','OLLAMA_FLASH_ATTENTION':'1','OLLAMA_KV_CACHE_TYPE':cache}
    for key,value in env.items():args+=['--env',key+'='+value]
    r.podman(*args,'--entrypoint=/bin/ollama',image,'serve')

def probe(root,context):
    # Fixed synthetic owner probe through the sealed agent's loopback adapter.
    code="""import json,time
from runtime.local_ollama import ollama
from runtime.agents import load_personas
model=load_personas()['home-assistant']['model'];start=time.monotonic()
reply=ollama('/api/chat',{'model':model,'messages':[{'role':'user','content':'Explain AES-GCM nonce uniqueness in three short sentences.'}],'stream':False,'think':False,'keep_alive':-1,'options':{'num_ctx':CONTEXT,'num_predict':100,'num_gpu':99,'temperature':0}},timeout=120)
item=next(m for m in ollama('/api/ps')['models'] if m['name']==model)
seconds=reply.get('eval_duration',0)/1e9
print(json.dumps({'context':item.get('context_length'),'full_gpu':item['size_vram']>=item['size'],'size':item['size'],'vram':item['size_vram'],'elapsed_seconds':round(time.monotonic()-start,3),'prompt_tokens':reply.get('prompt_eval_count'),'output_tokens':reply.get('eval_count'),'tokens_per_second':round(reply.get('eval_count',0)/seconds,2) if seconds else None,'content':reply['message']['content']}))
""".replace('CONTEXT',str(context))
    profile=r.read(root/'deployment.json')
    for attempt in range(10):
        try:
            r.podman('exec',profile.get('agent_name','larpus-agent'),'python','-c',"from runtime.local_ollama import ollama;ollama('/api/tags',timeout=2)")
            break
        except RuntimeError:
            if attempt==9:raise
            time.sleep(.5)
    result=json.loads(r.podman('exec',profile.get('agent_name','larpus-agent'),'python','-c',code))
    if not result['full_gpu'] or result['context']!=context:raise ValueError('Target context is not fully GPU-resident')
    return result

def apply(cache):
    STATE.mkdir(parents=True,exist_ok=True)
    if (STATE/'pending.json').exists():raise ValueError('Pending maintenance; recover before another change')
    active=r.read(r.STORE/'active.json');root=r.release_path(active['id']);r.validate(root)
    profile=r.read(root/'deployment.json')
    # Validate the live boundary using frozen production sources before cloning.
    r.run(root,sys.executable,'-c','from runtime.isolation import preflight;preflight()')
    before=json.loads(r.podman('inspect','larpus-model'))[0]
    baseline=probe(root,4096)
    r.write(STATE/'baseline.json',baseline)
    create(profile,cache)  # Stopped candidate; production has not been drained.
    journal={'version':1,'active':active,'before':before,'profile':profile,'cache':cache,'phase':'prepared'}
    r.write(STATE/'pending.json',journal)
    stopped=False;renamed=False;switched=False;new=None
    try:
        print('Draining gateway for authorised cache maintenance; CPU voice stays running.',flush=True)
        r.stop(active);stopped=True
        r.podman('stop','--time','15','larpus-model')
        r.podman('rename','larpus-model',BACKUP);renamed=True
        r.podman('rename',CANDIDATE,'larpus-model');switched=True
        journal['phase']='switched';r.write(STATE/'pending.json',journal)
        r.podman('start','larpus-model')
        measured=[probe(root,4096),probe(root,TARGET),probe(root,TARGET)]
        swap_max=r.podman('exec','larpus-model','/bin/cat','/sys/fs/cgroup/memory.swap.max')
        swap_current=r.podman('exec','larpus-model','/bin/cat','/sys/fs/cgroup/memory.swap.current')
        if swap_max!='0' or swap_current!='0':raise ValueError('Model cgroup swap is not disabled')
        # The old HUD still explicitly requests 4k until its prepared update.
        probe(root,4096)
        new=r.launch(active['id'],active)
        journal['candidate_gateway']=new;r.write(STATE/'pending.json',journal)
        r.ready(new);r.write(r.STORE/'active.json',new)
        receipt={**journal,'phase':'complete','baseline':baseline,'measurements':measured,'swap_max':swap_max,'swap_current':swap_current,'scope':f'Short synthetic allocation/generation probes only; filled {TARGET}-token context NOT verified.'}
        r.write(STATE/'latest.json',receipt)
        r.podman('rm',BACKUP)  # Stopped ephemeral container; read-only weights persist.
        (STATE/'pending.json').unlink()
        print(json.dumps({'cache':cache,'measurements':measured,'swap_max':swap_max,'scope':receipt['scope']},indent=2),flush=True)
    except Exception:
        if new:r.stop(new)
        if switched:
            r.podman('stop','--time','15','larpus-model');r.podman('rm','larpus-model')
        if renamed:r.podman('rename',BACKUP,'larpus-model')
        r.podman('start','larpus-model')
        probe(root,4096)
        if stopped:
            if r.running(active):(root/'release-state/drain').unlink(missing_ok=True)
            else:
                restored=r.launch(active['id'],active);r.ready(restored);r.write(r.STORE/'active.json',restored)
        (STATE/'pending.json').unlink(missing_ok=True)
        raise

def recover():
    journal=r.read(STATE/'pending.json');old=journal['active'];root=r.release_path(old['id'])
    current=r.read(r.STORE/'active.json')
    if current!=old and r.running(current):
        r.ready(current)
        names=set(r.podman('ps','-a','--format','{{.Names}}').splitlines())
        if BACKUP in names:r.podman('rm',BACKUP)
        (STATE/'pending.json').unlink();return
    if journal.get('candidate_gateway') and r.running(journal['candidate_gateway']):r.stop(journal['candidate_gateway'])
    names=set(r.podman('ps','-a','--format','{{.Names}}').splitlines())
    if BACKUP in names:
        if 'larpus-model' in names:
            r.podman('stop','--time','15','larpus-model');r.podman('rm','larpus-model')
        r.podman('rename',BACKUP,'larpus-model')
    r.podman('start','larpus-model');probe(root,4096)
    if r.running(old):(root/'release-state/drain').unlink(missing_ok=True);r.ready(old)
    else:
        restored=r.launch(old['id'],old);r.ready(restored);r.write(r.STORE/'active.json',restored)
    (STATE/'pending.json').unlink()
    print('Recovered previous model and active gateway.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('operation',choices=('apply','recover'));parser.add_argument('--cache',choices=('q4_0','q8_0'),default='q4_0');args=parser.parse_args()
    with r.exclusive():
        if args.operation=='recover':recover()
        else:apply(args.cache)
