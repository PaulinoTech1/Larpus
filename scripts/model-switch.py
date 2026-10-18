"""Owner-only offline cache preparation, qualification and model recovery."""
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from runtime.model_backend import Backend
from runtime.model_selection import catalog
from runtime.model_switch import ModelSwitch
from scripts import releases
COPY=r"""import json,sys,hashlib,shutil,os,re
from pathlib import Path
j=json.load(sys.stdin);src=Path(j['source']);dst=Path('/home/larpus/models');rel=Path('manifests-v2/ollama.com/library/larpus3.8/27b-q4');raw=(src/rel).read_bytes();manifest=json.loads(raw);manifest_sha=hashlib.sha256(raw).hexdigest();assert manifest_sha=='9db1c57adceb2172ca2e0b183dcf12f2b295cf6117247095e97cc096ea38464f'
for spec in [manifest['config'],*manifest['layers']]:
 digest=spec['digest'];assert re.fullmatch('sha256:[a-f0-9]{64}',digest);name=digest.replace(':','-');source=src/'blobs'/name;target=dst/'blobs'/name;target.parent.mkdir(parents=True,exist_ok=True)
 h=hashlib.sha256();temp=target.with_suffix('.part')
 with source.open('rb') as f,temp.open('wb') as out:
  while buf:=f.read(8*1024*1024):h.update(buf);out.write(buf)
 assert h.hexdigest()==digest.split(':')[1];assert temp.stat().st_size==spec['size'];temp.replace(target)
assert any(x['digest']=='sha256:322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482' for x in manifest['layers'])
m=dst/'blobs'/('sha256-'+manifest_sha);m.write_bytes(raw)
metadata='sha256-322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482.json';(dst/'metadata').mkdir(exist_ok=True);shutil.copyfile(src/'metadata'/metadata,dst/'metadata'/metadata)
p=dst/rel;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.unlink(missing_ok=True);tmp.symlink_to('../../../../blobs/sha256-'+manifest_sha);tmp.replace(p);print(json.dumps({'copied_and_verified':True}))
"""
def prepare_cache():
 import subprocess
 b=Backend();source=releases.podman('volume','inspect','larpus-notes38-models','--format','{{.Mountpoint}}')
 with releases.exclusive():
  result=subprocess.run(['wsl.exe','-d','Larpus','-u','larpus','--exec','/usr/bin/python3','-c',COPY],input=json.dumps({'source':source}),capture_output=True,text=True,encoding='utf8',timeout=900)
  if result.returncode:raise RuntimeError('Verified offline model copy failed: '+result.stderr[-1200:])
  b.cache.parent.mkdir(parents=True,exist_ok=True);value=json.loads(b.cache.read_text()) if b.cache.exists() else {}
  value['larpus-3.8']={'sha256':catalog()['larpus-3.8']['weight_sha256'],'qualified_context':None};releases.write(b.cache,value);print(result.stdout)
def qualify():
 b=Backend();journal=b.root/'data/model-switch/qualification.json';paused=False
 with releases.exclusive():
  try:
   if b.notes_busy() or not b.idle():raise RuntimeError('Station busy; qualification did not start')
   releases.write(journal,{'phase':'starting','time':time.time()})
   releases.podman('stop','--time','15',b.profile['agent_name']);paused=True;b.unload('larpus-3.5')
   releases.write(journal,{'phase':'loading-3.8','time':time.time()});b.load('larpus-3.8');m=b.verify('larpus-3.8')
   value=json.loads(b.cache.read_text());value['larpus-3.8']['qualified_context']=131072;releases.write(b.cache,value)
   releases.write(journal,{'phase':'3.8-qualified','placement':m,'time':time.time()})
  finally:
   if paused:
    try:
     b.unload('larpus-3.8');b.load('larpus-3.5');m=b.verify('larpus-3.5')
     value=json.loads(b.cache.read_text());value['larpus-3.5']={'sha256':catalog()['larpus-3.5']['weight_sha256'],'qualified_context':131072};releases.write(b.cache,value)
     releases.write(journal,{'phase':'3.5-restored','placement':m,'time':time.time()})
    except Exception:
     releases.write(journal,{'phase':'recovery-required','time':time.time()});raise
    finally:releases.podman('start',b.profile['agent_name'])
 print('Qualified 3.8 at 131072 tokens; 3.5 restored with full GPU placement.')
def main():
 p=argparse.ArgumentParser();p.add_argument('operation',choices=('prepare-cache','qualify','status','recover'));a=p.parse_args()
 if a.operation=='prepare-cache':prepare_cache()
 elif a.operation=='qualify':qualify()
 elif a.operation=='status':print(json.dumps(Backend().read(),indent=2))
 else:
  control=ModelSwitch(start=lambda fn:None);recovered=control.recover();state=control.status();print(json.dumps(state,indent=2))
  return 0 if recovered and state['phase']=='ready' else 1
if __name__=='__main__':raise SystemExit(main())
