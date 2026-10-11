"""Owner-only read-only study-note progress; never calls inference."""
import argparse
import datetime
import json
from pathlib import Path
import sqlite3
import time

ROOT=Path(__file__).resolve().parents[1]

def events(path):
    if not path.exists():return []
    # Bounded tail, tolerate a concurrent partial line and legacy PowerShell logs.
    with path.open('rb') as handle:
        handle.seek(0,2);size=handle.tell();handle.seek(max(0,size-2_000_000))
        raw=handle.read()
    result=[]
    for line in raw.decode('utf-8-sig',errors='replace').splitlines():
        try:value=json.loads(line.lstrip('\ufeff'))
        except (ValueError,TypeError):continue
        if isinstance(value,dict):result.append(value)
    return result

def report(root=ROOT,now=None):
    now=time.time() if now is None else now
    database=root/'knowledge/notes.build.sqlite'
    result={'status':'unknown','windows_done':None,'notes':None,'last_saved_age_seconds':None,
            'recent_successful_requests':0,'recent_worker_errors':0,'recent_worker_retries':0,
            'median_successful_request_seconds':None,
            'scope':'Read-only saved progress and bounded log tail; not a live worker/process or GPU probe.'}
    if not database.exists():return result
    # mode=ro avoids accidentally creating a replacement database.
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True,timeout=5) as connection:
        done,last=connection.execute('SELECT count(*),max(at) FROM done').fetchone()
        result.update(windows_done=done,notes=connection.execute('SELECT count(*) FROM notes').fetchone()[0])
    if last is not None:result['last_saved_age_seconds']=round(max(0,now-last),1)
    tail=events(root/'data/study-notes.log')[-200:]
    timings=[e['seconds'] for e in tail if isinstance(e.get('seconds'),(float,int)) and e['seconds']>=0 and e.get('metrics',{}).get('done_reason')=='stop']
    timings.sort()
    if timings:
        mid=len(timings)//2
        result['median_successful_request_seconds']=round((timings[mid]+timings[~mid])/2,2)
    result['recent_successful_requests']=len(timings)
    result['recent_worker_errors']=sum('worker_error' in e for e in tail)
    result['recent_worker_retries']=sum('worker_retry' in e for e in tail)
    age=result['last_saved_age_seconds']
    result['status']='recent_progress' if age is not None and age<180 else 'needs_check'
    # A last transport failure is visible even when older saved progress is recent.
    relevant=[e for e in tail if 'worker_error' in e or 'worker_retry' in e or 'kept' in e]
    if relevant and ('worker_error' in relevant[-1] or 'worker_retry' in relevant[-1]):result['status']='recovery_or_failure'
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.parse_args()
    try:print(json.dumps(report(),indent=2))
    except (OSError,sqlite3.Error,ValueError,TypeError) as exc:
        print(json.dumps({'status':'unavailable','error':type(exc).__name__}));raise SystemExit(1)
