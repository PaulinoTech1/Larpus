import contextlib,tempfile,unittest
from pathlib import Path
from runtime.model_switch import ModelSwitch
from runtime import model_selection as ms
class Backend:
 def __init__(self):self.state=ms.initial();self.events=[];self.busy=False;self.fail=set();self.inflight=0
 def read(self):return dict(self.state)
 def publish(self,s):self.state=dict(s);self.events.append(s['phase'])
 def exclusive(self):return contextlib.nullcontext()
 def notes_busy(self):return self.busy
 def available(self,i):return True
 def idle(self):self.events.append('idle');return not self.inflight
 def unload(self,i):self.events.append('unload:'+i)
 def load(self,i):
  self.events.append('load:'+i)
  if i in self.fail:raise RuntimeError('failed to fit')
 def verify(self,i):self.events.append('verify:'+i)
class SwitchTests(unittest.TestCase):
 def setUp(self):
  self.d=tempfile.TemporaryDirectory();self.addCleanup(self.d.cleanup);self.b=Backend();self.c=ModelSwitch(self.b,Path(self.d.name),start=lambda fn:None)
 def test_switch_orders_unload_load_verify_before_ready(self):
  self.c.request('larpus-3.8');self.c.run('larpus-3.8');self.assertEqual(self.b.state['active_id'],'larpus-3.8');self.assertEqual(self.b.state['phase'],'ready')
  self.assertLess(self.b.events.index('unload:larpus-3.5'),self.b.events.index('load:larpus-3.8'));self.assertLess(self.b.events.index('verify:larpus-3.8'),len(self.b.events)-1)
 def test_busy_notes_and_duplicate_request_rejected(self):
  self.b.busy=True
  with self.assertRaises(RuntimeError):self.c.request('larpus-3.8')
  self.b.busy=False;self.c.request('larpus-3.8')
  with self.assertRaises(RuntimeError):self.c.request('larpus-3.5')
 def test_same_model_noop_and_arbitrary_model_rejected(self):
  self.assertEqual(self.c.request('larpus-3.5')['phase'],'ready');self.assertEqual(self.b.events,[])
  with self.assertRaises(ValueError):self.c.request('arbitrary:cloud')
 def test_failed_target_restores_previous_and_reports_error(self):
  self.b.fail={'larpus-3.8'};self.c.request('larpus-3.8');self.c.run('larpus-3.8');self.assertEqual(self.b.state['phase'],'ready');self.assertEqual(self.b.state['active_id'],'larpus-3.5');self.assertIn('restored',self.b.state['error'])
 def test_failed_restoration_remains_failed_and_durable(self):
  self.b.fail={'larpus-3.8','larpus-3.5'};self.c.request('larpus-3.8');self.c.run('larpus-3.8');self.assertEqual(self.b.state['phase'],'failed');self.assertTrue((Path(self.d.name)/'state.json').exists())
 def test_recovery_after_restart_restores_prior_selection(self):
  self.c.request('larpus-3.8');self.b.state=self.c.state.copy();new=ModelSwitch(self.b,Path(self.d.name),start=lambda fn:None);new.recover();self.assertEqual(self.b.state['phase'],'ready');self.assertIn('load:larpus-3.5',self.b.events)
 def test_current_work_must_finish_before_unload(self):
  self.b.inflight=1;self.c.wait_seconds=0;self.c.request('larpus-3.8');self.c.run('larpus-3.8');self.assertNotIn('unload:larpus-3.5',self.b.events);self.assertEqual(self.b.state['active_id'],'larpus-3.5')

 def test_busy_owner_lock_does_not_mutate_live_broker(self):
  def unavailable():raise OSError('locked')
  self.b.exclusive=unavailable;self.c.request('larpus-3.8');self.c.run('larpus-3.8');self.assertEqual(self.b.state['phase'],'ready');self.assertEqual(self.b.events,[])
