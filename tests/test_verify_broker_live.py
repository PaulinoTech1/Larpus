import importlib.util
import threading
import unittest
from pathlib import Path

from runtime.broker_scheduler import LIMITS

spec=importlib.util.spec_from_file_location('verify_broker_live',Path(__file__).resolve().parents[1]/'scripts/verify-broker-live.py')
live=importlib.util.module_from_spec(spec);spec.loader.exec_module(live)
HELD={'inference_budget':429,'queue_full':429}

class FakeBroker:
    """Scheduler-shaped fake: a running note holds until chat preempts it."""
    def __init__(self,preempts=True,note_finishes_early=False,warm_codes=(),resident_after=0,clock=None):
        self.preempts=preempts;self.early=note_finishes_early;self.warm=list(warm_codes)
        self.active=None;self.frame=False;self.preemptions=0;self.recoveries=0;self.faulted=False
        self.started=threading.Event();self.release=threading.Event();self.chats=0
        self.resident_after=resident_after;self.clock=clock;self.calls=[]
    def state(self):
        return {'active':self.active,'received_frame':self.frame,'faulted':self.faulted,
                'preemptions':self.preemptions,'confirmed_recoveries':self.recoveries}
    def agent_call(self,path):
        self.calls.append((path,self.clock() if self.clock else None))
        if path=='/broker/state':return {'http':200,'value':self.state()}
        if path=='/api/ps':
            self.resident_after-=1
            return {'http':200,'value':{'models':[] if self.resident_after>=0 else [{'name':'approved'}]}}
        if self.warm:
            code=self.warm.pop(0)
            return {'http':HELD.get(code,503),'value':{'done':None,'eval_count':None,'error':code}}
        self.chats+=1
        if self.active=='notes' and self.preempts:
            self.preemptions+=1;self.recoveries+=1;self.release.set()
        elif self.active=='notes':self.release.set()
        return {'http':200,'value':{'done':True,'eval_count':3,'error':None}}
    def chat_calls(self):return [t for p,t in self.calls if p=='/api/chat']
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
    def run_check(self,broker,clock=None):
        clock=clock or Clock()
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

    def test_missing_confirmed_recovery_fails(self):
        broker=FakeBroker()
        original=broker.agent_call
        def no_recovery(path):
            value=original(path)
            if path=='/api/chat' and broker.preemptions:broker.recoveries=0
            return value
        broker.agent_call=no_recovery
        with self.assertRaisesRegex(AssertionError,'confirmed preemption and recovery'):
            self.run_check(broker)

    def test_readiness_waits_out_unconfirmed_fence_then_proceeds(self):
        result=self.run_check(FakeBroker(warm_codes=['cancellation_unconfirmed']))
        self.assertEqual([a['http'] for a in result['readiness']['chat_probes']],[503,200])

    def test_readiness_treats_chat_budget_hold_as_wait(self):
        result=self.run_check(FakeBroker(warm_codes=['inference_budget','cancellation_unconfirmed']))
        self.assertEqual([a['code'] for a in result['readiness']['chat_probes']],['inference_budget','cancellation_unconfirmed',None])

    def test_readiness_fails_on_other_refusal_or_fault(self):
        with self.assertRaisesRegex(RuntimeError,'readiness handshake failed'):
            self.run_check(FakeBroker(warm_codes=['model_switching']))
        broker=FakeBroker(warm_codes=['cancellation_unconfirmed']);broker.faulted=True
        with self.assertRaisesRegex(RuntimeError,'readiness handshake failed'):
            self.run_check(broker)

    def test_readiness_chat_probes_are_bounded_and_spaced(self):
        clock=Clock();broker=FakeBroker(warm_codes=['cancellation_unconfirmed']*50,clock=clock)
        with self.assertRaisesRegex(RuntimeError,'readiness handshake failed'):
            self.run_check(broker,clock)
        times=broker.chat_calls()
        self.assertEqual(len(times),live.CHAT_PROBES)
        self.assertTrue(all(b-a>=live.CHAT_PROBE_SPACING for a,b in zip(times,times[1:])))

    def test_waiting_for_a_loading_model_uses_status_lane_not_chat(self):
        clock=Clock();broker=FakeBroker(resident_after=4,clock=clock)
        result=self.run_check(broker,clock)
        self.assertTrue(result['readiness']['model_resident'])
        first_chat=broker.calls.index(('/api/chat',broker.chat_calls()[0]))
        self.assertEqual({p for p,_ in broker.calls[:first_chat]},{'/api/ps'})
        self.assertEqual(broker.chats,2)

    def test_worst_case_chat_and_status_use_stays_within_broker_budgets(self):
        # Every chat-lane request in a whole run fits one 60 s window of the chat budget.
        self.assertLessEqual(live.CHAT_PROBES+1,LIMITS['chat']['requests'])
        # Status-lane polls (resident wait, state polling, per-probe state reads) stay under 120/min.
        per_minute=60/live.RESIDENT_POLL+60/live.STATE_POLL+live.CHAT_PROBES+2
        self.assertLess(per_minute,120)

    def test_note_summary_excludes_generated_text(self):
        self.assertNotIn('secret',str(live.note_summary({'ok':'secret note','metrics':{'done_reason':'stop'}})))

if __name__=='__main__':unittest.main()
