import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('model_cache',Path(__file__).resolve().parents[1]/'scripts/model-cache.py')
cache=importlib.util.module_from_spec(spec);spec.loader.exec_module(cache)

class ModelCacheTests(unittest.TestCase):
    def test_candidate_has_no_swap_or_new_network_and_readonly_models(self):
        profile={'model_image':'a'*64,'gpu_driver':'/usr/lib/wsl/drivers/nv_test.inf_amd64_'+'b'*16}
        with patch.object(cache.r,'podman') as command:cache.create(profile,'q4_0')
        args=command.call_args.args
        for option in ('--memory=32g','--memory-swap=32g','--read-only','OLLAMA_NO_CLOUD=1','OLLAMA_KV_CACHE_TYPE=q4_0','OLLAMA_NUM_PARALLEL=1','OLLAMA_FLASH_ATTENTION=1','--mount=type=bind,src=/home/larpus/models,dst=/models,ro'):self.assertIn(option,args)
        self.assertNotIn('--network=host',args)
        self.assertIn('larpus-offline',args)

    def test_gpu_or_context_mismatch_never_passes(self):
        for result in ({'full_gpu':False,'context':262144},{'full_gpu':True,'context':4096}):
            with patch.object(cache.r,'read',return_value={}),patch.object(cache.r,'podman',return_value=json.dumps(result)):
                with self.assertRaises(ValueError):cache.probe(Path('.'),262144)

    def test_failed_probe_restores_previous_container(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);state=root/'maintenance';active={'id':'a'*32,'pid':1}
            def read(path):return active if path.name=='active.json' else {'model_image':'b'*64}
            with patch.object(cache,'STATE',state),patch.object(cache,'create'),patch.object(cache,'probe',side_effect=[{'baseline':True},ValueError('full GPU failed'),{'restored':True}]),patch.object(cache.r,'read',side_effect=read),patch.object(cache.r,'release_path',return_value=root),patch.object(cache.r,'validate'),patch.object(cache.r,'run'),patch.object(cache.r,'write'),patch.object(cache.r,'stop'),patch.object(cache.r,'podman',return_value='[{}]') as command,patch.object(cache.r,'running',return_value=False),patch.object(cache.r,'launch',return_value=active),patch.object(cache.r,'ready'):
                with self.assertRaises(ValueError):cache.apply('q4_0')
            self.assertIn(('rename',cache.BACKUP,'larpus-model'),[c.args for c in command.call_args_list])
            self.assertIn(('rm','larpus-model'),[c.args for c in command.call_args_list])
