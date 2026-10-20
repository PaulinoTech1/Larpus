"""Binary-safe source transfer over WSL stdin after drive mounts are disabled."""
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime.isolation import wsl_command
from runtime.station_paths import ROOT

with (ROOT/'data/isolated-source.tar').open('rb') as source:
    subprocess.run(wsl_command('/bin/tar','-xf','-','-C','/home/larpus/build'),stdin=source,check=True,timeout=60)
print('Fixed source archive transferred through stdio; no Windows drive mount enabled.')
