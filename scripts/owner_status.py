"""Read-only owner snapshot. No WSL, scans, generation, service control or writes."""
import json
from pathlib import Path
import re
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.recovery_backend import REQUIRED, bounded_json, receipt_token
from scripts.recovery_state import Journal, safe_path

CHECKOUT=Path(__file__).resolve().parents[1]
FEATURES={'execution_profiles':'runtime/execution_profiles.py','mcp_skills':'runtime/mcp_skills.py',
          'recovery':'scripts/supervise.py','encrypted_backup':'scripts/backup_store.py','quality_support':'scripts/quality_evaluation.py'}

def _git(root,*args):
    result=subprocess.run(['git','-C',str(root),*args],capture_output=True,timeout=5,check=True)
    if len(result.stdout)>65536:raise ValueError('Git snapshot too large')
    return result.stdout.decode('utf-8').strip()

def owner_root(checkout=CHECKOUT):
    common=Path(_git(checkout,'rev-parse','--git-common-dir'))
    return (common if common.is_absolute() else checkout/common).resolve().parent

def git_snapshot(root):
    return {'branch':_git(root,'branch','--show-current'),'sha':_git(root,'rev-parse','HEAD'),
            'dirty_files':_git(root,'status','--porcelain=v1','--untracked-files=normal').splitlines(),
            'worktrees':_git(root,'worktree','list','--porcelain').splitlines()}

def _read(path):
    try:return bounded_json(path)
    except (OSError,ValueError,TypeError):return {}

def _age(path):
    try:return max(0.,time.time()-path.stat().st_mtime)
    except OSError:return None

def _selected(root):
    value=_read(root/'data/releases/active.json');identifier=value.get('id')
    if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{32}',identifier):return {},None
    directory=root/'data/releases'/identifier
    try:safe_path(directory)
    except OSError:return {},None
    return value,directory

def _readiness(directory,active,now):
    if directory is None:return {'state':'unknown'},{}
    report={};path=directory/'release-state/health/latest.json'
    if not path.exists():path=directory/'data/health/latest.json'
    report=_read(path);checks=report.get('checks',[])
    statuses={c.get('name'):c.get('status') for c in checks if isinstance(c,dict)}
    passed=all(statuses.get(name)=='pass' for name in REQUIRED)
    age=_age(path);state='unknown'
    if age is not None and age>180:state='stale'
    elif passed:state='reported-ready-unbound'
    producer=report.get('producer',{})
    if producer:
        state=_producer_state(producer,active,now,passed)
    return {'state':state,'required_checks_pass':passed,'health_age_seconds':age,
            'checks':statuses,'evidence':'saved health only; no live readiness probe'},statuses

def _producer_state(producer,active,now,passed):
    from scripts.recovery_policy import GatewayIdentity
    try:
        expected=GatewayIdentity(active['id'],active['pid'],'owner-status','0'*64)
        report={'producer':producer,'checks':[{'name':n,'status':'pass'} for n in REQUIRED]}
        token=receipt_token(report,expected,0,now=now)
        if token and passed:return 'ready'
        finished=producer.get('finished')
        if type(finished) in (int,float) and now-finished>180:return 'stale'
    except (ValueError,KeyError,TypeError):pass
    return 'unknown'

def _prepared(root):
    store=root/'data/releases'
    if not store.exists():return []
    rows=[]
    for i,path in enumerate(store.iterdir()):
        if i>=1000:return rows+[{'state':'inventory-truncated'}]
        if not re.fullmatch('[a-f0-9]{32}',path.name):continue
        meta=_read(path/'release.json')
        if meta.get('status')=='prepared':rows.append({'id':path.name,'state':'prepared-receipt-only','pins_reverified':False})
    return sorted(rows,key=lambda row:row['id'])

def _recovery(root):
    try:
        h=Journal(root/'data/recovery').read()
        return {'state':h.state,'reason':h.reason,'armed':h.armed,'attempts':len(h.attempts),
                'reservation_present':h.reservation is not None,'supervisor_running':'not-probed'}
    except OSError:return {'state':'held','reason':'journal-unavailable','armed':None}

def _scan(summary,path,status):
    results=summary.get('results',[])
    if not isinstance(results,list):results=[]
    complete=sum(isinstance(r,dict) and r.get('complete') is True for r in results)
    warnings=sum(isinstance(r,dict) and r.get('status') in {'warn','warning'} for r in results)
    return {'status':status,'receipt_status':summary.get('status','unknown'),'receipt_age_seconds':_age(path),
            'target_count':len(results),'complete_targets':complete,'incomplete_targets':len(results)-complete,
            'warning_targets':warnings,'pins_reverified':False,'fresh_scan_performed':False}

def collect(root,*,git_probe=git_snapshot,monotonic_now=None,checkout=None):
    root=Path(root);active,directory=_selected(root)
    readiness,statuses=_readiness(directory,active,time.monotonic() if monotonic_now is None else monotonic_now)
    try:git=git_probe(checkout or root)
    except (OSError,ValueError,subprocess.SubprocessError):git={'state':'unknown'}
    scan_path=directory/'release-state/security/summary.json' if directory else root/'no-selected-release'
    summary=_read(scan_path)
    features={name:{'selected_payload_present':bool(directory and (directory/path).is_file()),
                    'checkout_present':((checkout or root)/path).is_file()} for name,path in FEATURES.items()}
    return {'active':{'state':'selected' if active else 'unknown','id':active.get('id'),'recorded_pid':active.get('pid')},
            'pending_cutover':(root/'data/releases/pending.json').exists(),'readiness':readiness,
            'scan':_scan(summary,scan_path,statuses.get('security_scan','unknown')),
            'recovery':_recovery(root),'prepared':_prepared(root),'checkout':git,'features':features}

def main():
    print(json.dumps(collect(owner_root(),checkout=CHECKOUT),indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
