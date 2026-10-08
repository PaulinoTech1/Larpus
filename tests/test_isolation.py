import copy
import json
import unittest
from unittest.mock import patch
from runtime import isolation,mcp_client

def fixture(model=False):
    mounts=[{'Type':'bind','Destination':'/models','Source':'/home/larpus/models','RW':False},{'Type':'bind','Destination':'/usr/lib/wsl/lib','Source':'/usr/lib/wsl/lib','RW':False}] if model else [{'Type':'volume','Name':'larpus-quarantine','Destination':'/app/data/quarantine','RW':True,'Options':['noexec','nosuid','nodev']}]
    return {'State':{'Running':True},'Image':'sha256:'+'a'*64,'Config':{'User':'1000:1000'},'Mounts':mounts,'HostConfig':{'ReadonlyRootfs':True,'Privileged':False,'PortBindings':{},'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges'],'Memory':1073741824,'PidsLimit':64,'Devices':[{'PathOnHost':'/dev/dxg'}] if model else []}}

class IsolationTests(unittest.TestCase):
    def test_rootless_oci_gpu_binding_requires_narrow_driver_mount(self):
        driver='/usr/lib/wsl/drivers/nv_dispi.inf_amd64_'+'b'*16
        item=fixture(True);item['HostConfig']['Devices']=[]
        item['Mounts'].append({'Type':'bind','Source':driver,'Destination':driver,'RW':False})
        oci={'root':{'readonly':True},'process':{'noNewPrivileges':True,'capabilities':{}},'mounts':[{'type':'bind','source':'/dev/dxg','destination':'/dev/dxg'}]}
        isolation.validate_container(item,'sha256:'+'a'*64,True,oci,driver)
        oci['mounts'].append({'type':'bind','source':'/dev/sda','destination':'/dev/sda'})
        with self.assertRaises(ValueError):
            isolation.validate_container(item,'sha256:'+'a'*64,True,oci,driver)

    def test_exact_model_guard_mounts_and_security_required(self):
        for model in (False,True):
            isolation.validate_container(fixture(model),'sha256:'+'a'*64,model)
            for key,value in (('Privileged',True),('ReadonlyRootfs',False),('CapDrop',[]),('SecurityOpt',[]),('PidMode','host'),('PortBindings',{'11434/tcp':[{}]}),('Memory',0)):
                item=fixture(model);item['HostConfig'][key]=value
                with self.assertRaises(ValueError):
                    isolation.validate_container(item,'sha256:'+'a'*64,model)
        item=fixture();item['HostConfig']['CapDrop']=['CAP_CHOWN'];item['EffectiveCaps']=None;item['BoundingCaps']=None
        isolation.validate_container(item,'sha256:'+'a'*64,False)
        item['BoundingCaps']=['CAP_CHOWN']
        with self.assertRaises(ValueError):
            isolation.validate_container(item,'sha256:'+'a'*64,False)
        item=fixture(True);item['Mounts'][0]['Source']='/home/owner'
        with self.assertRaises(ValueError):
            isolation.validate_container(item,'sha256:'+'a'*64,True)
        item=fixture(True);item['Mounts'].append(fixture()['Mounts'][0])
        with self.assertRaises(ValueError):
            isolation.validate_container(item,'sha256:'+'a'*64,True)

    def test_unknown_mode_and_missing_executor_never_fall_back(self):
        with patch.dict('os.environ',{'LARPUS_ISOLATION':'mistyped'}):
            with self.assertRaises(ValueError):
                mcp_client.child_parameters()
        with patch.dict('os.environ',{'LARPUS_ISOLATION':'wsl-podman'}),patch.object(mcp_client,'child_args',side_effect=OSError('missing distro')):
            with self.assertRaises(OSError):
                mcp_client.child_parameters()

    def test_isolated_stdio_has_no_shell_or_extra_env(self):
        command=['wsl.exe','--distribution','Larpus','--user','larpus','--exec','podman','exec','--interactive','larpus-agent','python','-m','runtime.mcp_server']
        with patch.dict('os.environ',{'LARPUS_ISOLATION':'wsl-podman','SECRET':'private'}),patch.object(mcp_client,'child_args',return_value=command):
            parameters=mcp_client.child_parameters()
            self.assertEqual(parameters.command,'wsl.exe')
            self.assertEqual(parameters.args,command[1:])
            self.assertNotIn('SECRET',parameters.env)
