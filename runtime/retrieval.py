"""Optional CPU-only semantic search and cross-encoder reranking for approved evidence.

Fail closed: a missing package, model, index or any hash/size mismatch disables
this tier and the caller keeps the original BM25 behaviour. Models run through
ONNX Runtime's CPU provider only; nothing here touches the GPU, Ollama or network.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from runtime.station_paths import ROOT

CONFIG=ROOT/'config/cpu-retrieval.json'
MODELS=ROOT/'vendor/retrieval-models'
INDEX_MANIFEST='embeddings-manifest.json'
MAX_CONFIG=100000
_LOCK=threading.Lock()
_ENGINES={}
_REASONS={}
_RETRY_NOT_BEFORE={}
_ENGINE_RETRY_SECONDS=30.0

def sha256_file(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block:=stream.read(1024*1024):digest.update(block)
    return digest.hexdigest()

def load_config(path=None):
    path=Path(path or CONFIG)
    if path.is_symlink() or path.stat().st_size>MAX_CONFIG:raise ValueError('Invalid retrieval manifest')
    data=json.loads(path.read_bytes())
    if data.get('version')!=1:raise ValueError('Invalid retrieval manifest')
    for role in ('embedder','reranker'):
        model=data['models'][role]
        if not re.fullmatch(r'[a-f0-9]{40}',model.get('revision','')) or not re.fullmatch(r'[a-z0-9.-]+',model.get('directory','')):
            raise ValueError('Unpinned retrieval model')
        for name,spec in model['files'].items():
            if not re.fullmatch(r'[a-z_.]+',name) or not re.fullmatch(r'[a-f0-9]{64}',spec.get('sha256','')) or type(spec.get('bytes')) is not int:
                raise ValueError('Unpinned retrieval model file')
    return data

def _stamp(path,expected):
    """Read-only image files cannot change during a container's life. Remember one
    full verification of this exact file identity so short-lived MCP children do
    not rehash 1.2 GB per request. Writable (host) files are always rehashed."""
    if os.name=='nt' or os.access(path,os.W_OK):return None
    info=os.stat(path)
    key=hashlib.sha256(f'{path}|{info.st_dev}|{info.st_ino}|{info.st_size}|{info.st_mtime_ns}|{info.st_ctime_ns}|{expected}'.encode()).hexdigest()
    return Path(os.environ.get('HOME') or '/tmp')/'.larpus-retrieval-verified'/key

def verify_file(path,spec):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('Retrieval artifact missing: '+path.name)
    if path.stat().st_size!=spec['bytes']:raise ValueError('Retrieval artifact size mismatch: '+path.name)
    stamp=_stamp(path,spec['sha256'])
    if stamp is not None and stamp.is_file():return path
    if sha256_file(path)!=spec['sha256']:raise ValueError('Retrieval artifact hash mismatch: '+path.name)
    if stamp is not None:
        try:stamp.parent.mkdir(parents=True,exist_ok=True);stamp.write_text('ok\n')
        except OSError:pass
    return path

def verify_model(config,role,models=None):
    model=config['models'][role];directory=Path(models or MODELS)/model['directory']
    return {name:verify_file(directory/name,spec) for name,spec in model['files'].items()}

def load_index(directory,config):
    """Embedding matrix bound to the exact approved database and embedder revision."""
    import numpy
    directory=Path(directory);manifest_path=directory/INDEX_MANIFEST
    if manifest_path.is_symlink() or manifest_path.stat().st_size>MAX_CONFIG:raise ValueError('Invalid embedding manifest')
    manifest=json.loads(manifest_path.read_bytes())
    library=json.loads((directory/'manifest.json').read_bytes())
    embedder=config['models']['embedder']
    if manifest.get('version')!=1 or manifest.get('database_sha256')!=library.get('database_sha256'):raise ValueError('Embedding index does not match approved database')
    if manifest.get('embedder_revision')!=embedder['revision'] or manifest.get('embedder_sha256')!=embedder['files']['model.onnx']['sha256']:raise ValueError('Embedding index built by another model')
    vectors=numpy.load(verify_file(directory/'embeddings.npy',{'sha256':manifest['vectors_sha256'],'bytes':manifest['vectors_bytes']}),allow_pickle=False)
    rowids=numpy.load(verify_file(directory/'embeddings-rowids.npy',{'sha256':manifest['rowids_sha256'],'bytes':manifest['rowids_bytes']}),allow_pickle=False)
    if vectors.dtype!=numpy.float16 or vectors.ndim!=2 or vectors.shape!=(manifest['rows'],manifest['dimensions']) or rowids.shape!=(manifest['rows'],) or rowids.dtype!=numpy.int64:
        raise ValueError('Embedding index shape mismatch')
    return vectors.astype(numpy.float32),rowids

def _session(path,threads):
    import onnxruntime
    options=onnxruntime.SessionOptions()
    options.intra_op_num_threads=threads;options.inter_op_num_threads=1
    options.graph_optimization_level=onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
    options.log_severity_level=3
    session=onnxruntime.InferenceSession(str(path),options,providers=['CPUExecutionProvider'])
    if session.get_providers()!=['CPUExecutionProvider']:raise ValueError('Retrieval models are CPU-only')
    return session

def _tokenizer(path,limit,pad=True):
    from tokenizers import Tokenizer
    tokenizer=Tokenizer.from_file(str(path))
    tokenizer.enable_truncation(max_length=limit)
    if pad:tokenizer.enable_padding()
    return tokenizer

def _feed(session,encodings):
    import numpy
    names={i.name for i in session.get_inputs()}
    feed={'input_ids':numpy.array([e.ids for e in encodings],dtype=numpy.int64),'attention_mask':numpy.array([e.attention_mask for e in encodings],dtype=numpy.int64)}
    if 'token_type_ids' in names:feed['token_type_ids']=numpy.zeros_like(feed['input_ids'])
    return feed

class Embedder:
    def __init__(self,config,threads,models=None):
        files=verify_model(config,'embedder',models);spec=config['models']['embedder']
        self.session=_session(files['model.onnx'],threads)
        self.tokenizer=_tokenizer(files['tokenizer.json'],spec['max_tokens'])
        self.prefix=spec['query_prefix']
    def encode(self,texts,query=False):
        import numpy
        encodings=self.tokenizer.encode_batch([self.prefix+t if query else t for t in texts])
        hidden=self.session.run(None,_feed(self.session,encodings))[0][:,0]
        return hidden/numpy.maximum(numpy.linalg.norm(hidden,axis=1,keepdims=True),1e-12)

class Reranker:
    def __init__(self,config,threads,models=None):
        files=verify_model(config,'reranker',models);spec=config['models']['reranker']
        self.session=_session(files['model.onnx'],threads)
        self.tokenizer=_tokenizer(files['tokenizer.json'],spec['max_tokens'])
    def score(self,question,passages,batch=4,deadline=None):
        """Relevance logits in input order; None for pairs skipped by the deadline."""
        scores=[None]*len(passages)
        for start in range(0,len(passages),batch):
            if deadline is not None and start and time.monotonic()>deadline:break
            encodings=self.tokenizer.encode_batch([(question,p) for p in passages[start:start+batch]])
            logits=self.session.run(None,_feed(self.session,encodings))[0].reshape(-1)
            for offset,value in enumerate(logits):scores[start+offset]=float(value)
        return scores

class Engine:
    def __init__(self,directory,config=None,models=None):
        self.config=config or load_config()
        settings=self.config['runtime']
        threads=max(1,min(int(settings['threads']),os.cpu_count() or 1))
        self.bm25=int(settings['bm25_candidates']);self.semantic=int(settings['semantic_candidates'])
        self.batch=int(settings['rerank_batch']);self.deadline=float(settings['rerank_deadline_seconds'])
        self.minimum=float(settings['semantic_min_rerank_score'])
        self.vectors,self.rowids=load_index(directory,self.config)
        from runtime.scoring_pipeline import Pipeline
        self.pipeline=Pipeline(self.vectors)
        self.embedder=Embedder(self.config,threads,models)
        self.reranker=Reranker(self.config,threads,models)
    def neighbors(self,question,limit):
        import numpy
        query=self.embedder.encode([question],query=True)[0]
        similarity=self.pipeline.score(query,limit)
        limit=min(limit,len(similarity))
        if limit<=0:return []
        top=numpy.argpartition(-similarity,limit-1)[:limit]
        return [int(self.rowids[i]) for i in top[numpy.argsort(-similarity[top],kind='stable')]]
    def rerank(self,question,passages,deadline=None):
        return self.reranker.score(question,passages,self.batch,deadline)

class RemoteEngine:
    """Client for the persistent in-container worker; same interface as Engine."""
    def __init__(self,config=None):
        from runtime import retrieval_worker
        self.worker=retrieval_worker
        self.config=config or load_config();settings=self.config['runtime']
        self.bm25=int(settings['bm25_candidates']);self.semantic=int(settings['semantic_candidates'])
        self.batch=int(settings['rerank_batch']);self.deadline=float(settings['rerank_deadline_seconds'])
        self.minimum=float(settings['semantic_min_rerank_score'])
        reply=self.worker.call({'action':'status'},1.0)
        if reply.get('ready') is not True:raise OSError('Retrieval worker not ready')
    def neighbors(self,question,limit):
        rowids=self.worker.call({'action':'neighbors','question':question[:4000],'limit':min(64,limit)},1.0)['rowids']
        if not isinstance(rowids,list) or any(type(i) is not int for i in rowids):raise ValueError('Invalid neighbours')
        return rowids
    def rerank(self,question,passages,deadline=None):
        remaining=(deadline-time.monotonic()) if deadline is not None else self.deadline
        budget=max(1,min(5000,int(remaining*1000)))
        scores=self.worker.call({'action':'rerank','question':question[:4000],'passages':[p[:4000] for p in passages[:32]],'budget_ms':budget},budget/1000+1.0)['scores']
        if not isinstance(scores,list) or len(scores)!=min(32,len(passages)) or any(s is not None and type(s) not in (int,float) for s in scores):raise ValueError('Invalid scores')
        return scores+[None]*(len(passages)-len(scores))

def worker_mode():
    """'remote' in the sealed agent image (set by the Containerfile); otherwise load locally."""
    return os.environ.get('LARPUS_RETRIEVAL_WORKER','local')

def disabled():
    return os.environ.get('LARPUS_CPU_RETRIEVAL','').casefold() in ('0','off','false','disabled')

def engine(directory):
    """Return the cached engine. A failed open is remembered for 30 seconds, then tried again.

    None means this call uses BM25. The reason keeps the exception type only.
    A ready engine stays cached until reset or process replacement."""
    if disabled():return None
    key=str(Path(directory).resolve())
    now=time.monotonic()
    with _LOCK:
        loaded=_ENGINES.get(key)
        if loaded is not None or now<_RETRY_NOT_BEFORE.get(key,0):return loaded
        try:loaded=RemoteEngine() if worker_mode()=='remote' else Engine(directory)
        except Exception as exc:
            _REASONS[key]=type(exc).__name__
            _RETRY_NOT_BEFORE[key]=now+_ENGINE_RETRY_SECONDS
            return None
        _ENGINES[key]=loaded
        _REASONS[key]='ready ('+worker_mode()+')'
        _RETRY_NOT_BEFORE.pop(key,None)
        return loaded

def status(directory):
    key=str(Path(directory).resolve())
    loaded=engine(directory)
    return {'cpu_retrieval':'ready' if loaded else 'bm25-only','reason':_REASONS.get(key,'disabled by environment'),
            'failure_cached':loaded is None and key in _RETRY_NOT_BEFORE}

def reset():
    with _LOCK:_ENGINES.clear();_REASONS.clear();_RETRY_NOT_BEFORE.clear()
