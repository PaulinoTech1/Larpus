"""Pure, conservative owner recovery decisions. No runtime or process I/O."""
from dataclasses import dataclass
import math
import re

STATES=frozenset({'disabled','observing','suspect','waiting','recovering','cooldown','held'})
REASONS=frozenset({'disabled','healthy','suspect','dead','unknown','reused','maintenance',
    'deployment','drain','busy','dependency','broker-fault','clock','budget',
    'cooldown','reservation','invalid-state','launch-failed','readiness-failed',
    'cleanup-uncertain','launch-uncertain','persist-failed','recovered','observe-only',
    'acknowledged','lock-busy','integrity','unsupported','port-occupied'})

def finite(value):
    return type(value) in (float,int) and math.isfinite(value) and value>=0

@dataclass(frozen=True)
class Policy:
    interval_seconds: float=5
    dead_threshold: int=3
    attempt_limit: int=2
    window_seconds: float=600
    cooldown_seconds: float=60
    jitter_max_seconds: float=10

    def __post_init__(self):
        values=(self.interval_seconds,self.window_seconds,self.cooldown_seconds)
        if not all(finite(v) and v>0 for v in values):raise ValueError('Invalid recovery timing')
        if type(self.dead_threshold) is not int or self.dead_threshold<3:raise ValueError('Invalid death threshold')
        if type(self.attempt_limit) is not int or not 1<=self.attempt_limit<=2:raise ValueError('Invalid attempt bound')
        if not finite(self.jitter_max_seconds) or self.jitter_max_seconds>10:raise ValueError('Invalid jitter')

@dataclass(frozen=True)
class GatewayIdentity:
    release_id: str
    pid: int
    creation: str
    command_sha256: str

    def __post_init__(self):
        if not isinstance(self.release_id,str) or not re.fullmatch('[a-f0-9]{32}',self.release_id):raise ValueError('Invalid release identity')
        if type(self.pid) is not int or self.pid<=0:raise ValueError('Invalid process identity')
        if not isinstance(self.creation,str) or not 1<=len(self.creation)<=100:raise ValueError('Invalid creation identity')
        if not isinstance(self.command_sha256,str) or not re.fullmatch('[a-f0-9]{64}',self.command_sha256):raise ValueError('Invalid command identity')

@dataclass(frozen=True)
class Observation:
    identity: GatewayIdentity | None
    process: str
    http: str
    readiness: str
    dependencies: str
    broker: str
    suppression: str | None
    wall_time: float
    monotonic_time: float

    def __post_init__(self):
        fields=((self.process,{'alive','dead','reused','unknown'}),
                (self.http,{'responding','refused','unreachable','unknown'}),
                (self.readiness,{'ready','failed','stale','unknown'}),
                (self.dependencies,{'ready','busy','failed','unknown'}),
                (self.broker,{'idle','busy','faulted','unknown'}))
        if any(value not in allowed for value,allowed in fields):raise ValueError('Invalid observation')
        if self.suppression not in {None,'maintenance','deployment','drain','lock-busy','unsupported'}:raise ValueError('Invalid suppression')
        if not finite(self.wall_time) or not finite(self.monotonic_time):raise ValueError('Invalid observation time')
        if self.identity is not None and not isinstance(self.identity,GatewayIdentity):raise ValueError('Invalid gateway identity')

@dataclass(frozen=True)
class History:
    armed: bool=False
    state: str='disabled'
    reason: str='disabled'
    identity: GatewayIdentity | None=None
    dead_count: int=0
    attempts: tuple[float,...]=()
    last_wall_time: float=0
    last_monotonic_time: float=0
    next_attempt_wall_time: float=0
    reservation: dict | None=None

    def __post_init__(self):
        if type(self.armed) is not bool or self.state not in STATES or self.reason not in REASONS:raise ValueError('Invalid recovery state')
        if type(self.dead_count) is not int or not 0<=self.dead_count<=1000:raise ValueError('Invalid death count')
        self._times()
        if self.identity is not None and not isinstance(self.identity,GatewayIdentity):raise ValueError('Invalid gateway identity')
        if self.reservation is not None and not isinstance(self.reservation,dict):raise ValueError('Invalid reservation')

    def _times(self):
        if not isinstance(self.attempts,tuple) or len(self.attempts)>2 or not all(finite(t) for t in self.attempts):raise ValueError('Invalid attempts')
        if not all(finite(t) for t in (self.last_wall_time,self.last_monotonic_time,self.next_attempt_wall_time)):raise ValueError('Invalid history time')

@dataclass(frozen=True)
class Decision:
    state: str
    reason: str
    action: str='none'
    dead_count: int=0

def clock_valid(o,h):
    if o.wall_time<h.last_wall_time:return False
    if not h.last_monotonic_time:return True
    elapsed=o.monotonic_time-h.last_monotonic_time
    return elapsed>=0 and abs(o.wall_time-h.last_wall_time-elapsed)<=10

def _guard(o,h):
    if not h.armed:return Decision('disabled','disabled')
    if h.state=='held':return Decision('held',h.reason)
    if not clock_valid(o,h):return Decision('held','clock')
    if o.suppression:return Decision('held' if o.suppression=='unsupported' else 'waiting',o.suppression)
    if o.identity is None or o.process=='unknown':return Decision('held','unknown')
    if o.process=='reused':return Decision('held','reused')
    return None

def _dependencies(o):
    if o.broker=='faulted':return Decision('held','broker-fault')
    if o.dependencies=='busy' or o.broker=='busy':return Decision('waiting','busy')
    if o.dependencies!='ready' or o.broker!='idle':return Decision('held','dependency')
    return None

def decide(observation,history,policy):
    o,h=observation,history
    guard=_guard(o,h) or _dependencies(o)
    if guard:return guard
    if h.reservation is not None:return Decision('held','reservation')
    if o.process=='alive':
        if o.http=='responding' and o.readiness=='ready':return Decision('observing','healthy')
        return Decision('held','unknown')
    if o.http=='unknown':return Decision('held','unknown')
    if o.http in {'responding','refused'}:return Decision('held','port-occupied')
    return _dead(o,h,policy)

def _dead(o,h,p):
    attempts=[t for t in h.attempts if o.wall_time-t<p.window_seconds]
    if any(t>o.wall_time for t in attempts):return Decision('held','clock')
    if len(attempts)>=p.attempt_limit:return Decision('held','budget')
    if o.wall_time<h.next_attempt_wall_time:return Decision('cooldown','cooldown')
    count=min(1000,h.dead_count+1) if o.identity==h.identity else 1
    if count<p.dead_threshold:return Decision('suspect','suspect',dead_count=count)
    return Decision('recovering','dead','recover',count)
