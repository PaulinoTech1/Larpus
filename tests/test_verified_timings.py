import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from runtime import knowledge,mcp_client,mcp_server


class VerifiedTimingTests(unittest.TestCase):
    def test_child_import_timing_is_numeric_and_diagnostic_only(self):
        plain={'status':200,'content':'ok'}
        detailed={'status':200,'content':'ok'}
        fast={'status':200,'content':'ok'}
        self.assertIs(mcp_server.startup_timing(plain,{'profile':'verified'}),plain)
        self.assertTrue(0<=plain['timing_ms']['mcp_child_import']<=90000)
        self.assertIs(mcp_server.startup_timing(detailed,{'profile':'diagnostic'}),detailed)
        self.assertTrue(0<=detailed['timing_ms']['mcp_child_import']<=90000)
        self.assertIs(mcp_server.startup_timing(fast,{'profile':'ultra-fast'}),fast)
        self.assertNotIn('timing_ms',fast)

    def test_retrieval_detail_wiring_keeps_evidence_unchanged(self):
        evidence=[{'id':'example','text':'approved passage'}]
        timings={}
        with patch.object(knowledge,'_retrieve',return_value=evidence) as retrieve,patch.object(knowledge,'provenance_entries',return_value={}),patch.object(knowledge,'study_notes',return_value=[]):
            result=knowledge.retrieve('home-assistant','example question',timings=timings)
        self.assertEqual(result,evidence)
        self.assertIs(retrieve.call_args.kwargs['timings'],timings)
        self.assertTrue({'retrieval_base','retrieval_provenance'}<=set(timings))
        self.assertNotIn('approved passage',str(timings))

    def test_retrieval_measurement_preserves_result_failure_and_disabled_clock(self):
        with patch.object(knowledge.time,'perf_counter',side_effect=AssertionError('disabled')):
            self.assertEqual(knowledge.measured(None,'retrieval_base',lambda:42),42)
        timings={}
        with patch.object(knowledge.time,'perf_counter',side_effect=[1.,1.25]):
            self.assertEqual(knowledge.measured(timings,'retrieval_base',lambda:42),42)
        self.assertEqual(timings,{'retrieval_base':250.})
        with self.assertRaisesRegex(ValueError,'required gate'):
            knowledge.measured({},'retrieval_base',lambda:(_ for _ in ()).throw(ValueError('required gate')))

    def test_broken_timing_sink_or_clock_cannot_change_retrieval(self):
        class Broken(dict):
            def __setitem__(self,*args):raise OSError('sink')
        self.assertEqual(knowledge.measured(Broken(),'retrieval_base',lambda:42),42)
        with patch.object(knowledge.time,'perf_counter',side_effect=OSError('clock')):
            self.assertEqual(knowledge.measured({},'retrieval_base',lambda:42),42)

    def test_diagnostic_host_phase_timings_reach_result_without_default_overhead(self):
        class FakeClient:
            def __init__(self,*args,**kwargs):pass
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def call_tool(self,*args,**kwargs):
                return SimpleNamespace(is_error=False,structured_content={'status':200,'content':'ok'})
        def parameters(execution=None,timings=None):
            if timings is not None:timings['preflight_initial_reads']=12.
            return 'fixed'
        with patch.object(mcp_client,'child_parameters',side_effect=parameters),patch.object(mcp_client,'Client',FakeClient):
            diagnostic=asyncio.run(mcp_client.call_async('chat_local',execution={'profile':'diagnostic'}))
            default=asyncio.run(mcp_client.call_async('chat_local'))
            fast=asyncio.run(mcp_client.call_async('chat_local',execution={'profile':'ultra-fast'}))
        self.assertEqual(diagnostic['timing_ms']['preflight_initial_reads'],12.)
        self.assertEqual(default['timing_ms']['preflight_initial_reads'],12.)
        self.assertIn('mcp_parent_stages_ms',default)
        self.assertNotIn('preflight_initial_reads',fast['timing_ms'])
        self.assertNotIn('mcp_parent_stages_ms',fast)


if __name__=='__main__':unittest.main()
