"""Bounded numeric observations; never policy, user text or a shared sink."""
import math
from typing import Callable

EVENTS=frozenset(('input','retrieval','model_selection','model_first_text','first_approved','complete'))

def exclusive_stages(events):
    """Adjacent local inference offsets only. Never add overlapping parent clocks."""
    boundaries=(('input','input'),('retrieval','retrieval'),('model_selection','model_selection'),
                ('first_approved','generation_to_approved'),('complete','after_first_approved'))
    previous=0.;result={}
    for boundary,name in boundaries:
        value=events.get(boundary)
        if type(value) not in (int,float) or not math.isfinite(value):return {}
        if not previous<=value<=3600000:return {}
        result[name]=round(value-previous,3);previous=value
    return result

class Trace:
    def __init__(self,enabled: bool,clock: Callable[[],float]):
        self.clock=clock;self.enabled=enabled;self.events={};self.started=self._time() if enabled else None;self.last_approved=None
    def _time(self):
        try:
            value=self.clock()
            return value if type(value) in (int,float) and math.isfinite(value) else None
        except Exception:return None
    def mark(self,name: str) -> None:
        if name not in EVENTS:raise ValueError('Unknown trace event')
        if not self.enabled or self.started is None or name in self.events:return
        now=self._time()
        if now is not None and 0<=now-self.started<=3600:self.events[name]=round((now-self.started)*1000,3)
    def snapshot(self) -> dict:
        return dict(self.events)
    def attach(self,result):
        self.mark('complete')
        if self.enabled:
            result['execution_trace_ms']=self.snapshot()
            result['execution_stages_ms']=exclusive_stages(self.snapshot())
    def model_text(self,delta):
        if delta:self.mark('model_first_text')
    def screen(self,check,*args):
        if not self.enabled:return check(*args)
        before=self._time()
        try:return check(*args)
        finally:
            elapsed=self.elapsed(before)
            self.events['gate_total']=round(self.events.get('gate_total',0.)+elapsed,3)
            self.events['gate_calls']=self.events.get('gate_calls',0)+1
    def elapsed(self,before):
        after=self._time()
        if before is None or after is None:return 0.
        return round(max(0.,min(3600.,after-before))*1000,3)
    def approved(self):
        if not self.enabled:return
        now=self._time()
        if now is None or self.started is None:return
        self.events.setdefault('first_approved',round(max(0.,now-self.started)*1000,3))
        if self.last_approved is not None:
            self.events['approved_gap_max']=max(self.events.get('approved_gap_max',0.),round(max(0.,now-self.last_approved)*1000,3))
        self.last_approved=now
