"""Broker-owned generation admission. Socket identity, never request text, sets lane."""
from collections import deque
from contextlib import contextmanager
import socket
import threading
import time

LIMITS={
    'chat':{'requests':12,'tokens':12288,'output':1024,'seconds':180},
    'notes':{'requests':6,'tokens':36000,'output':6000,'seconds':180},
}

class Refused(OSError):
    def __init__(self,status,code):
        super().__init__(code);self.status=status;self.code=code

class Job:
    def __init__(self,lane):
        self.lane=lane;self.reason=None;self.sock=None;self.lock=threading.Lock();self.received=False
    def cancel(self,reason):
        with self.lock:
            self.reason=self.reason or reason
            if self.sock is not None:
                try:self.sock.shutdown(socket.SHUT_RDWR)
                except OSError:pass
    def bind(self,sock):
        with self.lock:self.sock=sock
        if self.reason:self.cancel(self.reason);raise Refused(409,self.reason)

class Scheduler:
    def __init__(self,verify_idle,wait_seconds=20,limits=None):
        self.verify_idle=verify_idle;self.wait_seconds=wait_seconds;self.limits=limits or LIMITS
        self.condition=threading.Condition();self.active=None;self.waiting=0
        self.faulted=False;self.needs_probe=True
        self.history={lane:deque() for lane in self.limits};self.status_history=deque()
        self.preemptions=0;self.recoveries=0
    def snapshot(self):
        with self.condition:
            return {'active':self.active.lane if self.active else None,
                    'received_frame':bool(self.active and self.active.received),
                    'waiting_chat':self.waiting,'faulted':self.faulted,
                    'preemptions':self.preemptions,'confirmed_recoveries':self.recoveries}
    def status_budget(self):
        with self.condition:
            now=time.monotonic()
            while self.status_history and self.status_history[0]<=now-60:self.status_history.popleft()
            if len(self.status_history)>=120:raise Refused(429,'status_budget')
            self.status_history.append(now)
    def charge(self,lane,tokens):
        history=self.history[lane];limit=self.limits[lane];now=time.monotonic()
        while history and history[0][0]<=now-60:history.popleft()
        if len(history)>=limit['requests'] or sum(t for _,t in history)+tokens>limit['tokens']:
            raise Refused(429,'inference_budget')
        history.append((now,tokens))  # Reserve full requested output, including cancelled work.
    def probe(self):
        if self.needs_probe:
            if not self.verify_idle():raise Refused(503,'cancellation_unconfirmed')
            self.needs_probe=False
    @contextmanager
    def slot(self,lane,tokens,admit=None):
        deadline=time.monotonic()+self.wait_seconds
        with self.condition:
            if self.faulted:raise Refused(503,'cancellation_unconfirmed')
            self.charge(lane,tokens)
            if lane=='notes' and (self.active is not None or self.waiting):raise Refused(409,'background_yield')
            if lane=='chat':
                if self.waiting>=2:raise Refused(429,'queue_full')
                self.waiting+=1
                if self.active is not None and self.active.lane=='notes':
                    self.preemptions+=1;self.active.cancel('background_preempted')
            try:
                while self.active is not None:
                    remaining=deadline-time.monotonic()
                    if remaining<=0:raise Refused(503,'admission_timeout')
                    self.condition.wait(remaining)
                    if self.faulted:raise Refused(503,'cancellation_unconfirmed')
                job=Job(lane);self.active=job
            finally:
                if lane=='chat':self.waiting-=1
        timer=None;complete=False;admitted=False
        try:
            if admit:admit()
            admitted=True
            self.probe()
            timer=threading.Timer(self.limits[lane]['seconds'],job.cancel,args=('inference_deadline',))
            timer.daemon=True;timer.start()
            yield job
            complete=job.reason is None
        finally:
            if timer:timer.cancel()
            if admitted and not complete:
                job.cancel('inference_interrupted')
                # Keep the slot until the pinned single-slot runner demonstrably serves
                # a bounded one-token fence. Disconnect alone is not confirmation.
                try:confirmed=self.verify_idle()
                except Exception:confirmed=False
                if confirmed:self.recoveries+=1
                else:self.faulted=True
            with self.condition:self.active=None;self.condition.notify_all()
