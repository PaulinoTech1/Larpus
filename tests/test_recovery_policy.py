import unittest
from dataclasses import replace
from scripts.recovery_policy import Policy, GatewayIdentity, Observation, History, decide

IDENTITY=GatewayIdentity('a'*32,123,'created','b'*64)

def observation(**changes):
    base=Observation(IDENTITY,'dead','unreachable','unknown','ready','idle',None,1000.,100.)
    return replace(base,**changes)

def history(**changes):
    return replace(History(),armed=True,state='observing',identity=IDENTITY,**changes)

class PolicyTests(unittest.TestCase):
    def test_only_third_confirmed_death_proposes_recovery(self):
        for count in (0,1,2):
            result=decide(observation(),history(dead_count=count),Policy())
            self.assertEqual(result.action,'recover' if count==2 else 'none')
            self.assertEqual(result.dead_count,count+1)

    def test_unknown_and_reused_process_never_advance_death(self):
        for process in ('alive','unknown','reused'):
            result=decide(observation(process=process),history(dead_count=2),Policy())
            self.assertEqual(result.action,'none');self.assertEqual(result.dead_count,0)

    def test_refusals_and_warnings_never_become_restart_requests(self):
        for changes in ({'dependencies':'busy'},{'dependencies':'failed'},
                        {'dependencies':'unknown'},{'broker':'busy'},
                        {'broker':'faulted'},{'broker':'unknown'},
                        {'suppression':'maintenance'},{'suppression':'deployment'}):
            with self.subTest(changes=changes):
                self.assertEqual(decide(observation(**changes),history(dead_count=2),Policy()).action,'none')
        live=observation(process='alive',http='responding',readiness='ready')
        self.assertEqual(decide(live,history(),Policy()).state,'observing')

    def test_budget_cooldown_selection_and_clock_boundaries(self):
        for changes in ({'attempts':(900.,950.)},{'next_attempt_wall_time':1001.},
                        {'last_wall_time':1001.},{'reservation':{'id':'pending'}}):
            self.assertEqual(decide(observation(),history(dead_count=2,**changes),Policy()).action,'none')
        changed=observation(identity=replace(IDENTITY,pid=124))
        self.assertEqual(decide(changed,history(dead_count=2),Policy()).dead_count,1)
        self.assertEqual(decide(observation(),replace(history(),state='held'),Policy()).state,'held')

    def test_disabled_and_missing_identity_never_launch(self):
        self.assertEqual(decide(observation(),History(),Policy()).state,'disabled')
        self.assertEqual(decide(observation(identity=None),history(dead_count=2),Policy()).action,'none')

    def test_unknown_http_cannot_confirm_an_empty_listener(self):
        self.assertEqual(decide(observation(http='unknown'),history(dead_count=2),Policy()).action,'none')

    def test_invalid_records_fail_closed(self):
        for changes in ({'process':'maybe'},{'wall_time':float('nan')},{'wall_time':True}):
            with self.assertRaises(ValueError):observation(**changes)
        for changes in ({'attempt_limit':3},{'interval_seconds':0},{'window_seconds':float('inf')}):
            with self.assertRaises(ValueError):Policy(**changes)
        with self.assertRaises(ValueError):replace(IDENTITY,pid=True)

