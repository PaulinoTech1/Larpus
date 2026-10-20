import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_isolation
from runtime import isolation, skills
from runtime import inference, knowledge
import test_optimized_pipeline
import test_retrieval_worker
from runtime.source_integrity import fingerprint


class ExecutionModularityTests(unittest.TestCase):
    def test_optional_fallbacks_are_retained_for_every_profile(self):
        for profile in ('verified','ultra-fast','diagnostic'):
            def augment(messages,persona,timings=None):
                test_optimized_pipeline.OptimizedPipelineTests().test_failure_disables_only_optimized_and_uses_numpy()
                test_retrieval_worker.RetrievalWorkerTests().test_worker_failure_mid_chat_keeps_bm25_order()
                with tempfile.TemporaryDirectory() as temporary,patch.object(knowledge,'DIRECTORY',Path(temporary)):
                    self.assertIsNone(knowledge.notes_database())
                return messages,[]
            # Release is a stub here: this test isolates optional components;
            # real screening/storage faults are covered in execution_security.
            with patch.object(inference,'augment',side_effect=augment) as retrieval,patch.object(inference,'active_model',return_value='qwen3.5:27b-q4_K_M'),patch.object(inference,'gpu_placement',return_value='GPU'),patch.object(inference,'ollama',return_value={'message':{'content':'Useful reply.'}}),patch.object(inference,'gate',side_effect=lambda content,system:{'status':200,'content':content}):
                result=inference.chat('home-assistant',[{'role':'user','content':'Hello'}],execution={'profile':profile})
                self.assertEqual(result['status'],200)
                retrieval.assert_called_once()

    def test_all_new_reachable_security_modules_are_scanned(self):
        source=Path('runtime/security_scan.py').read_text(encoding='utf-8')
        for name in ('source_integrity.py','execution_profiles.py','execution_trace.py','execution_preflight.py','isolation_probe.py'):
            self.assertIn(repr(name),source)

    def test_consistent_optional_skill_removal_and_tamper(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            folder=root/'example'
            folder.mkdir()
            path=folder/'SKILL.md'
            path.write_bytes(b'---\nname: example\ndescription: Test\n---\nOffer a useful explanation.\n')
            registry=root/'registry.json'
            entry={'id':'example','name':'Example','description':'Test','origin':'local-authored','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
            registry.write_text(json.dumps({'version':1,'skills':[entry]}))
            with patch.object(skills,'SKILLS',root),patch.object(skills,'REGISTRY',registry):
                self.assertEqual(set(skills.load_skills()),{'example'})
                path.write_text('changed')
                with self.assertRaises(ValueError):skills.load_skills()
                # Reviewed removal updates both registration and persona allowlist.
                registry.write_text(json.dumps({'version':1,'skills':[]}))
                path.unlink()
                folder.rmdir()
                self.assertEqual(skills.load_skills(),{})
                self.assertEqual(skills.selected_prompt({'skills':[]},None),'')
                with self.assertRaises(ValueError):skills.selected_prompt({'skills':[]},'example')

    def observations(self,driver):
        infra='d'*64
        containers=[]
        for name,model in (('larpus-agent',False),('larpus-model',True)):
            item=test_isolation.fixture(model)
            item.update(Name=name,Pod='c'*64)
            item['HostConfig']['NetworkMode']='container:'+infra
            if model:item['Mounts'].append({'Type':'bind','Source':driver,'Destination':driver,'RW':False})
            containers.append(item)
        oci=[]
        for model in (False,True):
            oci.append({'value':{'root':{'readonly':True},'process':{'noNewPrivileges':True,'capabilities':{}},'mounts':[{'type':'bind','source':'/dev/dxg'}] if model else []}})
        return {'info':{'host':{'security':{'rootless':True}}},'containers':containers,'oci':oci,
                'pod':{'InfraConfig':{'HostNetwork':False,'Networks':[]},'InfraContainerID':infra},
                'infra':{'HostConfig':{'NetworkMode':'none'}}}

    def test_shared_validator_acceptance_and_rejection_matrix(self):
        driver='/usr/lib/wsl/drivers/nv_test.inf_amd64_'+'b'*16
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            profile={'version':1,'distro':'Larpus','user':'larpus','gpu_driver':driver,
                     'agent_image':'a'*64,'model_image':'a'*64,'source_fingerprint':fingerprint(root)}
            path=root/'deployment.json'
            path.write_text(json.dumps(profile))
            good=self.observations(driver)
            mutations=[('info','rootless'),('agent','privilege'),('agent','memory'),
                       ('model','image'),('model','caps'),('pod','network'),('infra','network')]
            with patch.object(isolation,'ROOT',root),patch.object(isolation,'PROFILE',path):
                for fast in (False,True):
                    with patch.object(isolation,'collect_observations',return_value=good):
                        self.assertEqual(isolation.preflight(fast=fast),profile)
                    for area,kind in mutations:
                        bad=copy.deepcopy(good)
                        if area=='info':bad['info']['host']['security']['rootless']=False
                        elif area=='pod':bad['pod']['InfraConfig']['HostNetwork']=True
                        elif area=='infra':bad['infra']['HostConfig']['NetworkMode']='host'
                        else:
                            target=bad['containers'][area=='model']
                            if kind=='privilege':target['HostConfig']['Privileged']=True
                            elif kind=='memory':target['HostConfig']['Memory']=0
                            elif kind=='image':target['Image']='e'*64
                            else:target['HostConfig']['CapDrop']=[]
                        with self.subTest(fast=fast,mutation=kind),patch.object(isolation,'collect_observations',return_value=bad):
                            with self.assertRaises(ValueError):isolation.preflight(fast=fast)
