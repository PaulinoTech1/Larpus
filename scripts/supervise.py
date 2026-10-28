"""Owner recovery CLI. Disabled by default; no installation or automatic arming."""
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.recovery_policy import Decision, Policy, decide
from scripts.recovery_state import Journal, StateError
from scripts.recovery_backend import Backend

ROOT=Path(__file__).resolve().parents[1]

def status(journal,*,now=None):
    h=journal.read();clock=time.time() if now is None else now
    value=asdict(h)
    value['stale']=bool(h.last_wall_time and (clock<h.last_wall_time or clock-h.last_wall_time>180))
    return value

def control(operation,backend,journal,*,stop_gateway=False):
    with backend.adapter.exclusive():
        if operation=='acknowledge':
            h=journal.read();journal.write(replace(h,state='observing',reason='acknowledged',dead_count=0))
        elif operation in {'arm','disable'}:journal.set_armed(operation=='arm')
        else:raise ValueError('Invalid owner operation')
        if stop_gateway:
            if operation!='disable':raise ValueError('Disable required before stop')
            backend.drain_owned(journal)
    return status(journal)

def _save(journal,o,decision):
    h=journal.read()
    held=h.state=='held'
    journal.write(replace(h,state=h.state if held else decision.state,reason=h.reason if held else decision.reason,
                          identity=o.identity,dead_count=decision.dead_count,last_wall_time=max(h.last_wall_time,o.wall_time),
                          last_monotonic_time=o.monotonic_time))

def _shown(decision):
    if decision.action!='recover':return decision
    return Decision('waiting','observe-only','recover',decision.dead_count)

def _stored_deaths(decision,previous):
    if decision.dead_count<previous:return decision.dead_count
    return previous

def _observe_locked(backend,journal,policy,observe_only,simulated_count):
    with backend.adapter.exclusive():
        h=journal.read();o=backend.observe()
        counted=h.dead_count if simulated_count is None or simulated_count[0] is None else simulated_count[0]
        simulated=replace(h,armed=True,dead_count=counted) if observe_only else h
        decision=decide(o,simulated,policy)
        if not observe_only:_save(journal,o,decision);return decision
        if simulated_count is not None:simulated_count[0]=decision.dead_count
        printed=_shown(decision)
        saved=_stored_deaths(decision,h.dead_count)
        _save(journal,o,replace(printed,dead_count=saved))
        return printed

def cycle(backend,journal,policy,observe_only=False,simulated_count=None):
    try:
        h=journal.read();o=backend.observe()
        decision=decide(o,replace(h,armed=True) if observe_only else h,policy)
        reconcile=h.reservation is not None and h.armed and h.state!='held'
        if not observe_only and (decision.action=='recover' or reconcile):
            result=backend.recover(o.identity,journal,policy)
            return Decision(result['state'],result['reason'])
        return _observe_locked(backend,journal,policy,observe_only,simulated_count)
    except StateError:return Decision('held','persist-failed')
    except OSError:return Decision('waiting','lock-busy')
    except (ValueError,KeyError,TypeError,RuntimeError):return Decision('held','invalid-state')

def watch(backend,journal,policy,*,observe_only=False,stop=None,max_cycles=None):
    stop=stop or threading.Event();count=0;simulated=[None]
    with journal.singleton():
        while not stop.is_set():
            try:print(json.dumps({'event':'observation','sequence':count+1}),flush=True)
            except (OSError,ValueError):return 2
            result=cycle(backend,journal,policy,observe_only,simulated if observe_only else None)
            try:print(json.dumps(asdict(result)),flush=True)
            except (OSError,ValueError):return 2
            count+=1
            if max_cycles is not None and count>=max_cycles:break
            stop.wait(policy.interval_seconds)
    return 0

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('status','watch','arm','disable','acknowledge'))
    parser.add_argument('--observe-only',action='store_true')
    parser.add_argument('--stop-gateway',action='store_true')
    args=parser.parse_args(argv)
    if args.observe_only and args.operation!='watch':parser.error('--observe-only requires watch')
    if args.stop_gateway and args.operation!='disable':parser.error('--stop-gateway requires disable')
    journal=Journal(ROOT/'data/recovery')
    try:return _command(args,journal)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        print(json.dumps({'state':'held','reason':'invalid-state'}));return 2

def _command(args,journal):
    if args.operation=='status':value=status(journal)
    elif args.operation=='watch':return watch(Backend(ROOT),journal,Policy(),observe_only=args.observe_only)
    else:value=control(args.operation,Backend(ROOT),journal,stop_gateway=args.stop_gateway)
    print(json.dumps(value));return 0

if __name__=='__main__':raise SystemExit(main())
