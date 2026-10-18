"""Owner-side model lifecycle; never a model/MCP capability."""
import json,threading,time,uuid
from pathlib import Path
from runtime import model_selection as selection
from runtime.diagnostics import report,describe
class ModelSwitch:
 def __init__(self,backend=None,directory=None,start=None):
  if backend is None:
   from runtime.model_backend import Backend
   backend=Backend()
  self.backend=backend;self.directory=Path(directory or backend.directory);self.lock=threading.RLock();self.wait_seconds=120;self.pending=False
  self.start=start or (lambda fn:threading.Thread(target=fn,daemon=True,name='model-switch').start())
  self.state=selection.validate(backend.read());self.directory.mkdir(parents=True,exist_ok=True)
  if selection.is_switching(self.state):self.start(self.recover)
 def persist(self,publish=True,**changes):
  self.state=dict(self.state,**changes);selection.validate(self.state)
  if publish:self.backend.publish(self.state)
  temp=self.directory/'state.tmp';temp.write_text(json.dumps(self.state),encoding='utf8');temp.replace(self.directory/'state.json')
 def refresh(self):
  if not self.pending:self.state=selection.validate(self.backend.read())
 def status(self):
  with self.lock:self.refresh()
  return dict(self.state,models=[dict(id=k,**v,available=self.backend.available(k)) for k,v in selection.catalog().items()])
 def request(self,identifier):
  selection.model(identifier)
  with self.lock:
   self.refresh()
   if selection.is_switching(self.state):raise RuntimeError('A model switch is already in progress')
   if self.backend.notes_busy():raise RuntimeError('GPU notes maintenance is active; finish or recover it first')
   if identifier==self.state['active_id']:return self.status()
   if not self.backend.available(identifier):raise ValueError('Model is not prepared locally')
   self.pending=True
   self.persist(publish=False,target_id=identifier,phase='waiting',operation_id=uuid.uuid4().hex,error=None)
   self.start(lambda:self.run(identifier))
   return self.status()
 def wait_idle(self):
  deadline=time.monotonic()+self.wait_seconds
  while not self.backend.idle():
   if time.monotonic()>=deadline:raise TimeoutError('Current inference did not finish')
   time.sleep(1)
 def finish(self,identifier,error=None):
  self.persist(active_id=identifier,target_id=None,phase='ready',error=error)
 def restore(self,previous,target):
  self.persist(phase='restoring')
  if target:self.backend.unload(target)
  self.backend.load(previous);self.backend.verify(previous)
  self.finish(previous,'Requested model failed; previous model restored.')
 def diagnose(self,exc):
  identifier=report('LARP-MODEL-MAINTENANCE',exc)
  details={key:self.state[key] for key in ('phase','operation_id','active_id','target_id')}
  details.update(error_id=identifier,category=describe(exc)['reason'])
  try:
   temp=self.directory/'diagnostic.tmp';temp.write_text(json.dumps(details),encoding='utf8');temp.replace(self.directory/'diagnostic.json')
  except OSError:pass  # The stderr record survives; diagnostic storage cannot block restoration.
  return identifier
 def failed(self,identifier):self.persist(phase='failed',error='Model switch and recovery failed. Run owner recovery. / diagnostic '+identifier)
 def run(self,identifier):
  previous=self.state['active_id'];unloaded=False;acquired=False
  try:
   with self.backend.exclusive():
    acquired=True
    try:
     if self.backend.notes_busy():raise RuntimeError('GPU notes maintenance is active')
     self.persist(phase='waiting');self.wait_idle();self.persist(phase='unloading');unloaded=True;self.backend.unload(previous)
     self.persist(phase='loading');self.backend.load(identifier);self.persist(phase='verifying');self.backend.verify(identifier);self.finish(identifier)
    except Exception as exc:
     diagnostic=self.diagnose(exc)
     if unloaded:
      self.restore(previous,identifier);self.persist(error='Requested model failed; previous model restored. / diagnostic '+diagnostic)
     else:self.finish(previous,'Switch could not begin; previous model retained. / diagnostic '+diagnostic)
  except Exception as exc:
   diagnostic=self.diagnose(exc)
   if acquired:self.failed(diagnostic)
   else:
    self.state=self.backend.read();self.persist(publish=False,error='Owner maintenance is busy; selection unchanged. / diagnostic '+diagnostic)
  finally:self.pending=False
 def recover(self):
  self.pending=True;acquired=False;success=False
  try:
   with self.backend.exclusive():
    acquired=True;self.restore(self.state['active_id'],self.state['target_id']);success=True
  except Exception as exc:
   diagnostic=self.diagnose(exc)
   if acquired:self.failed(diagnostic)
  finally:self.pending=False
  return success
