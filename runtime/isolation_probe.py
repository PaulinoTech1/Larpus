"""Fixed read-only WSL observation program; host retains all policy decisions."""

CODE = r'''import configparser,json,os,pathlib,re,subprocess,sys
def query(*args):
 result=subprocess.run(['/usr/bin/podman',*args],env={**os.environ,'XDG_RUNTIME_DIR':'/run/user/1000'},capture_output=True,check=True,timeout=15)
 if len(result.stdout)>1000000:raise ValueError('Oversized isolation response')
 return json.loads(result.stdout)
def identifier(value):
 if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{64}',value):raise ValueError('Invalid isolation identity')
 return value
def observe(names):
 c=configparser.ConfigParser();c.read('/etc/wsl.conf')
 assert not c.getboolean('automount','enabled')
 assert not c.getboolean('automount','mountFsTab')
 assert not c.getboolean('interop','enabled')
 assert not c.getboolean('interop','appendWindowsPath')
 assert not pathlib.Path('/mnt/c').exists()
 assert not pathlib.Path('/mnt/e').exists()
 assert not pathlib.Path('/proc/sys/fs/binfmt_misc/WSLInterop').exists()
 info=query('info','--format','json')
 containers=query('inspect',*names);oci=[]
 for item in containers:
  path='/home/larpus/.local/share/containers/storage/overlay-containers/'+identifier(item['Id'])+'/userdata/config.json'
  if item.get('OCIConfigPath')!=path:raise ValueError('Unexpected OCI configuration path')
  with open(path,'rb') as stream:raw=stream.read(1000001)
  if len(raw)>1000000:raise ValueError('Oversized OCI configuration')
  oci.append({'path':path,'value':json.loads(raw)})
 model=next(item for item in containers if item['Name'].lstrip('/')=='larpus-model')
 pod=query('pod','inspect',identifier(model['Pod']))
 infra=query('inspect',identifier(pod['InfraContainerID']))
 if not isinstance(infra,list) or len(infra)!=1:raise ValueError('Invalid infra observation')
 return {'info':info,'containers':containers,'oci':oci,'pod':pod,'infra':infra[0]}
print(json.dumps(observe(json.loads(sys.argv[1]))))
'''
