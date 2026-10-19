import io
import json
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
from scripts import ultra_fast_station as station_module

try:
    from scripts import ultra_fast_worker as worker, benchmark_ultra_fast as bench
except ImportError:
    worker=bench=None


class UltraFastTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(worker,'Owner-only Ultra Fast benchmark is not implemented')

    def test_first_text_ignores_empty_model_frames(self):
        response=io.BytesIO(b'{"message":{"content":""}}\n{"message":{"content":"Hi"}}\n{"done":true,"eval_count":2,"eval_duration":1000000000}\n')
        ticks=iter((0,0.1,0.3,0.8,0.9))
        row=worker.measure(response,clock=lambda:next(ticks))
        self.assertTrue(row['ok']);self.assertEqual(row['first_text_seconds'],0.3)
        self.assertEqual(row['answer'],'Hi');self.assertEqual(row['tokens_per_second'],2)

    def test_partial_response_is_retained_as_failure(self):
        row=worker.measure(io.BytesIO(b'{"message":{"content":"partial"}}\n'))
        self.assertFalse(row['ok']);self.assertEqual(row['answer'],'partial')
        self.assertEqual(row['error'],'missing_done')

    def test_invalid_and_empty_streams_do_not_succeed(self):
        for raw in (b'not-json\n',b'{"done":true}\n',b'{"message":{"content":9}}\n'):
            with self.subTest(raw=raw):self.assertFalse(worker.measure(io.BytesIO(raw))['ok'])

    def test_model_error_is_failure(self):
        row=worker.measure(io.BytesIO(b'{"error":"failed"}\n'))
        self.assertFalse(row['ok']);self.assertEqual(row['error'],'model_error')

    def test_schedule_excludes_warmups_and_balances_order(self):
        plan=bench.schedule([{'id':'a'}],4)
        self.assertEqual(len(plan),10)
        self.assertEqual([x[2] for x in plan[:2]],['raw','prepared'])
        measured=[x[2] for x in plan if x[0]=='measured']
        self.assertEqual(measured,['prepared','raw','raw','prepared','prepared','raw','raw','prepared'])

    def test_summary_keeps_failures_and_missing_timings(self):
        rows=[{'phase':'warmup','variant':'raw','case':'a','ok':True,'first_text_seconds':99},
              {'phase':'measured','variant':'raw','case':'a','ok':True,'first_text_seconds':1,'total_seconds':2},
              {'phase':'measured','variant':'raw','case':'a','ok':False}]
        result=bench.summarize(rows)['raw']
        self.assertEqual(result['attempted'],2);self.assertEqual(result['succeeded'],1)
        self.assertEqual(result['first_text_seconds']['median'],1)

    def test_dry_run_does_not_start_services(self):
        with patch.object(bench,'run') as run,patch('sys.stdout',new=io.StringIO()):
            self.assertEqual(bench.main([]),0)
        run.assert_not_called()

    def test_payload_preserves_settings_and_prepared_messages(self):
        messages=[{'role':'system','content':'exact instructions'},{'role':'user','content':'question'}]
        result=bench.payload('fixed-tag',131072,0.2,messages,1024)
        self.assertEqual(result['messages'],messages)
        self.assertEqual(result['options'],{'temperature':0.2,'num_ctx':131072,'num_predict':1024,'num_gpu':99})
        self.assertTrue(result['stream']);self.assertFalse(result['think'])

    def test_results_are_invalid_on_identity_change_or_partial_run(self):
        rows=[{'ok':True}]
        self.assertFalse(bench.valid(rows,2,{'id':1},{'id':1}))
        self.assertFalse(bench.valid(rows,1,{'id':1},{'id':2}))
        self.assertFalse(bench.valid([{'ok':False}],1,{},{}))

    def test_running_gateway_is_never_stopped_by_benchmark(self):
        station=station_module.Station()
        with patch.object(station_module.releases,'read',return_value={'id':'a'*32,'pid':1}),patch.object(station_module.releases,'running',return_value=True),patch.object(station_module.releases,'podman') as command:
            with self.assertRaisesRegex(RuntimeError,'stopped station'):station.open()
        command.assert_not_called()

    def test_cleanup_stops_only_started_services_and_restores_stopped_wsl(self):
        station=station_module.Station();station.started=['larpus-model','larpus-agent-'+'a'*32]
        station.touched=True;station.was_running=False;station.state={'id':'a'*32}
        with patch.object(station_module.releases,'podman') as command,patch.object(station_module.releases,'read',return_value=station.state),patch.object(station_module,'running',return_value=[]),patch.object(station_module,'distro_running',return_value=False),patch.object(station_module.subprocess,'run') as terminate:
            station.close()
        self.assertEqual(command.call_args_list[0].args,('stop','--time','20','larpus-agent-'+'a'*32,'larpus-model'))
        terminate.assert_called_once();self.assertTrue(station.cleanup['wsl_stopped'])
        self.assertTrue(station.cleanup['restored'])

    def test_failed_open_runs_cleanup(self):
        station=station_module.Station()
        with patch.object(station_module,'distro_running',return_value=False),patch.object(station,'open',side_effect=RuntimeError('model failed')),patch.object(station,'close') as close:
            with self.assertRaisesRegex(RuntimeError,'model failed'):station.__enter__()
        close.assert_called_once()

    def test_initially_running_wsl_is_preserved(self):
        station=station_module.Station();station.was_running=True;station.state={'id':'a'*32}
        with patch.object(station_module.releases,'read',return_value=station.state),patch.object(station_module.subprocess,'run') as terminate:
            station.close()
        terminate.assert_not_called()

    def test_new_unowned_container_prevents_pod_stop_and_wsl_termination(self):
        station=station_module.Station();station.touched=True;station.was_running=False
        with patch.object(station_module,'running',return_value=[{'Names':['new-owner-work'],'IsInfra':False}]),patch.object(station_module.releases,'podman') as command,patch.object(station_module.subprocess,'run') as terminate:
            with self.assertRaisesRegex(RuntimeError,'Unexpected services'):station.close()
        command.assert_not_called();terminate.assert_not_called()

    def test_interrupted_attempt_is_returned_for_durable_failure_record(self):
        station=SimpleNamespace(profile={'agent_image':'fixed-image'})
        with patch.object(bench,'wsl_command',return_value=['fixed-command']),patch.object(bench.subprocess,'run',side_effect=KeyboardInterrupt):
            try:row=bench.direct(station,{})
            except KeyboardInterrupt:self.fail('Interrupted benchmark attempt was lost')
        self.assertFalse(row['ok']);self.assertEqual(row['error'],'interrupted')

    def test_failed_wsl_stop_cannot_be_reported_as_restored(self):
        station=station_module.Station();station.was_running=False;station.touched=True;station.state={'id':'a'*32}
        with patch.object(station_module.releases,'podman'),patch.object(station_module.releases,'read',return_value=station.state),patch.object(station_module,'running',return_value=[]),patch.object(station_module,'distro_running',return_value=True),patch.object(station_module.subprocess,'run'):
            station.close()
        self.assertFalse(station.cleanup['restored'])


if __name__=='__main__':unittest.main()
