"""Owner-only CPU retrieval preparation. Never imported by the model runtime.

fetch   ONLINE, owner-approved: pinned wheels (no dependencies) and pinned
        Hugging Face model revisions, each verified against config/cpu-retrieval.json.
verify  Offline re-verification of every fetched artifact.
install-host  Offline install of the pinned Windows wheels for owner tools/tests.
sync    Copy verified Linux wheels/models into the WSL build cache with SHA256SUMS.
index   Offline: embed every approved passage on all CPU cores into a hash-pinned
        knowledge/embeddings.npy bound to approved.sqlite.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from runtime import retrieval  # noqa: E402

WHEELS=ROOT/'vendor/retrieval-wheels'
MODELS=retrieval.MODELS
HOSTS={'huggingface.co','pypi.org','files.pythonhosted.org'}

def fetch_url(url,dest,spec):
    if urllib.parse.urlsplit(url).hostname not in HOSTS:raise ValueError('Unreviewed host: '+url)
    dest.parent.mkdir(parents=True,exist_ok=True);part=dest.with_name(dest.name+'.part')
    with urllib.request.urlopen(url,timeout=60) as response,part.open('wb') as out:shutil.copyfileobj(response,out,1<<20)
    try:retrieval.verify_file(part,spec)
    except ValueError:part.unlink(missing_ok=True);raise
    part.replace(dest)

def wheel_specs(config):
    for name,package in config['packages'].items():
        for platform,wheel in package['wheels'].items():yield name,package['version'],platform,wheel

def fetch(config):
    for name,version,platform,wheel in wheel_specs(config):
        dest=WHEELS/platform/wheel['file']
        try:retrieval.verify_file(dest,wheel);continue
        except ValueError:pass
        release=json.load(urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json',timeout=60))
        url=next(f['url'] for f in release['urls'] if f['filename']==wheel['file'] and f['digests']['sha256']==wheel['sha256'])
        fetch_url(url,dest,wheel);print('fetched',dest.relative_to(ROOT))
    for role,model in config['models'].items():
        for name,spec in model['files'].items():
            dest=MODELS/model['directory']/name
            try:retrieval.verify_file(dest,spec);continue
            except ValueError:pass
            fetch_url(f"https://huggingface.co/{model['repository']}/resolve/{model['revision']}/{spec['upstream']}",dest,spec);print('fetched',dest.relative_to(ROOT))

def verify(config):
    for _,_,platform,wheel in wheel_specs(config):retrieval.verify_file(WHEELS/platform/wheel['file'],wheel)
    for role in config['models']:retrieval.verify_model(config,role)
    print('All pinned retrieval wheels and model files verified.')

def install_host(config):
    verify(config)
    files=[str(WHEELS/'win-cp310'/w['file']) for _,_,p,w in wheel_specs(config) if p=='win-cp310']
    subprocess.run([sys.executable,'-m','pip','install','--no-index','--no-deps',*files],check=True)

def wsl(*args,input_file=None):
    command=[str(Path(os.environ['SYSTEMROOT'])/'System32/wsl.exe'),'--distribution','Larpus','--user','larpus','--exec',*args]
    subprocess.run(command,stdin=input_file,check=True,timeout=900)

def sync(config):
    """Feed the sealed image build. Linux wheels join runtime-wheels; models get their own SUMS."""
    verify(config)
    with tempfile.TemporaryDirectory() as temporary:
        archive=Path(temporary)/'retrieval.tar'
        with tarfile.open(archive,'w') as tar:
            for _,_,platform,wheel in wheel_specs(config):
                if platform=='linux-cp312':tar.add(WHEELS/platform/wheel['file'],arcname='runtime-wheels/'+wheel['file'])
            for model in config['models'].values():
                for name in model['files']:tar.add(MODELS/model['directory']/name,arcname='retrieval-models/'+model['directory']+'/'+name)
        with archive.open('rb') as source:wsl('/bin/tar','-xf','-','-C','/home/larpus/build/vendor',input_file=source)
    wsl('/bin/sh','-c','cd /home/larpus/build/vendor/runtime-wheels && sha256sum *.whl > SHA256SUMS && sha256sum --strict --check --quiet SHA256SUMS')
    wsl('/bin/sh','-c','cd /home/larpus/build/vendor/retrieval-models && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS && sha256sum --strict --check --quiet SHA256SUMS')
    lines=[]
    for model in config['models'].values():
        for name,spec in model['files'].items():lines.append(spec['sha256']+'  ./'+model['directory']+'/'+name)
    with tempfile.NamedTemporaryFile('w',delete=False,newline='\n') as pins:pins.write('\n'.join(lines)+'\n')
    with open(pins.name,'rb') as source:wsl('/bin/sh','-c','cd /home/larpus/build/vendor/retrieval-models && sha256sum --strict --check --quiet -',input_file=source)
    os.unlink(pins.name)
    print('WSL build cache updated and verified against config/cpu-retrieval.json.')

def build_index(config,workers):
    import numpy
    from runtime import knowledge
    from contextlib import closing
    directory=knowledge.DIRECTORY
    library=json.loads((directory/'manifest.json').read_bytes())
    with closing(knowledge.database()) as connection:  # hash-verified immutable DB
        rows=connection.execute('SELECT rowid,source_id,locator,title,text FROM chunks ORDER BY rowid').fetchall()
    unique={}
    for rowid,source,locator,title,text in rows:unique.setdefault((source,locator,text),(rowid,(title or '')+'\n'+text))
    items=sorted(unique.values(),key=lambda pair:len(pair[1]))
    print(f'{len(rows)} passages, {len(items)} unique; embedding with {workers} workers',flush=True)
    # One session per worker: concurrent runs on a shared session would share
    # (and serialise on) a single intra-op thread pool.
    threads=max(1,(os.cpu_count() or 4)//workers);local=threading.local()
    batches=[items[i:i+32] for i in range(0,len(items),32)]
    started=time.monotonic();done=[0]
    def work(batch):
        if not hasattr(local,'embedder'):local.embedder=retrieval.Embedder(config,threads)
        vectors=local.embedder.encode([text for _,text in batch])
        done[0]+=len(batch)
        if done[0]%4096<len(batch):print(f'  {done[0]}/{len(items)} in {time.monotonic()-started:.0f}s',flush=True)
        return vectors
    with ThreadPoolExecutor(workers) as pool:vectors=numpy.concatenate(list(pool.map(work,batches))).astype(numpy.float16)
    rowids=numpy.array([rowid for rowid,_ in items],dtype=numpy.int64)
    order=numpy.argsort(rowids,kind='stable');rowids=rowids[order];vectors=vectors[order]
    temp_vectors=directory/'embeddings.build.npy';temp_rowids=directory/'embeddings-rowids.build.npy'
    numpy.save(temp_vectors,vectors,allow_pickle=False);numpy.save(temp_rowids,rowids,allow_pickle=False)
    if json.loads((directory/'manifest.json').read_bytes())!=library:raise ValueError('Approved database changed during index build')
    manifest={'version':1,'built_on':time.strftime('%Y-%m-%d'),'database_sha256':library['database_sha256'],
        'embedder':config['models']['embedder']['repository'],'embedder_revision':config['models']['embedder']['revision'],
        'embedder_sha256':config['models']['embedder']['files']['model.onnx']['sha256'],'text':'title + newline + passage; CLS pooling; L2-normalised; float16',
        'rows':int(len(rowids)),'dimensions':int(vectors.shape[1]),
        'vectors_sha256':retrieval.sha256_file(temp_vectors),'vectors_bytes':temp_vectors.stat().st_size,
        'rowids_sha256':retrieval.sha256_file(temp_rowids),'rowids_bytes':temp_rowids.stat().st_size,
        'build_seconds':round(time.monotonic()-started,1)}
    temp_vectors.replace(directory/'embeddings.npy');temp_rowids.replace(directory/'embeddings-rowids.npy')
    (directory/'embeddings-manifest.tmp').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (directory/'embeddings-manifest.tmp').replace(directory/retrieval.INDEX_MANIFEST)
    retrieval.load_index(directory,config)
    print(json.dumps(manifest,indent=2))

def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('operation',choices=('fetch','verify','install-host','sync','index'))
    parser.add_argument('--workers',type=int,default=6)
    args=parser.parse_args();config=retrieval.load_config()
    {'fetch':fetch,'verify':verify,'install-host':install_host,'sync':sync}.get(args.operation,lambda c:build_index(c,args.workers))(config)

if __name__=='__main__':main()