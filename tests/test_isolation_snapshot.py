import json
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from unittest.mock import mock_open
import configparser
import pathlib
import sys
from runtime import isolation


class SnapshotTests(unittest.TestCase):
    def fixture(self):
        names=['larpus-agent-'+'a'*32,'larpus-model']
        containers=[{'Name':name,'Id':c*64,'OCIConfigPath':'/home/larpus/.local/share/containers/storage/overlay-containers/'+c*64+'/userdata/config.json','Pod':'c'*64} for name,c in zip(names,'ab')]
        return names,{'info':{},'containers':containers,'oci':[{'path':c['OCIConfigPath'],'value':{}} for c in containers],'pod':{'Id':'c'*64,'InfraContainerID':'d'*64},'infra':{'Id':'d'*64}}

    def test_one_fresh_launch_returns_every_observation(self):
        self.assertTrue(hasattr(isolation,'read_snapshot'),'Fresh isolation observations should use one bounded WSL launch')
        names,value=self.fixture()
        with patch.object(isolation,'wsl_command',return_value=['fixed']) as command,patch.object(isolation.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps(value).encode())) as run:
            for _ in range(2):self.assertEqual(isolation.read_snapshot(names),value)
        self.assertEqual(run.call_count,2)  # never cache security observations
        self.assertEqual(command.call_args.args[:2],('python3','-c'))
        self.assertEqual(json.loads(command.call_args.args[-1]),names)
        self.assertTrue(run.call_args.kwargs['check'])
        self.assertLessEqual(run.call_args.kwargs['timeout'],90)

    def test_partial_reordered_or_mismatched_observations_reject(self):
        self.assertTrue(hasattr(isolation,'read_snapshot'))
        names,value=self.fixture()
        bad=[{**value,'containers':value['containers'][::-1]}, {**value,'oci':value['oci'][::-1]}, {**value,'infra':{'Id':'e'*64}}, {**value,'pod':{'Id':'e'*64,'InfraContainerID':'d'*64}}, {k:v for k,v in value.items() if k!='info'}]
        for payload in bad:
            with self.subTest(payload=payload),patch.object(isolation,'wsl_command',return_value=['fixed']),patch.object(isolation.subprocess,'run',return_value=SimpleNamespace(stdout=json.dumps(payload).encode())):
                with self.assertRaises((ValueError,KeyError)):isolation.read_snapshot(names)

    def test_invalid_names_reject_before_launch(self):
        self.assertTrue(hasattr(isolation,'read_snapshot'))
        for names in ([],['--privileged'],['larpus-model']*5,['larpus-model']*2):
            with patch.object(isolation.subprocess,'run') as run:
                with self.assertRaises(ValueError):isolation.read_snapshot(names)
                run.assert_not_called()

    def test_failures_have_no_partial_or_cached_fallback(self):
        self.assertTrue(hasattr(isolation,'read_snapshot'))
        names,_=self.fixture()
        for failure in (subprocess.CalledProcessError(1,['fixed']),subprocess.TimeoutExpired(['fixed'],60)):
            with patch.object(isolation,'wsl_command',return_value=['fixed']),patch.object(isolation.subprocess,'run',side_effect=failure):
                with self.assertRaises(type(failure)):isolation.read_snapshot(names)
        with patch.object(isolation,'wsl_command',return_value=['fixed']),patch.object(isolation.subprocess,'run',return_value=SimpleNamespace(stdout=b'x'*8_200_001)):
            with self.assertRaises(ValueError):isolation.read_snapshot(names)

    def execute_probe(self,fail_policy=False,oversized=False):
        from runtime.isolation_probe import CODE
        names,value=self.fixture();queries=[]
        config=configparser.ConfigParser();config.read_string('[automount]\nenabled=false\nmountFsTab=false\n[interop]\nenabled=false\nappendWindowsPath=false')
        replies=[value['info'],value['containers'],value['pod'],[value['infra']]]
        def run(command,**kwargs):
            queries.append((command,kwargs))
            return SimpleNamespace(stdout=json.dumps(replies[len(queries)-1]).encode())
        raw=b'x'*1_000_001 if oversized else b'{}'
        with patch('configparser.ConfigParser',return_value=config),patch.object(config,'read'),patch.object(pathlib.Path,'exists',return_value=fail_policy),patch.object(subprocess,'run',side_effect=run),patch('builtins.open',mock_open(read_data=raw)),patch.object(sys,'argv',['probe',json.dumps(names)]),patch('builtins.print') as output:
            exec(compile(CODE,'<fixed-isolation-probe>','exec'),{})
        return names,value,queries,json.loads(output.call_args.args[0])

    def test_fixed_probe_collects_bounded_current_state(self):
        names,value,queries,actual=self.execute_probe()
        self.assertEqual(actual,value)
        self.assertEqual([q[0][1:] for q in queries],[['info','--format','json'],['inspect',*names],['pod','inspect','c'*64],['inspect','d'*64]])
        for command,kwargs in queries:
            self.assertEqual(command[0],'/usr/bin/podman')
            self.assertEqual(kwargs['timeout'],15);self.assertTrue(kwargs['check'])
            self.assertEqual(kwargs['env']['XDG_RUNTIME_DIR'],'/run/user/1000')

    def test_fixed_probe_rejects_distro_exposure_and_large_oci(self):
        with self.assertRaises(AssertionError):self.execute_probe(fail_policy=True)
        with self.assertRaises(ValueError):self.execute_probe(oversized=True)
