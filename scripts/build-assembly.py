"""Owner build only: pinned Linux Zig toolchain, no runtime compiler or downloads."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from runtime.isolation import wsl_command

def run(*args,input=None):
 result=subprocess.run(wsl_command(*args),input=input,capture_output=True,timeout=180,check=True)
 return result.stdout

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--zig',default='/home/larpus/native-assembly-build/zig-0.17.0/zig')
 args=parser.parse_args();dest='/home/larpus/native-assembly-build/work'
 source=ROOT/'runtime/native/score_half.S';directory=source.parent
 run('/bin/mkdir','-p',dest)
 run('/usr/bin/tee',dest+'/score_half.S',input=source.read_bytes())
 version=run(args.zig,'version').decode().strip()
 if version!='0.17.0':raise ValueError('Expected pinned Zig 0.17.0')
 run('/usr/bin/env','ZIG_GLOBAL_CACHE_DIR='+dest+'/cache','ZIG_LOCAL_CACHE_DIR='+dest+'/local-cache',
     args.zig,'cc','-target','x86_64-linux-gnu','-shared','-nostdlib','-O3',
     '-Wl,--build-id=none,-z,now,-z,relro,-z,noexecstack',dest+'/score_half.S','-o',dest+'/liblarpus_score.so')
 artifact=run('/bin/cat',dest+'/liblarpus_score.so')
 if not artifact.startswith(b'\x7fELF'):raise ValueError('Not an ELF artifact')
 (directory/'liblarpus_score.so').write_bytes(artifact)
 spec={'version':1,'sha256':hashlib.sha256(artifact).hexdigest(),'bytes':len(artifact),
       'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'compiler':'Zig '+version,
       'target':'x86_64-linux-gnu','workers':4}
 (directory/'manifest.json').write_text(json.dumps(spec,indent=2)+'\n')
 print(json.dumps(spec))

if __name__=='__main__':main()
