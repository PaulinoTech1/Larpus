from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from scripts.supervise import cycle, control, status, watch
from unittest.mock import patch
from scripts.recovery_policy import History, Policy
from scripts.recovery_backend import Backend
from scripts.recovery_state import Journal, StateError
from tests.test_recovery_backend import FakeAdapter
from tests.test_recovery_policy import IDENTITY, observation, history

class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.journal=Journal(self.root/'recovery',protect=lambda p,**kw:None)
        self.adapter=FakeAdapter();self.adapter.stop_selected=lambda:setattr(self.adapter,'stops',self.adapter.stops+1)
        self.backend=Backend(self.root,adapter=self.adapter,jitter=lambda:0)

    def test_queued_cycle_cannot_resurrect_intentional_shutdown(self):
        self.journal.write(history(dead_count=2))
        self.adapter.on_lock=lambda:self.journal.set_armed(False)
        cycle(self.backend,self.journal,Policy(),False)
        self.assertEqual(self.adapter.launches,0)
        self.assertFalse(self.journal.read().armed)

    def test_disabled_intent_persists_before_gateway_drain(self):
        self.journal.write(history())
        def stop(identity):
            self.assertFalse(self.journal.read().armed)
            self.adapter.stopped.append(identity);self.adapter.dead.add(identity)
        self.adapter.stop=stop
        control('disable',self.backend,self.journal,stop_gateway=True)
        self.assertFalse(self.journal.read().armed);self.assertEqual(self.adapter.stopped,[IDENTITY])

    def test_failed_publication_disable_drains_the_reserved_replacement(self):
        self.journal.write(history(dead_count=3));self.adapter.fail_publish=True
        self.assertEqual(self.backend.recover(IDENTITY,self.journal,Policy())['reason'],'launch-uncertain')
        self.assertEqual(self.adapter.stopped,[])
        launched=self.adapter.new
        control('disable',self.backend,self.journal,stop_gateway=True)
        self.assertFalse(self.journal.read().armed)
        self.assertEqual(self.adapter.stopped,[IDENTITY,launched])
        self.assertIsNone(self.journal.read().reservation)

    def test_disable_stop_holds_reused_unknown_and_unconfirmed_drain(self):
        self.journal.write(history(dead_count=3));self.adapter.fail_publish=True
        self.backend.recover(IDENTITY,self.journal,Policy())
        self.adapter.stopped=[];self.adapter.claim_mode='reused'
        control('disable',self.backend,self.journal,stop_gateway=True)
        self.assertEqual(self.adapter.stopped,[self.adapter.new])
        self.assertEqual(self.journal.read().reason,'reused')
        self.journal.write(history());self.adapter.stopped=[];self.adapter.claim_mode='unknown'
        control('disable',self.backend,self.journal,stop_gateway=True)
        self.assertEqual(self.adapter.stopped,[]);self.assertEqual(self.journal.read().reason,'unknown')
        self.adapter.claim_mode='owned';self.adapter.stop=lambda identity:(_ for _ in ()).throw(RuntimeError('drain'))
        self.journal.write(history())
        control('disable',self.backend,self.journal,stop_gateway=True)
        self.assertEqual(self.journal.read().reason,'cleanup-uncertain')

    def test_reused_or_unreadable_replacement_is_not_a_confirmed_drain(self):
        for marker in ('reused_identities','unreadable'):
            with self.subTest(marker=marker):
                self.journal.write(history(dead_count=3));self.adapter.fail_publish=True
                self.adapter.reused_identities=set();self.adapter.unreadable=set();self.adapter.dead=set()
                self.backend.recover(IDENTITY,self.journal,Policy())
                self.adapter.claim_mode='absent';self.adapter.stopped=[]
                getattr(self.adapter,marker).add(self.adapter.new)
                control('disable',self.backend,self.journal,stop_gateway=True)
                self.assertEqual(self.adapter.stopped,[])
                self.assertIsNotNone(self.journal.read().reservation)
                self.assertEqual(self.journal.read().reason,'reused' if marker=='reused_identities' else 'unknown')

    def test_observation_and_acknowledgement_do_not_waive_gates(self):
        self.journal.write(history(dead_count=2))
        result=cycle(self.backend,self.journal,Policy(),True)
        self.assertEqual(result.reason,'observe-only');self.assertEqual(result.action,'recover')
        self.assertEqual(self.adapter.launches,0);self.assertEqual(self.journal.read().dead_count,2)
        self.assertEqual(self.journal.read().attempts,())
        self.journal.write(replace(history(),state='held',reason='broker-fault',attempts=(900.,950.)))
        control('acknowledge',self.backend,self.journal)
        self.assertEqual(self.journal.read().attempts,(900.,950.))
        self.adapter.current=observation(broker='faulted',dependencies='failed')
        self.assertEqual(cycle(self.backend,self.journal,Policy(),False).reason,'broker-fault')
        self.assertEqual(self.adapter.launches,0)

    def test_pending_cutover_and_existing_drain_suppress_action(self):
        for suppression in ('deployment','maintenance','drain','unsupported'):
            self.journal.write(history(dead_count=2))
            self.adapter.current=observation(suppression=suppression)
            self.assertEqual(cycle(self.backend,self.journal,Policy(),False).action,'none')
        self.assertEqual(self.adapter.launches,0)

    def test_disable_and_rearm_cannot_clear_a_durable_hold(self):
        self.journal.write(replace(history(),state='held',reason='clock'))
        control('disable',self.backend,self.journal)
        cycle(self.backend,self.journal,Policy(),False)
        control('arm',self.backend,self.journal)
        self.assertEqual(self.journal.read().state,'held')

    def test_status_is_read_only_and_reports_age(self):
        self.assertFalse(status(self.journal,now=1000)['armed'])
        self.assertFalse(self.journal.directory.exists())
        self.journal.write(history(last_wall_time=100))
        self.assertTrue(status(self.journal,now=1000)['stale'])

    def test_observe_only_does_not_prime_an_armed_launch(self):
        self.journal.write(history(dead_count=0))
        stream=io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(watch(self.backend,self.journal,Policy(),observe_only=True,max_cycles=3),0)
        actions=[json.loads(line)['action'] for line in stream.getvalue().splitlines() if 'action' in json.loads(line)]
        self.assertEqual(actions,['none','none','recover'])
        self.assertEqual(self.journal.read().dead_count,0);self.assertEqual(self.adapter.launches,0)
        control('arm',self.backend,self.journal)
        self.assertNotEqual(cycle(self.backend,self.journal,Policy(),False).action,'recover')
        self.assertEqual(self.adapter.launches,0);self.assertEqual(self.journal.read().dead_count,1)

    def test_observe_only_drops_a_stale_streak_for_health_or_a_new_process(self):
        self.journal.write(history(dead_count=2))
        self.adapter.current=observation(process='alive',http='responding',readiness='ready')
        cycle(self.backend,self.journal,Policy(),True)
        self.assertEqual(self.journal.read().dead_count,0);self.assertEqual(self.adapter.launches,0)
        other=replace(IDENTITY,pid=999)
        self.journal.write(history(dead_count=2));self.adapter.current=observation(identity=other)
        cycle(self.backend,self.journal,Policy(),True)
        self.assertEqual(self.journal.read().dead_count,1);self.assertEqual(self.journal.read().identity,other)
        control('arm',self.backend,self.journal);self.adapter.validate=lambda expected:None
        self.assertNotEqual(cycle(self.backend,self.journal,Policy(),False).action,'recover')
        self.assertEqual(self.adapter.launches,0);self.assertEqual(self.journal.read().dead_count,2)
        self.assertEqual(cycle(self.backend,self.journal,Policy(),False).reason,'recovered')
        self.assertEqual(self.adapter.launches,1)

    def test_diagnostic_sink_failure_cannot_permit_a_launch(self):
        self.journal.write(history(dead_count=2))
        with patch('builtins.print',side_effect=OSError('closed')):
            self.assertEqual(watch(self.backend,self.journal,Policy(),max_cycles=1),2)
        self.assertEqual(self.adapter.launches,0)

