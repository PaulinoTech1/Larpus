import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from runtime import model_selection

spec=importlib.util.spec_from_file_location('releases',Path(__file__).resolve().parents[1]/'scripts/releases.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

class ReleaseTests(unittest.TestCase):
    def test_driver_repin_requires_one_narrow_existing_package(self):
        old={'gpu_driver':'/usr/lib/wsl/drivers/nv_dispi.inf_amd64_aaaaaaaaaaaaaaaa'}
        new='/usr/lib/wsl/drivers/nv_dispi.inf_amd64_20f49c6eb5c9b39b'
        with patch.object(release,'wsl',return_value='') as check:
            selected=release.select_gpu_driver(old,new)
        check.assert_called_once_with('/usr/bin/test','-f',new+'/libcuda.so.1.1')
        self.assertEqual(selected['gpu_driver'],new)
        self.assertEqual(old['gpu_driver'],'/usr/lib/wsl/drivers/nv_dispi.inf_amd64_aaaaaaaaaaaaaaaa')
        with patch.object(release,'wsl') as check:
            for invalid in ('/usr/lib/wsl/drivers','/usr/lib/wsl/drivers/nv_dispi.inf_amd64_20f49c6eb5c9b39b/../other'):
                with self.assertRaisesRegex(ValueError,'narrow NVIDIA'):
                    release.select_gpu_driver(old,invalid)
            check.assert_not_called()
        with patch.object(release,'wsl',side_effect=RuntimeError('missing')):
            with self.assertRaisesRegex(RuntimeError,'missing'):
                release.select_gpu_driver(old,new)

    def test_ui_checks_use_the_candidates_manifest(self):
        import contextlib,io
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'scripts').mkdir();(root/'tests').mkdir()
            (root/'scripts/ui_checks.py').write_text("TESTS=('candidate-ui.cjs',)\n",encoding='utf-8')
            (root/'tests/candidate-ui.cjs').write_text("console.log('candidate suite passed');\n",encoding='utf-8')
            output=io.StringIO()
            with contextlib.redirect_stdout(output):release.check_ui(root)
            self.assertEqual(output.getvalue().strip(),'candidate suite passed')

    def test_startup_model_readiness_reuses_verified_model(self):
        class Backend:
            def __init__(self):
                self.state = dict(model_selection.initial(), active_id='larpus-3.8')
                self.model = {'name':'larpus3.8:27b-q4','size':10,'size_vram':10,'context_length':131072}
                self.loads = []
                self.verifications = []
            def read(self):return self.state
            def call(self,path,timeout=300,process_timeout=None):return {'models':[self.model]}
            def verify(self,identifier):
                self.verifications.append(identifier)
                return self.model
            def load(self,identifier):self.loads.append(identifier)
            def notes_busy(self):return False
        backend=Backend()
        result=release.ensure_startup_model(backend,timeout=1,poll_interval=0)
        self.assertEqual(result['name'],backend.model['name'])
        self.assertEqual(backend.verifications,['larpus-3.8'])
        self.assertEqual(backend.loads,[])

    def test_startup_model_readiness_warms_cold_approved_model(self):
        class Backend:
            def __init__(self):
                self.state = dict(model_selection.initial(), active_id='larpus-3.8')
                self.model = {'name':'larpus3.8:27b-q4','size':10,'size_vram':10,'context_length':131072}
                self.loaded=False;self.loads=[];self.verifications=[]
            def read(self):return self.state
            def call(self,path,timeout=300,process_timeout=None):return {'models':[self.model] if self.loaded else []}
            def identity(self,identifier):self.asserted_identity=identifier
            def load(self,identifier):
                self.identity(identifier);self.loads.append(identifier);self.loaded=True
            def verify(self,identifier):
                self.verifications.append(identifier)
                if not self.loaded:raise ValueError('Model is not resident')
                return self.model
            def notes_busy(self):return False
        backend=Backend()
        release.ensure_startup_model(backend,timeout=1,poll_interval=0)
        self.assertEqual(backend.loads,['larpus-3.8'])
        self.assertEqual(backend.verifications,['larpus-3.8'])
        self.assertEqual(backend.asserted_identity,'larpus-3.8')

    def test_startup_model_readiness_waits_for_delayed_model_service(self):
        class Backend:
            def __init__(self):
                self.state=model_selection.initial();self.calls=0
                self.model={'name':'qwen3.5:27b-q4_K_M','size':10,'size_vram':10,'context_length':131072}
            def read(self):return self.state
            def call(self,path,timeout=300,process_timeout=None):
                self.calls+=1
                if self.calls<3:raise RuntimeError('Model service is starting')
                return {'models':[self.model]}
            def verify(self,identifier):return self.model
            def load(self,identifier):self.fail('Already verified model was reloaded')
            def notes_busy(self):return False
        backend=Backend()
        with patch.object(release.time,'sleep'):
            release.ensure_startup_model(backend,timeout=1,poll_interval=.01)
        self.assertEqual(backend.calls,3)

    def test_startup_model_readiness_waits_for_full_gpu_placement(self):
        class Backend:
            def __init__(self):
                self.state=model_selection.initial();self.verifications=0
                self.model={'name':'qwen3.5:27b-q4_K_M','size':10,'size_vram':10,'context_length':131072}
            def read(self):return self.state
            def call(self,path,timeout=300,process_timeout=None):return {'models':[self.model]}
            def verify(self,identifier):
                self.verifications+=1
                if self.verifications==1:raise release.ModelPlacementPending('partial placement')
                return self.model
            def load(self,identifier):self.fail('Already loaded model was reloaded')
            def notes_busy(self):return False
        backend=Backend()
        with patch.object(release.time,'sleep'):
            release.ensure_startup_model(backend,timeout=1,poll_interval=.01)
        self.assertEqual(backend.verifications,2)

    def test_startup_model_readiness_fails_bounded_when_service_stays_down(self):
        class Backend:
            def read(self):return model_selection.initial()
            def call(self,path,timeout=300,process_timeout=None):raise RuntimeError('Model service is unavailable')
        with patch.object(release.time,'sleep'):
            with self.assertRaisesRegex(RuntimeError,'model service'):
                release.ensure_startup_model(Backend(),timeout=.01,poll_interval=0)

    def test_startup_model_readiness_rejects_invalid_identity_or_placement(self):
        class Backend:
            def __init__(self,model):
                self.state=model_selection.initial();self.model=model;self.loads=[]
            def read(self):return self.state
            def call(self,path,timeout=300,process_timeout=None):return {'models':[self.model]}
            def verify(self,identifier):raise ValueError('Full GPU/context verification failed')
            def load(self,identifier):self.loads.append(identifier)
            def notes_busy(self):return False
        for model in (
            {'name':'qwen3.5:27b-q4_K_M','size':10,'size_vram':9,'context_length':131072},
            {'name':'qwen3.5:27b-q4_K_M','size':10,'size_vram':10,'context_length':65536},
        ):
            backend=Backend(model)
            with self.assertRaisesRegex(ValueError,'GPU/context'):
                release.ensure_startup_model(backend,timeout=1,poll_interval=0)
            self.assertEqual(backend.loads,[])

    def test_startup_model_readiness_rejects_bad_cold_identity_before_warmup(self):
        class Backend:
            def __init__(self):self.state=model_selection.initial();self.warmups=0
            def read(self):return self.state
            def call(self,path,timeout=300,process_timeout=None):return {'models':[]}
            def notes_busy(self):return False
            def identity(self,identifier):raise ValueError('Model weight identity differs')
            def load(self,identifier):
                self.identity(identifier);self.warmups+=1
        backend=Backend()
        with self.assertRaisesRegex(ValueError,'identity'):
            release.ensure_startup_model(backend,timeout=1,poll_interval=0)
        self.assertEqual(backend.warmups,0)

    def test_startup_model_readiness_rejects_unapproved_selection(self):
        class Backend:
            def read(self):return dict(model_selection.initial(),active_id='remote-model')
        with self.assertRaisesRegex(ValueError,'Unknown local model'):
            release.ensure_startup_model(Backend(),timeout=1,poll_interval=0)

    def test_startup_model_readiness_defers_cold_warmup_during_notes(self):
        class Backend:
            def read(self):return model_selection.initial()
            def call(self,path,timeout=300,process_timeout=None):return {'models':[]}
            def notes_busy(self):return True
            def load(self,identifier):self.fail('Must not warm while notes are active')
        with self.assertRaisesRegex(RuntimeError,'Nightly notes'):
            release.ensure_startup_model(Backend(),timeout=1,poll_interval=0)

    def test_broker_startup_requires_private_sockets_and_idle_scheduler(self):
        profile={'broker':{'container':'larpus-broker-'+'a'*32}}
        state={'faulted':False,'active':None,'waiting_chat':0}
        with patch.object(release,'podman',return_value=json.dumps(state)) as command:
            self.assertEqual(release.verify_broker_startup(profile),state)
        self.assertEqual(command.call_args.args[:4],('exec',profile['broker']['container'],'python','-c'))
        self.assertIn('/run/larpus-notes/inference.sock',command.call_args.args[4])

    def test_broker_startup_waits_for_active_work_without_stopping_it(self):
        profile={'broker':{'container':'larpus-broker-'+'a'*32}}
        states=iter(({'faulted':False,'active':'notes','waiting_chat':0},{'faulted':False,'active':None,'waiting_chat':0}))
        with patch.object(release,'podman',side_effect=lambda *args,**kwargs:json.dumps(next(states))) as command,patch.object(release.time,'sleep'):
            release.verify_broker_startup(profile,timeout=1,poll_interval=.01)
        self.assertEqual(command.call_count,2)
        self.assertTrue(all(call.args[0]=='exec' for call in command.call_args_list))

    def test_broker_startup_does_not_clear_cancellation_fault(self):
        profile={'broker':{'container':'larpus-broker-'+'a'*32}}
        state={'faulted':True,'active':None,'waiting_chat':0}
        with patch.object(release,'podman',return_value=json.dumps(state)) as command:
            with self.assertRaisesRegex(RuntimeError,'cancellation fence is faulted'):
                release.verify_broker_startup(profile)
        self.assertEqual(command.call_count,1)

    def test_startup_model_failure_does_not_start_agent_or_gateway(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(release,'STORE',Path(directory)),patch.object(release,'running',return_value=False),patch.object(release,'verify_broker_startup'),patch.object(release,'ensure_startup_model',side_effect=RuntimeError('model not ready')),patch.object(release,'launch') as launch,patch.object(release,'podman') as podman:
            identifier='a'*32;root=Path(directory)/identifier;root.mkdir()
            release.write(Path(directory)/'active.json',{'id':identifier,'pid':1})
            release.write(root/'deployment.json',{'broker':{'container':'larpus-broker-'+identifier},'agent_name':'larpus-agent-'+identifier})
            release.write(root/'voice-deployment.json',{'container':'larpus-voice-'+identifier})
            with self.assertRaisesRegex(RuntimeError,'model not ready'):release.start()
            launch.assert_not_called()
            self.assertEqual([call.args for call in podman.call_args_list],[('start','larpus-model'),('start','larpus-broker-'+identifier)])

    def test_startup_model_is_verified_before_agent_and_gateway_start(self):
        events=[]
        with tempfile.TemporaryDirectory() as directory,patch.object(release,'STORE',Path(directory)),patch.object(release,'running',return_value=False),patch.object(release,'verify_broker_startup',side_effect=lambda profile:events.append('broker-ready')),patch.object(release,'ensure_startup_model',side_effect=lambda:events.append('model-ready')),patch.object(release,'podman',side_effect=lambda *args:events.append('container:'+args[-1])),patch.object(release,'launch',side_effect=lambda *args:events.append('gateway') or {'id':'a'*32,'pid':2}),patch.object(release,'ready',side_effect=lambda state:events.append('functional-ready')):
            identifier='a'*32;root=Path(directory)/identifier;root.mkdir()
            release.write(Path(directory)/'active.json',{'id':identifier,'pid':1})
            release.write(root/'deployment.json',{'broker':{'container':'larpus-broker-'+identifier},'notes':{'container':'larpus-notes-'+identifier},'agent_name':'larpus-agent-'+identifier})
            release.write(root/'voice-deployment.json',{'container':'larpus-voice-'+identifier})
            release.start()
        self.assertEqual([event for event in events if event.startswith('container:')],[
            'container:larpus-model','container:larpus-broker-'+identifier,
            'container:larpus-notes-'+identifier,'container:larpus-voice-'+identifier,
            'container:larpus-agent-'+identifier])
        self.assertLess(events.index('model-ready'),events.index('container:larpus-agent-'+identifier))
        self.assertLess(events.index('broker-ready'),events.index('model-ready'))
        self.assertLess(events.index('model-ready'),len(events)-3)
        self.assertLess(events.index('model-ready'),events.index('gateway'))
        self.assertLess(events.index('gateway'),events.index('functional-ready'))

    def test_startup_health_failure_closes_and_drains_unready_gateway(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(release,'STORE',Path(directory)),patch.object(release,'running',return_value=False),patch.object(release,'verify_broker_startup'),patch.object(release,'ensure_startup_model'),patch.object(release,'podman'),patch.object(release,'launch',return_value={'id':'a'*32,'pid':2}),patch.object(release,'ready',side_effect=RuntimeError('functional health failed')),patch.object(release,'stop') as stop:
            identifier='a'*32;root=Path(directory)/identifier;root.mkdir()
            previous={'id':identifier,'pid':1}
            release.write(Path(directory)/'active.json',previous)
            release.write(root/'deployment.json',{'broker':{'container':'larpus-broker-'+identifier},'agent_name':'larpus-agent-'+identifier})
            release.write(root/'voice-deployment.json',{'container':'larpus-voice-'+identifier})
            with self.assertRaisesRegex(RuntimeError,'functional health'):
                release.start()
            self.assertEqual(release.read(Path(directory)/'active.json'),previous)
            stop.assert_called_once_with({'id':identifier,'pid':2})

    def test_pipeline_preparation_smoke_switches_and_restores_before_scan(self):
        response={'initial':{'active_id':'assembly'},'numpy':{'active_id':'numpy'},'assembly':{'active_id':'assembly'},'optimized':{'active_id':'assembly-optimized'},'restored':{'active_id':'assembly'}}
        with patch.object(release,'podman',return_value=json.dumps(response)) as command:
            release.verify_pipeline({'agent_name':'larpus-agent-'+'a'*32})
        self.assertEqual(command.call_args.args[:3],('exec','larpus-agent-'+'a'*32,'python'))
        response['assembly']['active_id']='numpy'
        with patch.object(release,'podman',return_value=json.dumps(response)):
            with self.assertRaises(ValueError):release.verify_pipeline({'agent_name':'larpus-agent-'+'a'*32})

    def test_scoped_staging_reads_source_and_keeps_owner_store_and_data(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'owner';source=Path(directory)/'source';store=root/'data/releases'
            for path in (root/'runtime',root/'vendor',store,source/'runtime'):path.mkdir(parents=True,exist_ok=True)
            (root/'runtime/one.py').write_text('unrelated owner edit')
            (source/'runtime/one.py').write_text('scoped candidate')
            junction=Mock()
            with patch.object(release,'ROOT',root),patch.object(release,'STORE',store),patch.object(release,'DIRECTORIES',('runtime',)),patch.object(release,'FILES',()),patch.object(release,'run',return_value='a'*64),patch('scripts.knowledge_counts.reconcile'),patch.dict('sys.modules',{'_winapi':SimpleNamespace(CreateJunction=junction)}):
                identifier=release.stage(source)
            self.assertEqual((store/identifier/'runtime/one.py').read_text(),'scoped candidate')
            self.assertEqual((root/'runtime/one.py').read_text(),'unrelated owner edit')
            self.assertEqual(junction.call_args_list[0].args,(str((root/'data').resolve()),str(store/identifier/'data')))

    def test_staging_rejects_catalog_index_mismatch_before_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source';source.mkdir()
            store=Path(directory)/'releases'
            with patch.object(release,'STORE',store),patch('scripts.knowledge_counts.reconcile',side_effect=ValueError('catalog mismatch')):
                with self.assertRaisesRegex(ValueError,'catalog mismatch'):
                    release.stage(source)
            self.assertFalse(store.exists())

    def test_readiness_uses_functional_station_health(self):
        import io
        names=('password','local_skills','approved_knowledge','input_filter','output_dlp','mcp_surface','models','model_gpu','egress_enforcement','voice')
        body=json.dumps({'checks':[{'name':name,'status':'pass'} for name in names]}).encode()
        with tempfile.TemporaryDirectory() as directory,patch.object(release,'STORE',Path(directory)),patch.object(release,'running',return_value=True),patch.object(release.HTTP,'open',return_value=io.BytesIO(body)) as request:
            release.ready({'id':'a'*32,'port':8080})
            self.assertEqual(request.call_args.args[0],'http://127.0.0.1:8080/api/station-health')
            self.assertEqual(release._startup_gate('a'*32).read_text(), 'ready\n')

    def test_recovery_preserves_already_restored_gateway_pid(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(release,'STORE',Path(directory)),patch.object(release,'running',return_value=True),patch.object(release,'ready') as ready,patch.object(release,'stop') as stop:
            old={'id':'a'*32,'pid':1};restored={**old,'pid':3}
            release.write(Path(directory)/'active.json',restored)
            release.write(Path(directory)/'pending.json',{'old':old,'candidate':{'id':'b'*32,'pid':2}})
            release.start()
            self.assertEqual(release.read(Path(directory)/'active.json'),restored)
            self.assertFalse((Path(directory)/'pending.json').exists())
            stop.assert_not_called();ready.assert_called_once_with(restored)

    def test_release_ids_cannot_escape_store(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(release,'STORE',Path(directory)):
            for value in ('../active','x'*32,'a'*31,None,'a'*32+'/nested'):
                with self.assertRaises(ValueError):release.release_path(value)
            self.assertEqual(release.release_path('a'*32),Path(directory)/('a'*32))

    def test_payload_catches_ui_and_knowledge_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'web').mkdir();(root/'knowledge').mkdir()
            (root/'web/app.js').write_text('original');(root/'knowledge/approved.sqlite').write_bytes(b'index')
            original=release.payload(root)
            (root/'web/app.js').write_text('new')
            self.assertNotEqual(original,release.payload(root))
            self.assertEqual(original['knowledge/approved.sqlite'],release.payload(root)['knowledge/approved.sqlite'])

    def test_scan_gate_rejects_new_missing_and_incomplete_findings(self):
        summary={'status':'warning','results':[{'target':'skill'+str(i),'status':'pass','complete':True} for i in range(64)]+[{'target':'mcp','status':'warning','complete':True}]}
        report={'issues':[{'category':'Execution','pattern':'fixed helper','severity':'MEDIUM','location':{'file':'isolation.py'}}]}
        release.scan_gate(summary,report,report)
        with self.assertRaises(ValueError):release.scan_gate(summary,{'issues':[]},report)
        summary['results'][0]['complete']=False
        with self.assertRaises(ValueError):release.scan_gate(summary,report,report)

    def test_reused_pid_never_signalled(self):
        state={'pid':12,'process':{'CreationDate':'before'}}
        with patch.object(release,'process',return_value={'CreationDate':'after'}):
            self.assertFalse(release.running(state))
            with self.assertRaises(ValueError):release.stop(state)
        with patch.object(release,'process',return_value=None):self.assertFalse(release.running(state))

    def test_failed_candidate_restores_old_release_and_pointer(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(release,'STORE',Path(directory)),patch.object(release,'validate'),patch.object(release,'run'),patch.object(release,'stop') as stop,patch.object(release,'running',return_value=False),patch.object(release,'launch') as launch,patch.object(release,'ready',side_effect=[RuntimeError('candidate failed'),None]),patch.object(release,'ensure_execution'):
            old={'id':'a'*32,'pid':1,'process':{},'host':'192.168.1.2','subnet':'192.168.1.0/24','port':8080}
            new={**old,'id':'b'*32,'pid':2};restored={**old,'pid':3}
            release.write(Path(directory)/'active.json',old);launch.side_effect=[new,restored]
            for state in (old,new):release.write(Path(directory)/state['id']/'deployment.json',{})
            with self.assertRaises(RuntimeError):release.cutover(new['id'])
            self.assertEqual(release.read(Path(directory)/'active.json')['pid'],3)
            self.assertEqual(stop.call_args_list[0].args[0],old)
            self.assertEqual(stop.call_args_list[1].args[0],new)
            self.assertFalse((Path(directory)/'pending.json').exists())

    def test_failed_validation_never_stops_active(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(release,'STORE',Path(directory)),patch.object(release,'validate',side_effect=ValueError('bad candidate')),patch.object(release,'stop') as stop:
            with self.assertRaises(ValueError):release.cutover('a'*32)
            stop.assert_not_called()

    def test_changed_deployment_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/('a'*32);root.mkdir()
            release.write(root/'deployment.json',{'source_fingerprint':'b'*64,'agent_image':'c'*64})
            release.write(root/'release-state/security/summary.json',{'fingerprint':'b'*64})
            release.write(root/'release-state/security/mcp.json',{'issues':[]})
            meta={'version':1,'id':root.name,'source_fingerprint':'b'*64,'files':{'web/app.js':'test'},'status':'prepared','deployment_sha256':release.checksum(root/'deployment.json'),'scan_summary_sha256':release.checksum(root/'release-state/security/summary.json'),'scan_report_sha256':release.checksum(root/'release-state/security/mcp.json')}
            release.write(root/'release.json',meta)
            with patch.object(release,'payload',return_value=meta['files']),patch.object(release,'run',return_value='b'*64):
                release.validate(root)
                release.write(root/'deployment.json',{'source_fingerprint':'b'*64,'agent_image':'d'*64})
                with self.assertRaises(ValueError):release.validate(root)

    def test_agent_name_is_fixed_or_release_identity(self):
        from runtime.isolation import agent_name
        self.assertEqual(agent_name({}),'larpus-agent')
        self.assertEqual(agent_name({'agent_name':'larpus-agent-'+'a'*32}),'larpus-agent-'+'a'*32)
        for name in ('other-service','larpus-agent;sh','larpus-agent-../','larpus-agent-'+'a'*12):
            with self.assertRaises(ValueError):agent_name({'agent_name':name})

    def test_drain_keeps_auth_boundary_and_blocks_new_inference(self):
        import http.client
        import threading
        from http.server import ThreadingHTTPServer
        from runtime import gateway
        from runtime.auth import Auth,password_record
        with tempfile.TemporaryDirectory() as directory,patch.object(gateway,'DRAIN',Path(directory)/'drain'),patch.object(gateway,'mcp_chat') as model:
            gateway.DRAIN.write_text('drain')
            server=ThreadingHTTPServer(('127.0.0.1',0),gateway.Handler)
            server.auth=Auth(password_record('test-password-only'));server.lan_network=None;server.tls=False;server.local_auth_bypass=True
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                conn.request('POST','/api/chat','{}',{'Content-Type':'application/json'})
                response=conn.getresponse();self.assertEqual(response.status,503);self.assertEqual(response.getheader('Retry-After'),'5');response.read();conn.close()
                server.local_auth_bypass=False
                conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                conn.request('POST','/api/chat','{}',{'Content-Type':'application/json'})
                response=conn.getresponse();self.assertEqual(response.status,401);response.read();conn.close()
                model.assert_not_called()
            finally:server.shutdown();server.server_close();thread.join()

    def test_restart_uses_active_release_voice_container(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(release,'STORE',Path(directory)),patch.object(release,'running',return_value=False),patch.object(release,'podman') as podman,patch.object(release,'launch',return_value={'id':'a'*32,'pid':2}),patch.object(release,'ready'):
            identifier='a'*32;root=Path(directory)/identifier;name='larpus-voice-'+identifier
            release.write(Path(directory)/'active.json',{'id':identifier,'pid':1})
            release.write(root/'deployment.json',{'agent_name':'larpus-agent-'+identifier})
            release.write(root/'voice-deployment.json',{'container':name})
            release.start()
            self.assertIn((('start',name),{}),[(c.args,c.kwargs) for c in podman.call_args_list])
            self.assertNotIn((('start','larpus-voice'),{}),[(c.args,c.kwargs) for c in podman.call_args_list])

if __name__=='__main__':unittest.main()


class PruneTests(unittest.TestCase):
    def test_prune_stops_only_idle_release_containers(self):
        import importlib.util as u
        from pathlib import Path as P
        from unittest.mock import patch as p
        s=u.spec_from_file_location('rel_prune',P(__file__).resolve().parents[1]/'scripts/releases.py');m=u.module_from_spec(s);s.loader.exec_module(m)
        running='4c73-infra\nlarpus-model\nlarpus-agent-'+'a'*32+'\nlarpus-agent-'+'b'*32+'\nlarpus-agent-'+'c'*32+'\nlarpus-voice-'+'d'*32+'\nlarpus-voice\nlarpus-agent-before-x'
        calls=[]
        def podman(*args,**kw):
            calls.append(args);return running if args[0]=='ps' else ''
        with p.object(m,'read',return_value={'id':'a'*32,'previous':'b'*32}),p.object(m,'keep_names',return_value={'larpus-model','larpus-agent-'+'a'*32,'larpus-agent-'+'b'*32,'larpus-voice-'+'d'*32}),p.object(m,'podman',side_effect=podman),p.object(m,'release_path',return_value=P(__file__)),p.object(m,'STORE',P(__file__).parent/'__no_releases__'):
            stopped=m.prune()
        self.assertEqual(sorted(stopped),sorted(['larpus-agent-'+'c'*32,'larpus-voice','larpus-agent-before-x']))
        self.assertNotIn('rm',[c[0] for c in calls])
        self.assertNotIn('4c73-infra',stopped);self.assertNotIn('larpus-model',stopped)
