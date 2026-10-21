import importlib.util
import threading
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('verify_broker_live',Path(__file__).resolve().parents[1]/'scripts/verify-broker-live.py')
live=importlib.util.module_from_spec(spec);spec.loader.exec_module(live)

class FakeBroker:
    """Scheduler-shaped fake: a running note holds until chat preempts it."""
    def __init__(self,preempts=True,note_finishes_early=False,warm_codes=()):
        self.preempts=preempts;self.early=note_finishes_early;self.warm=list(warm_codes)
        self.active=None;self.frame=False;self.preemptions=0;self.recoveries=0;self.faulted=False
        self.started=threading.Event();self.release=threading.Event();self.chats=0
    def state(self):
        return {'active':self.active,'received_frame':self.frame,'faulted':self.faulted,
                'preemptions':self.preemptions,'confirmed_recoveries':self.recoveries}
    def agent_call(self,path):
        if path=='/broker/state':return {'http':200,'value':self.state()}
        if self.warm:
            return {'http':503,'value':{'done':None,'eval_count':None,'error':self.warm.pop(0)}}
        self.chats+=1
        if self.active=='notes' and self.preempts:
            self.preemptions+=1;self.recoveries+=1;self.release.set()
        elif self.active=='notes':self.release.set()
        return {'http':200,'value':{'done':True,'eval_count':3,'error':None}}
    def note_call(self):
        if self.early:return {'error':'broker-held','code':'cancellation_unconfirmed','http_status':503}
        self.active='notes';self.frame=True;self.started.set()
        self.release.wait(5)
        self.active=None;self.frame=False
        if self.preempts:return {'error':'broker-held','code':'background_preempted','http_status':409}
        return {'ok':'{}','metrics':{'done_reason':'stop'}}

class Clock:
    def __init__(self):self.now=0.
    def __call__(self):return self.now
    def sleep(self,seconds):self.now+=seconds

class VerifyBrokerLiveTests(unittest.TestCase):
    def run_check(self,broker):
        clock=Clock()
        def sleep(seconds):
            clock.sleep(seconds);broker.started.wait(.05)
        return live.exercise_preemption(broker.agent_call,broker.note_call,clock=clock,sleep=sleep)

    def test_running_note_is_preempted_and_passes(self):
        broker=FakeBroker()
        result=self.run_check(broker)
        self.assertEqual(result['background_code'],'background_preempted')
        self.assertEqual(result['after']['preemptions'],1)
        self.assertEqual(broker.chats,2)  # readiness chat, then the preempting chat

    def test_note_ending_before_cancellation_fails_with_its_outcome(self):
        with self.assertRaisesRegex(RuntimeError,'ended before cancellation.*cancellation_unconfirmed'):
            self.run_check(FakeBroker(note_finishes_early=True))

    def test_ignored_cancellation_fails(self):
        with self.assertRaisesRegex(AssertionError,'not preempted'):
            self.run_check(FakeBroker(preempts=False))

    def test_readiness_waits_out_unconfirmed_fence_then_proceeds(self):
        result=self.run_check(FakeBroker(warm_codes=['cancellation_unconfirmed']))
        self.assertEqual([a['http'] for a in result['readiness']],[503,200])

    def test_readiness_fails_on_other_refusal_or_fault(self):
        with self.assertRaisesRegex(RuntimeError,'readiness handshake failed'):
            self.run_check(FakeBroker(warm_codes=['inference_budget']))
        broker=FakeBroker(warm_codes=['cancellation_unconfirmed']);broker.faulted=True
        with self.assertRaisesRegex(RuntimeError,'readiness handshake failed'):
            self.run_check(broker)

    def test_note_summary_excludes_generated_text(self):
        self.assertNotIn('secret',str(live.note_summary({'ok':'secret note','metrics':{'done_reason':'stop'}})))

if __name__=='__main__':unittest.main()
