"""Owner-local provenance for benchmark runs; no mutation or model switching."""
import configparser
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def read_json(opener,path):
    with opener.open('http://127.0.0.1:8080'+path,timeout=15) as response:
        raw=response.read(1000001)
        if len(raw)>1000000:raise ValueError('Oversized station metadata')
        return json.loads(raw)


def snapshot(opener):
    pointer=json.loads((ROOT/'data/releases/active.json').read_text());release=ROOT/'data/releases'/pointer['id']
    selected=read_json(opener,'/api/model-selection');health=read_json(opener,'/api/health')
    catalog=json.loads((release/'config/model-selection.json').read_text())['models']
    tag=catalog[selected['active_id']]['tag']
    if selected['phase']!='ready' or health.get('model_processors',{}).get(tag)!='GPU':raise ValueError('Station is not ready on GPU')
    identity={'release':pointer['id'],'gateway_pid':pointer['pid'],'source_fingerprint':json.loads((release/'release.json').read_text())['source_fingerprint'],
              'model_id':selected['active_id'],'model_weight_sha256':catalog[selected['active_id']]['weight_sha256'],
              'model_operation':selected['operation_id'],'context':catalog[selected['active_id']]['context'],
              'retrieval':json.loads((release/'config/cpu-retrieval.json').read_text())['runtime'],
              'database_sha256':json.loads((release/'knowledge/manifest.json').read_text())['database_sha256']}
    identity['embedding_manifest_sha256']=hashlib.sha256((release/'knowledge/embeddings-manifest.json').read_bytes()).hexdigest()
    notes=release/'knowledge/notes-manifest.json'
    identity['notes_manifest_sha256']=hashlib.sha256(notes.read_bytes()).hexdigest() if notes.exists() else None
    if (release/'runtime/scoring_pipeline.py').exists():
        pipeline=read_json(opener,'/api/retrieval-pipeline')
        identity['scoring_pipeline']={key:pipeline[key] for key in ('active_id','requested_id','workers')}
        identity['assembly_manifest_sha256']=hashlib.sha256((release/'runtime/native/manifest.json').read_bytes()).hexdigest()
    settings=configparser.ConfigParser();settings.read(Path.home()/'.wslconfig')
    identity['wsl_processors_configured']=settings.getint('wsl2','processors',fallback=None)
    return identity


def host_environment():
    result={'platform':sys.platform,'python':sys.version.split()[0],'wsl_processors_observed':None}
    if sys.platform=='win32':
        count=subprocess.run(['wsl.exe','--distribution','Larpus','--user','larpus','--exec','/usr/bin/nproc','--all'],capture_output=True,text=True,timeout=20,check=True)
        result['wsl_processors_observed']=int(count.stdout.strip())
    return result
