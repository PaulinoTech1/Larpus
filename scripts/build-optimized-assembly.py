"""Owner-only reproducible optimized scorer build on the registered E: WSL disk."""
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.assembly_lab import e_path,registered_on_e
from runtime.isolation import wsl_command

def run(*args,input=None):
 return subprocess.run(wsl_command(*args),input=input,capture_output=True,check=True,timeout=300).stdout

def main():
 e_path(ROOT);disk=registered_on_e()
 directory=ROOT/'runtime/native';dest='/home/larpus/native-assembly-build/optimized-v1'
 zig='/home/larpus/native-assembly-build/zig-0.17.0/zig'
 run('/bin/mkdir','-p',dest+'/tmp')
 sources={name:(directory/name).read_bytes() for name in ('pool.c','score_half.S','score_float.S')}
 for name,raw in sources.items():run('/usr/bin/tee',dest+'/'+name,input=raw)
 version=run(zig,'version').decode().strip()
 if version!='0.17.0':raise ValueError('Expected pinned Zig 0.17.0')
 args=['cc','-target','x86_64-linux-gnu','-mcpu=znver3','-O3','-fPIC','-shared','-pthread','-Wl,--build-id=none,-z,now,-z,relro,-z,noexecstack',*[dest+'/'+name for name in sources],'-o',dest+'/liblarpus_pool.so']
 run('/usr/bin/env','TMPDIR='+dest+'/tmp','ZIG_GLOBAL_CACHE_DIR='+dest+'/cache','ZIG_LOCAL_CACHE_DIR='+dest+'/cache/local',zig,*args)
 binary=run('/bin/cat',dest+'/liblarpus_pool.so')
 if not binary.startswith(b'\x7fELF'):raise ValueError('Not an ELF artifact')
 spec={'version':1,'sha256':hashlib.sha256(binary).hexdigest(),'bytes':len(binary),'compiler':'Zig '+version,'compiler_sha256':run('/usr/bin/sha256sum',zig).decode().split()[0],'target':'x86_64-linux-gnu','workers':4,'mode':'aligned-half','sources':{name:hashlib.sha256(raw).hexdigest() for name,raw in sources.items()},'arguments':args,'wsl_disk':disk}
 for name,raw in sources.items():
  if raw!=(directory/name).read_bytes():raise ValueError('Source changed during build')
 (directory/'liblarpus_pool.so').write_bytes(binary)
 (directory/'optimized-manifest.json').write_text(json.dumps(spec,indent=2)+'\n')
 print(json.dumps(spec))

if __name__=='__main__':main()
