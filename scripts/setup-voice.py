"""Explicit public-artifact preparation or offline deployment of the CPU voice worker."""
import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime.agents import ROOT
from runtime.isolation import wsl_command

BASE='docker.io/library/python@sha256:2ed6491b93cd49272ee6de2b5a38440c3448360322c089fc23e370722d74179d'
STUDIO='06c6e077f0fc35149efefc3561e9be5ae835d916'
parser=argparse.ArgumentParser()
parser.add_argument('operation',choices=('prepare','deploy'))
args=parser.parse_args()

def wsl(*args,**kwargs):
    return subprocess.run(wsl_command(*args),check=True,**kwargs)

if args.operation=='prepare':
    # This is the sole online phase, not a request-time fallback.
    checkout=ROOT/'vendor/VoiceStudio'
    if not checkout.exists():
        subprocess.run(['git','clone','https://github.com/debpalash/VoiceStudio.git',str(checkout)],check=True)
    actual=subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD'],text=True).strip()
    if actual!=STUDIO:
        raise SystemExit('VoiceStudio checkout is not the pinned commit; inspect/checkout '+STUDIO)
    wsl('/bin/mkdir','-p','/home/larpus/voice-build/wheels','/home/larpus/voice-models')
    code="""import subprocess,urllib.request
subprocess.run(['python','-m','pip','download','--dest','/build/wheels','faster-whisper==1.2.1','piper-tts==1.8.0'],check=True)
subprocess.run(['python','-m','pip','install','--no-index','--find-links=/build/wheels','faster-whisper==1.2.1','piper-tts==1.8.0'],check=True)
from huggingface_hub import snapshot_download
snapshot_download('Systran/faster-whisper-small.en',local_dir='/models/whisper-small.en',allow_patterns=['*.json','*.bin','*.txt'])
base='https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/'
for name in ['en_GB-alan-medium.onnx','en_GB-alan-medium.onnx.json','MODEL_CARD']:
 urllib.request.urlretrieve(base+name,'/models/'+name)
"""
    wsl('podman','run','--rm','--interactive','--name','larpus-voice-prepare','--volume','/home/larpus/voice-build:/build','--volume','/home/larpus/voice-models:/models',BASE,'python','-',input=code.encode())
    print('Online preparation completed. Run deploy to seal offline execution.')
else:
    checkout=ROOT/'vendor/VoiceStudio'
    actual=subprocess.check_output(['git','-C',str(checkout),'rev-parse','HEAD'],text=True).strip()
    if actual!=STUDIO:
        raise SystemExit('VoiceStudio source pin mismatch')
    original=subprocess.check_output(['git','-C',str(checkout),'show',STUDIO+':backend/engines/_asr_sidecar/main.py'])
    if original.replace(b'\r\n',b'\n')!=(checkout/'backend/engines/_asr_sidecar/main.py').read_bytes().replace(b'\r\n',b'\n'):
        raise SystemExit('VoiceStudio adapter changed from pinned source')
    archive=ROOT/'data/voice-source.tar'
    archive.parent.mkdir(exist_ok=True)
    with tarfile.open(archive,'w') as tar:
        for source,name in [('runtime/voice_worker.py','voice_worker.py'),('vendor/VoiceStudio/backend/engines/_asr_sidecar/main.py','asr.py'),('vendor/VoiceStudio/LICENSE','VOICESTUDIO-LICENSE'),('deploy/voice/Containerfile','Containerfile')]:
            tar.add(ROOT/source,arcname=name)
    with archive.open('rb') as source:
        wsl('/bin/tar','-xf','-','-C','/home/larpus/voice-build',stdin=source)
    # Refuse automatic replacement; existing worker must be explicitly stopped/reviewed.
    exists=subprocess.run(wsl_command('podman','container','exists','larpus-voice')).returncode
    if exists==0:
        raise SystemExit('Existing voice worker preserved. Stop/remove only larpus-voice before redeploying.')
    if exists!=1:
        raise SystemExit('Cannot inspect voice deployment')
    wsl('podman','build','--pull=never','--network=none','--build-arg','BASE_IMAGE='+BASE,'--tag','localhost/larpus-voice:sealed','/home/larpus/voice-build')
    image=subprocess.check_output(wsl_command('podman','image','inspect','localhost/larpus-voice:sealed','--format','{{.Id}}'),text=True).strip()
    wsl('podman','run','--detach','--pull=never','--name','larpus-voice','--network=none','--read-only','--read-only-tmpfs=false','--user=1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=128','--memory=4g','--cpus=8','--log-driver=none','--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=128m','--mount=type=bind,src=/home/larpus/voice-models,dst=/models,ro',image)
    profile={'version':1,'image':image,'voicestudio_commit':STUDIO,'worker_sha256':hashlib.sha256((ROOT/'runtime/voice_worker.py').read_bytes()).hexdigest(),'tts':'en_GB-alan-medium','stt':'small.en'}
    (ROOT/'data/voice-deployment.json').write_text(json.dumps(profile,indent=2)+'\n',encoding='utf-8')
    # Record exact cached artifact hashes locally; floating upstream revisions can change.
    code="import pathlib,hashlib,json; r=pathlib.Path('/home/larpus/voice-models');print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*') if p.is_file() and '.cache' not in p.parts}))"
    hashes=subprocess.check_output(wsl_command('python3','-c',code))
    (ROOT/'data/voice-model-hashes.json').write_bytes(hashes)
    print('Voice image sealed and profile saved. Run the main isolation check before starting the gateway.')
