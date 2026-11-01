from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from scripts.recovery_backend import Backend, WindowsAdapter, receipt_token, _gpu_ready
from unittest.mock import Mock, patch
from scripts.recovery_policy import Policy
from scripts.recovery_state import Journal, StateError
from tests.test_recovery_policy import IDENTITY, observation, history

class FakeAdapter:
    def __init__(self):
        self.current=observation();self.launches=0;self.stops=0;self.publish_count=0
        self.on_lock=lambda:None;self.ready=True;self.alive=True;self.fail_publish=False
        self.new=replace(IDENTITY,pid=124);self.stopped=[];self.dead=set();self.claim_mode='owned'
        self.reused_identities=set();self.unreadable=set()
    @contextmanager
    def exclusive(self):
        self.on_lock();yield
    def selected_claim(self):
        return self.claim_mode,None if self.claim_mode=='absent' else self.current.identity
    def observe(self):return self.current
    def validate(self,expected):assert expected==IDENTITY
    def validate_running(self,expected):assert expected==self.new
    def launch(self):self.launches+=1;return self.new
    def wait_ready(self,new,started):return self.ready
    def publish(self,new):
        if self.fail_publish:raise OSError('synthetic publication failure')
        self.publish_count+=1
    def presence(self,new):
        if new in self.reused_identities:return 'reused'
        if new in self.unreadable:return 'unknown'
        if self.alive and new not in self.dead:return 'alive'
        return 'absent'
    def owned_alive(self,new):return self.presence(new)=='alive'
    def stop(self,new):self.stops+=1;self.stopped.append(new);self.dead.add(new)

class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.journal=Journal(self.root/'recovery',protect=lambda p,**kw:None)
        self.journal.write(history(dead_count=3))
        self.adapter=FakeAdapter();self.backend=Backend(self.root,adapter=self.adapter,jitter=lambda:0)

    def test_gateway_recovery_never_calls_general_start_or_starts_containers(self):
        result=self.backend.recover(IDENTITY,self.journal,Policy())
        self.assertEqual(result['reason'],'recovered')
        self.assertEqual(self.adapter.launches,1);self.assertEqual(self.adapter.stops,0)
        self.assertEqual(self.adapter.publish_count,1)
        self.assertEqual(len(self.journal.read().attempts),1)

    def test_lock_recheck_defeats_disable_selection_port_and_cutover_races(self):
        cases=[{'suppression':'deployment'},{'suppression':'drain'},
               {'process':'reused'},{'broker':'faulted'},{'broker':'busy'},
               {'identity':replace(IDENTITY,pid=999)},{'http':'responding'},
               {'dependencies':'failed'},{'process':'unknown'}]
        for change in cases:
            with self.subTest(change=change):
                self.adapter.current=observation(**change)
                self.assertNotEqual(self.backend.recover(IDENTITY,self.journal,Policy())['reason'],'recovered')
        self.adapter.current=observation()
        self.adapter.on_lock=lambda:self.journal.set_armed(False)
        self.backend.recover(IDENTITY,self.journal,Policy())
        self.assertEqual(self.adapter.launches,0)

    def test_persistence_failure_never_launches(self):
        self.journal.protect=lambda p,**kw:(_ for _ in ()).throw(OSError('ACL failure'))
        result=self.backend.recover(IDENTITY,self.journal,Policy())
        self.assertEqual(result['state'],'held');self.assertEqual(self.adapter.launches,0)

    def test_orphan_launch_reconciliation_and_cleanup_uncertainty_hold(self):
        self.adapter.fail_publish=True
        result=self.backend.recover(IDENTITY,self.journal,Policy())
        self.assertEqual(result['state'],'held');self.assertIsNotNone(self.journal.read().reservation)
        self.backend.recover(IDENTITY,self.journal,Policy())
        self.assertEqual(self.adapter.launches,1)

    def test_restart_reconciles_known_launch_without_launching_again(self):
        token=self.journal.reserve(IDENTITY,1000,0,started_monotonic=100)
        self.journal.record_launch(token,self.adapter.new)
        result=self.backend.recover(IDENTITY,self.journal,Policy())
        self.assertEqual(result['reason'],'recovered');self.assertEqual(self.adapter.launches,0)

    def test_reserved_launch_cannot_overwrite_a_new_selected_release(self):
        token=self.journal.reserve(IDENTITY,1000,0,started_monotonic=100)
        self.journal.record_launch(token,self.adapter.new)
        selected=replace(IDENTITY,release_id='d'*32)
        self.adapter.current=observation(identity=selected)
        self.backend.recover(selected,self.journal,Policy())
        self.assertEqual(self.adapter.publish_count,0)

    def test_readiness_failure_drains_only_new_process(self):
        self.adapter.ready=False
        result=self.backend.recover(IDENTITY,self.journal,Policy())
        self.assertEqual(result['reason'],'readiness-failed');self.assertEqual(self.adapter.stops,1)

    def test_release_runtime_errors_are_fixed_holds(self):
        self.adapter.launch=Mock(side_effect=RuntimeError('raw private output'))
        self.assertEqual(self.backend.recover(IDENTITY,self.journal,Policy())['reason'],'launch-uncertain')
        self.assertEqual(self.journal.read().state,'held')

    def test_unrecorded_launch_is_drained_and_uncertain_cleanup_holds(self):
        with patch.object(self.journal,'record_launch',side_effect=StateError('disk')):
            result=self.backend.recover(IDENTITY,self.journal,Policy())
        self.assertEqual(self.adapter.stops,1);self.assertEqual(result['reason'],'persist-failed')

    def test_drain_timeout_records_cleanup_uncertainty(self):
        self.adapter.ready=False;self.adapter.stop=Mock(side_effect=RuntimeError('drain'))
        result=self.backend.recover(IDENTITY,self.journal,Policy())
        self.assertEqual(result['reason'],'cleanup-uncertain')
        self.assertIsNotNone(self.journal.read().reservation)

    def test_locked_broker_fault_remains_held_after_fault_disappears(self):
        self.adapter.on_lock=lambda:setattr(self.adapter,'current',observation(broker='faulted'))
        self.assertEqual(self.backend.recover(IDENTITY,self.journal,Policy())['reason'],'broker-fault')
        self.adapter.on_lock=lambda:None;self.adapter.current=observation()
        self.backend.recover(IDENTITY,self.journal,Policy())
        self.assertEqual(self.adapter.launches,0)
        self.assertEqual(self.journal.read().state,'held')

    def test_reconciliation_revalidates_pins_and_drains_failed_readiness(self):
        token=self.journal.reserve(IDENTITY,1000,0,started_monotonic=100)
        self.journal.record_launch(token,self.adapter.new)
        self.adapter.validate_running=Mock(side_effect=ValueError('pin drift'))
        self.assertEqual(self.backend.recover(IDENTITY,self.journal,Policy())['state'],'held')
        self.assertEqual(self.adapter.publish_count,0)

    def test_reconciliation_failed_readiness_drains_owned_process(self):
        token=self.journal.reserve(IDENTITY,1000,0,started_monotonic=100)
        self.journal.record_launch(token,self.adapter.new);self.adapter.ready=False
        self.backend.recover(IDENTITY,self.journal,Policy())
        self.assertEqual(self.adapter.stops,1)

    def test_recent_health_from_other_generation_is_not_ready(self):
        value={'producer':{'version':1,'release_id':IDENTITY.release_id,'pid':IDENTITY.pid,'token':'c'*32,
                           'started':110.,'finished':120.},'checks':[{'name':n,'status':'pass'} for n in
                ('password','local_skills','approved_knowledge','input_filter','output_dlp','mcp_surface','models','model_gpu','egress_enforcement','voice')]}
        self.assertEqual(receipt_token(value,IDENTITY,100,now=130),'c'*32)
        for field,other in (('pid',124),('started',99.),('finished',140.),('release_id','d'*32),('token','bad')):
            with self.subTest(field=field):
                invalid={**value,'producer':{**value['producer'],field:other}}
                self.assertIsNone(receipt_token(invalid,IDENTITY,100,now=130))
        self.assertIsNone(receipt_token(value,IDENTITY,100,now=301))

    def test_stopped_wsl_observation_never_executes_a_distro_command(self):
        adapter=object.__new__(WindowsAdapter);adapter.release=Mock()
        adapter._wsl_running=lambda:False
        self.assertEqual(adapter._dependencies(self.root),('failed','unknown'))
        adapter.release.podman.assert_not_called()

    def test_reconciliation_names_a_faulted_broker(self):
        token=self.journal.reserve(IDENTITY,1000,0,started_monotonic=100)
        self.journal.record_launch(token,self.adapter.new)
        self.adapter.current=observation(broker='faulted',dependencies='failed')
        self.assertEqual(self.backend.recover(IDENTITY,self.journal,Policy())['reason'],'broker-fault')

    def test_container_inventory_accepts_one_leading_slash(self):
        import json
        adapter=object.__new__(WindowsAdapter);adapter.release=Mock()
        profile={'agent_name':'larpus-agent','agent_image':'a'*64,'model_image':'b'*64,
                 'broker':{'container':'larpus-broker','image':'c'*64},
                 'notes':{'container':'larpus-notes','image':'d'*64}}
        voice={'container':'larpus-voice','image':'e'*64}
        images={'larpus-agent':'a'*64,'larpus-model':'b'*64,'larpus-broker':'c'*64,'larpus-notes':'d'*64,'larpus-voice':'e'*64}
        items=[{'Name':'/'+name,'State':{'Running':True},'Image':image} for name,image in images.items()]
        adapter.release.podman.return_value=json.dumps(items)
        adapter._containers(profile,voice)

    def test_unrecorded_child_is_closed_on_its_process_handle(self):
        import subprocess
        import scripts.releases as releases
        child=Mock();child.pid=4242;child.poll.return_value=None;child.wait.return_value=0
        root=self.root;identifier='a'*32
        settings={'host':'127.0.0.1','subnet':'127.0.0.1/32','port':9}
        with patch.object(releases,'validate'),patch.object(releases,'release_path',return_value=root),patch.object(releases,'_startup_gate',return_value=root/'gate'),patch.object(releases,'STORE',root),patch.object(releases,'process',side_effect=subprocess.TimeoutExpired('wmi',15)),patch.object(releases.subprocess,'Popen',return_value=child):
            with self.assertRaises(subprocess.TimeoutExpired):releases.launch(identifier,settings)
        child.terminate.assert_called_once();child.kill.assert_not_called()

    def test_gpu_context_mismatch_is_not_ready(self):
        result={'tags':{'active_model':'larpus3.8:27b-q4'},'models':{'models':[
            {'name':'larpus3.8:27b-q4','size':100,'size_vram':100,'context_length':4096}]}}
        self.assertFalse(_gpu_ready(result))

