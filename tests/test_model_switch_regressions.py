import contextlib,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from runtime import model_selection as ms, inference
from runtime.model_backend import Backend
from runtime.broker_scheduler import Scheduler,Refused
from tests.test_model_switch import Backend as FakeBackend
from runtime.model_switch import ModelSwitch
class Regressions(unittest.TestCase):
 def test_stale_admission_never_probes_or_fences(self):
  fences=[];scheduler=Scheduler(lambda:fences.append(True) or True)
  from runtime import inference_broker as broker
  # Owner has just observed idle after publishing waiting; a stale request enters next.
  self.assertIsNone(scheduler.snapshot()['active'])
  state=dict(ms.initial(),phase='waiting',target_id='larpus-3.8')
  def reject():
   with patch.object(ms,'read_selection',return_value=state):broker.ensure_selected({'model':'qwen3.5:27b-q4_K_M','selection_enabled':True},{'model':'qwen3.5:27b-q4_K_M'})
  with self.assertRaises(Refused):
   with scheduler.slot('chat',1,admit=reject):self.fail('admitted stale request')
  self.assertEqual(fences,[]);self.assertIsNone(scheduler.snapshot()['active']);self.assertFalse(scheduler.faulted)
 def test_live_controller_observes_external_recovery(self):
  with tempfile.TemporaryDirectory() as d:
   b=FakeBackend();controller=ModelSwitch(b,d,start=lambda fn:None)
   b.state=dict(ms.initial(),phase='failed');controller.state=b.state.copy()
   b.state=dict(ms.initial(),active_id='larpus-3.8')
   self.assertEqual(controller.status()['phase'],'ready')
   self.assertEqual(controller.request('larpus-3.8')['active_id'],'larpus-3.8')
 def test_warmup_requires_completed_nonempty_content(self):
  b=Backend.__new__(Backend);b.identity=lambda i:None
  for response in ({'error':'bad'},{'done':False,'message':{'content':'ready'}},{'done':True,'message':{'content':' '}}):
   b.call=lambda *a:response
   with self.assertRaises(ValueError):b.load('larpus-3.8')
 def test_backend_verify_requires_exact_approved_gpu_and_context(self):
  from scripts.releases import ModelPlacementPending
  model={'name':'larpus3.8:27b-q4','size':10,'size_vram':10,'context_length':131072}
  b=Backend.__new__(Backend);b.call=lambda path:{'models':[model]};b.identity=lambda identifier:None
  self.assertEqual(b.verify('larpus-3.8'),model)
  b.call=lambda path:{'models':[{**model,'context_length':65536}]}
  with self.assertRaises(ValueError):b.verify('larpus-3.8')
  b.call=lambda path:{'models':[{**model,'size_vram':9}]}
  with self.assertRaises(ModelPlacementPending):b.verify('larpus-3.8')
  b.call=lambda path:{'models':[{'name':model['name'],'size':10,'size_vram':0,'context_length':131072}]}
  with self.assertRaises(ModelPlacementPending):b.verify('larpus-3.8')
 def test_health_retains_switch_gate(self):
  with patch.object(inference,'ollama',return_value={'models':[],'switching':True}),patch.object(inference,'gpu_placement',return_value='GPU'):
   self.assertTrue(inference.health()['switching'])
 def test_next_release_inherits_ready_selection(self):
  from scripts import releases
  with tempfile.TemporaryDirectory() as d:
   dest=Path(d);(dest/'config').mkdir();(dest/'config/inference-broker.json').write_text('{"selection_enabled":true}')
   profile={'model_selection':'/home/larpus/release-selection/old'};commands=[]
   def wsl(*args):
    commands.append(args[-1]);return json.dumps(dict(ms.initial(),active_id='larpus-3.8'))
   with patch.object(releases,'wsl',side_effect=wsl):releases.prepare_selection(dest,profile,'a'*32)
   self.assertIn('larpus-3.8',commands[-1])
 def test_cutover_refuses_stale_prepared_selection(self):
  from scripts import releases
  with tempfile.TemporaryDirectory() as d:
   new=Path(d)/'new';old=Path(d)/'old';new.mkdir();old.mkdir()
   for path,source in ((new,'new-source'),(old,'old-source')):(path/'deployment.json').write_text(json.dumps({'model_selection':source}))
   def state(*args):return json.dumps(dict(ms.initial(),active_id='larpus-3.8' if 'old-source' in args[-1] else 'larpus-3.5'))
   with patch.object(releases,'wsl',side_effect=state):
    with self.assertRaises(ValueError):releases.check_cutover_selection(new,old)
 def test_note_producers_survive_duplication_and_publication(self):
  spec=importlib.util.spec_from_file_location('study',Path(__file__).resolve().parents[1]/'scripts/study-notes.py');study=importlib.util.module_from_spec(spec);spec.loader.exec_module(study)
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'knowledge').mkdir()
   with patch.object(study,'BUILD',root/'build.sqlite'),patch.object(study,'ROOT',root):
    with contextlib.closing(study.build_db()) as db:
     row=('k','s','title','url','loc','fact','','fact text','quote','context')
     study.store_notes(db,[row],'qwen3.5:27b-q4_K_M');study.store_notes(db,[row],'larpus3.8:27b-q4');db.commit()
     study.duplicate_notes(db,'k','copy','s','title','url','loc2')
    study.publish()
    import sqlite3
    with contextlib.closing(sqlite3.connect(root/'knowledge/notes.sqlite')) as db:
     models=[r[0] for r in db.execute('SELECT p.model FROM notes n JOIN note_producers p ON n.rowid=p.note_rowid ORDER BY n.rowid')]
     self.assertEqual(models,['qwen3.5:27b-q4_K_M','larpus3.8:27b-q4']*2)
