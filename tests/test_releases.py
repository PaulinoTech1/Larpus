import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('releases',Path(__file__).resolve().parents[1]/'scripts/releases.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

class ReleaseTests(unittest.TestCase):
    def test_readiness_uses_functional_station_health(self):
        import io
        names=('password','local_skills','approved_knowledge','input_filter','output_dlp','mcp_surface','models','model_gpu','egress_enforcement','voice')
        body=json.dumps({'checks':[{'name':name,'status':'pass'} for name in names]}).encode()
        with patch.object(release,'running',return_value=True),patch.object(release.HTTP,'open',return_value=io.BytesIO(body)) as request:
            release.ready({'port':8080})
            self.assertEqual(request.call_args.args[0],'http://127.0.0.1:8080/api/station-health')

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
        with tempfile.TemporaryDirectory() as directory,patch.object(release,'STORE',Path(directory)),patch.object(release,'validate'),patch.object(release,'run'),patch.object(release,'stop') as stop,patch.object(release,'running',return_value=False),patch.object(release,'launch') as launch,patch.object(release,'ready',side_effect=[RuntimeError('candidate failed'),None]):
            old={'id':'a'*32,'pid':1,'process':{},'host':'192.168.1.2','subnet':'192.168.1.0/24','port':8080}
            new={**old,'id':'b'*32,'pid':2};restored={**old,'pid':3}
            release.write(Path(directory)/'active.json',old);launch.side_effect=[new,restored]
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
