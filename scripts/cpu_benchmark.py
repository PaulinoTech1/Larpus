"""Owner-only retrieval sweep. No GPU, network, configuration writes or activation."""
import argparse
import json
import os
import platform
from pathlib import Path
import sqlite3
import statistics
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
QUESTIONS=(
    'How should I learn norms and stability before studying topology?',
    'How can a SOC validate AI alert triage and retain human oversight?',
    'What controls should govern AI assisted penetration testing workflows?',
)


def approved_directory(root=ROOT):
    active=root/'data/releases/active.json'
    if not active.exists():return root/'knowledge'
    identifier=json.loads(active.read_text())['id']
    if not re.fullmatch(r'[a-f0-9]{32}',identifier):raise ValueError('Invalid active release ID')
    return root/'data/releases'/identifier/'knowledge'


def bounded(values,maximum):
    if not values or any(type(value) is not int or not 1<=value<=maximum for value in values):raise ValueError('Values must be between 1 and '+str(maximum))


def settings(threads,batches,repeats):
    bounded(threads,20);bounded(batches,16)
    if type(repeats) is not int or not 1<=repeats<=5:raise ValueError('Repeats must be between 1 and 5')
    return [(t,b) for t in dict.fromkeys(threads) for b in dict.fromkeys(batches)]


def effective_threads(requested,visible):
    bounded([requested],20)
    return min(requested,visible or 1)


def ranked(identifiers,scores):
    pairs=[(identifier,score) for identifier,score in zip(identifiers,scores) if score is not None]
    return [identifier for identifier,_ in sorted(pairs,key=lambda item:-item[1])][:5]


def overlap(reference,candidate):
    return len(set(reference)&set(candidate))/len(set(reference)) if reference else 0.0


def sample(engine,connection,question,budget):
    started=time.perf_counter();ids=engine.neighbors(question,16)
    neighbors_ms=(time.perf_counter()-started)*1000
    if not ids:raise ValueError('No semantic candidates; benchmark requires an approved embedding index')
    rows=dict(connection.execute('SELECT rowid,text FROM chunks WHERE rowid IN ('+','.join('?' for _ in ids)+')',ids))
    passages=[rows[i] for i in ids]
    # Match the live deadline: semantic search consumes part of the same budget.
    deadline=started+budget if budget is not None else None
    rerank_started=time.perf_counter();scores=engine.rerank(question,passages,deadline)
    return {'neighbors_ms':round(neighbors_ms,3),'rerank_ms':round((time.perf_counter()-rerank_started)*1000,3),
            'total_ms':round((time.perf_counter()-started)*1000,3),'scored':sum(s is not None for s in scores),
            'candidates':len(ids),'top':ranked(ids,scores)}


def worker(args):
    # Set before importing numerical libraries. Each case has a fresh process,
    # avoiding retained ONNX thread pools and BLAS oversubscription across cases.
    threads=effective_threads(args.worker_threads,os.cpu_count())
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        os.environ[key]=str(threads)
    os.environ['TOKENIZERS_PARALLELISM']='false'
    sys.path.insert(0,str(ROOT))
    from runtime.retrieval import Engine,load_config,verify_file
    import onnxruntime
    config=load_config();config['runtime']['threads']=threads;config['runtime']['rerank_batch']=args.worker_batch
    manifest=json.loads((Path(args.directory)/'manifest.json').read_bytes())
    database=verify_file(Path(args.directory)/'approved.sqlite',{'sha256':manifest['database_sha256'],'bytes':manifest['database_bytes']})
    started=time.perf_counter();engine=Engine(args.directory,config,args.models)
    setup_ms=round((time.perf_counter()-started)*1000,3)
    connection=sqlite3.connect(database.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
    try:
        budget=None if args.reference else config['runtime']['rerank_deadline_seconds']
        warm=[sample(engine,connection,q,budget) for q in QUESTIONS]
        runs=[[sample(engine,connection,q,budget) for q in QUESTIONS] for _ in range(args.repeats)]
    finally:connection.close()
    return {'threads':threads,'requested_threads':args.worker_threads,'effective_onnx_threads':engine.reranker.session.get_session_options().intra_op_num_threads,
            'batch':args.worker_batch,'setup_ms':setup_ms,'warmup':warm,'runs':runs,
            'environment':{'os':platform.system(),'onnxruntime':onnxruntime.__version__,'logical_cpus':os.cpu_count(),'database_sha256':manifest['database_sha256']}}


def run_worker(args,threads,batch,reference=False):
    command=[sys.executable,'-m','scripts.cpu_benchmark','--worker-threads',str(threads),'--worker-batch',str(batch),
             '--directory',str(Path(args.directory).resolve()),'--models',str(Path(args.models).resolve()),'--repeats',str(args.repeats)]
    if reference:command.append('--reference')
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=600,check=True)
    if len(result.stdout)>100000:raise ValueError('Oversized CPU benchmark receipt')
    return json.loads(result.stdout)


def compare(reference,result):
    observations=[s for repeat in result['runs'] for s in repeat]
    result['median_ms']=round(statistics.median(s['total_ms'] for s in observations),3)
    result['minimum_scored']=min(s['scored'] for s in observations)
    result['mean_top5_overlap']=round(statistics.mean(overlap(reference['runs'][0][i]['top'],s['top']) for repeat in result['runs'] for i,s in enumerate(repeat)),3)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--threads',type=int,nargs='+',default=[4,8,12,16,20])
    parser.add_argument('--batches',type=int,nargs='+',default=[2,4,8])
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--directory',default=str(approved_directory()))
    parser.add_argument('--models',default=str(ROOT/'vendor/retrieval-models'))
    parser.add_argument('--run',action='store_true',help='Run real CPU inference; otherwise print the plan only')
    parser.add_argument('--worker-threads',type=int,help=argparse.SUPPRESS)
    parser.add_argument('--worker-batch',type=int,default=4,help=argparse.SUPPRESS)
    parser.add_argument('--reference',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.worker_threads is not None:
        settings([args.worker_threads],[args.worker_batch],args.repeats)
        print(json.dumps(worker(args)));return
    cases=settings(args.threads,args.batches,args.repeats)
    print(json.dumps({'planned_cases':cases,'repeats':args.repeats,'thread_ceiling':20,'running':args.run,
                     'scope':'CPU semantic retrieval and reranking only; no generation, BM25, screening or browser rendering.'}),flush=True)
    if not args.run:return
    reference=run_worker(args,4,4,reference=True)
    print(json.dumps({'reference':reference,'quality_scope':'Top-5 overlap with full reranking is a regression proxy, not factual accuracy.'}),flush=True)
    for threads,batch in cases:
        print(json.dumps(compare(reference,run_worker(args,threads,batch))),flush=True)


if __name__=='__main__':main()
