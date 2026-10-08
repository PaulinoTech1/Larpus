import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from runtime import skills,health
from runtime.agents import load_personas,messages_for
from runtime.auth import password_record
from runtime.security_scan import write_json

class LocalSkillTests(unittest.TestCase):
    def test_local_skill_changes_system_prompt_only(self):
        persona=load_personas()['it-larp-coach']
        history=[{'role':'user','content':'Let us practice DNS troubleshooting.'}]
        prepared=messages_for(persona,history,'it-interview')
        self.assertIn('score it out of ten',prepared[0]['content'])
        self.assertEqual(prepared[1],history[0])
        with self.assertRaises(ValueError):
            messages_for(persona,history,'home-planning')

    def test_registry_rejects_drift_imports_and_extra_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'example';folder.mkdir()
            file=folder/'SKILL.md';file.write_bytes(b'---\nname: example\ndescription: Test\n---\nHelp plan an evening.\n')
            entry={'id':'example','name':'Example','description':'Test','origin':'local-authored','sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
            registry=root/'registry.json'
            write_json(registry,{'version':1,'skills':[entry]})
            with patch.object(skills,'SKILLS',root),patch.object(skills,'REGISTRY',registry):
                self.assertEqual(set(skills.load_skills()),{'example'})
                file.write_text('changed',encoding='utf-8')
                with self.assertRaises(ValueError):
                    skills.load_skills()
                file.write_bytes(b'---\nname: example\ndescription: Test\n---\nHelp plan an evening.\n')
                (folder/'run.py').write_text('print(1)')
                with self.assertRaises(ValueError):
                    skills.load_skills()
                (folder/'run.py').unlink()
                entry['origin']='downloaded'
                write_json(registry,{'version':1,'skills':[entry]})
                with self.assertRaises(ValueError):
                    skills.load_skills()

    def test_scanner_wrapper_denies_network_in_real_process(self):
        code="import sys,socket;from scripts.offline_skillspector import deny_network;sys.addaudithook(deny_network);socket.create_connection(('127.0.0.1',9),timeout=1)"
        result=subprocess.run([sys.executable,'-c',code],cwd=skills.ROOT,capture_output=True,text=True,timeout=5)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Larpus scanner policy denies network',result.stderr)

class HealthTests(unittest.TestCase):
    def setUp(self):
        fixture_mode=patch.dict('os.environ',{'LARPUS_ISOLATION':'host'})
        fixture_mode.start();self.addCleanup(fixture_mode.stop)

    def test_unverified_is_never_green_and_mcp_drift_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);password=root/'password.json';approved=root/'approved.json'
            write_json(password,password_record('test-password-only'))
            tools=[{'name':name} for name in ('chat_local','list_personas','local_status')]
            write_json(approved,{'tools':tools})
            write_json(root/'summary.json',{'fingerprint':'fixture','status':'pass'})
            with patch.object(health,'PASSWORD_FILE',password),patch.object(health,'APPROVED',approved),patch.object(health,'LATEST',root/'health.json'),patch.object(health,'DATA',root),patch.object(health,'discover',return_value=tools),patch.object(health,'model_health',return_value={'ollama':'online','models':['qwen2.5:14b']}),patch.object(health,'fingerprint',return_value='fixture'),patch.object(health.shutil,'which',return_value=None):
                report=health.check(False)
                self.assertEqual(report['status'],'degraded')
                self.assertTrue(any(c['status']=='unverified' for c in report['checks']))
                with patch.object(health,'discover',return_value=[{'name':'fetch_url'}]):
                    report=health.check(False)
                    self.assertEqual(report['status'],'error')

    def test_missing_latest_is_stale(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(health,'LATEST',Path(temp)/'missing.json'):
            self.assertEqual(health.read_latest()['status'],'stale')
