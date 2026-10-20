"""Windows owner adapter with fixed WSL commands; excluded from MCP tools."""
import json,subprocess,time
from pathlib import Path
from runtime import model_selection as selection
from runtime.isolation import wsl_command
from scripts import releases
CLIENT="""import json,sys,urllib.request
j=json.load(sys.stdin);r=urllib.request.Request('http://127.0.0.1:11434'+j['path'],json.dumps(j['body']).encode() if 'body' in j else None,{'Content-Type':'application/json'})
with urllib.request.urlopen(r,timeout=j['timeout']) as v:print(v.read(2000000).decode())
"""
class Backend:
 def __init__(self):
  root=selection.ROOT;pointer=json.loads((root/'data/releases/active.json').read_text(encoding='utf8'))
  self.root=root;self.release=root if (root/'deployment.json').exists() else root/'data/releases'/pointer['id']
  self.profile=json.loads((self.release/'deployment.json').read_text(encoding='utf8'))
  self.directory=root/'data/model-switch'/self.release.name
  self.source=self.profile.get('model_selection')
  self.cache=root/'data/model-switch/cache.json'
 def exclusive(self):return releases.exclusive()
 def linux(self,code,value=None):
  result=subprocess.run(['wsl.exe','-d','Larpus','-u','larpus','--exec','/usr/bin/python3','-c',code],input=json.dumps(value) if value is not None else None,capture_output=True,text=True,encoding='utf8',timeout=30)
  if result.returncode:raise RuntimeError('Owner selection state unavailable') from subprocess.CalledProcessError(result.returncode,['fixed-owner-state-operation'])
  return json.loads(result.stdout) if result.stdout.strip() else None
 def read(self):
  if not self.source:raise ValueError('Model selection is not prepared in this release')
  return selection.validate(self.linux('import json;print(open('+repr(self.source+'/state.json')+').read())'))
 def publish(self,state):
  selection.validate(state)
  self.linux('import json,sys,os;from pathlib import Path;p=Path('+repr(self.source+'/state.json')+');t=p.with_suffix(".tmp");t.write_text(json.dumps(json.load(sys.stdin)));os.chmod(t,0o644);t.replace(p)',state)
 def notes_busy(self):
  p=self.root/'data/notes38-cyber-week/gpu-maintenance.json'
  return p.exists() and json.loads(p.read_text())['phase']!='chat-restored'
 def available(self,identifier):
  entry=selection.model(identifier)
  if not self.cache.exists():return False
  cached=json.loads(self.cache.read_text()).get(identifier,{})
  return cached.get('sha256')==entry['weight_sha256'] and cached.get('qualified_context')==entry['context']
 def call(self,path,body=None,timeout=300,process_timeout=None):
  if type(timeout) is not int or not 1<=timeout<=300:raise ValueError('Invalid fixed local model timeout')
  args=['run','-i','--rm','--pull=never','--pod=larpus-offline','--read-only','--read-only-tmpfs=false','--user=1000:1000','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=32','--memory=256m','--cpus=1','--log-driver=none','--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=32m','--entrypoint=python',self.profile['agent_image'],'-c',CLIENT]
  value={'path':path,'timeout':timeout}
  if body is not None:value['body']=body
  result=subprocess.run(wsl_command('podman',*args),input=json.dumps(value),capture_output=True,text=True,encoding='utf8',timeout=330 if process_timeout is None else process_timeout)
  if result.returncode:raise RuntimeError('Fixed local model operation failed') from subprocess.CalledProcessError(result.returncode,['fixed-local-model-operation'])
  return json.loads(result.stdout)
 def idle(self):
  code="import http.client,socket,json;c=http.client.HTTPConnection('localhost',timeout=5);c.sock=socket.socket(socket.AF_UNIX);c.sock.connect('/run/larpus-broker/inference.sock');c.request('GET','/broker/state');r=c.getresponse();print(r.read().decode())"
  result=releases.podman('exec',self.profile['agent_name'],'python','-c',code)
  v=json.loads(result);return v['active'] is None and v['waiting_chat']==0
 def unload(self,identifier):self.call('/api/generate',{'model':selection.model(identifier)['tag'],'keep_alive':0})
 def identity(self,identifier):
  e=selection.model(identifier);show=self.call('/api/show',{'model':e['tag']})
  if not isinstance(show,dict) or not isinstance(show.get('modelfile'),str) or e['weight_sha256'] not in show['modelfile']:raise ValueError('Model weight identity differs')
 def load(self,identifier):
  self.identity(identifier);e=selection.model(identifier)
  reply=self.call('/api/chat',{'model':e['tag'],'messages':[{'role':'user','content':'Reply with ready.'}],'stream':False,'think':False,'keep_alive':-1,'options':{'num_gpu':99,'num_ctx':e['context'],'num_predict':16,'temperature':0}})
  if not isinstance(reply,dict) or reply.get('error') or reply.get('done') is not True or not isinstance(reply.get('message'),dict):raise ValueError('Warm-up did not complete')
  content=reply['message'].get('content')
  if not isinstance(content,str) or not content.strip():raise ValueError('Warm-up produced no text')
 def _loaded_model(self,entry):
  status=self.call('/api/ps')
  if not isinstance(status,dict) or not isinstance(status.get('models'),list):raise ValueError('Invalid model process status')
  matches=[x for x in status['models'] if isinstance(x,dict) and x.get('name')==entry['tag']]
  if len(matches)!=1:raise ValueError('Selected model is not loaded exactly once')
  return matches[0]
 def _verify_placement(self,model,entry):
  fields=('size','size_vram','context_length')
  if any(type(model.get(field)) is not int for field in fields):raise ValueError('Invalid model placement report')
  if model['size']<=0 or model['size_vram']<model['size']:raise releases.ModelPlacementPending('Selected model is not yet fully resident on the GPU')
  if model['context_length']!=entry['context']:raise ValueError('Model context differs from the approved selection')
 def verify(self,identifier):
  entry=selection.model(identifier);model=self._loaded_model(entry);self._verify_placement(model,entry);self.identity(identifier)
  return model
