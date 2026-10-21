"""Bounded owner-only recovery journal. A failed reservation never permits launch."""
from contextlib import contextmanager
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import re
import subprocess
import uuid
from scripts.recovery_policy import GatewayIdentity, History, Policy, finite

class StateError(OSError):
    """Fixed diagnostic; underlying exception text is never a public status."""

def safe_path(path):
    for parent in (path,*path.parents):
        if parent.is_symlink():raise StateError('Recovery path redirected')
        if parent.exists() and getattr(parent.lstat(),'st_file_attributes',0)&1024:
            raise StateError('Recovery path redirected')

def protect_directory(directory,*,initialize=False):
    if os.name=='nt':
        shell=str(Path(os.environ['SYSTEMROOT'])/'System32/WindowsPowerShell/v1.0/powershell.exe')
        args=[shell,'-NoProfile','-NonInteractive','-File',str(Path(__file__).with_name('protect-recovery.ps1')),'-Target',str(directory)]
        subprocess.run(args+(['-Initialize'] if initialize else []),capture_output=True,check=True,timeout=15)
    else:
        if initialize:directory.chmod(0o700)
        if directory.stat().st_uid!=os.getuid() or directory.stat().st_mode&0o077:raise StateError('Recovery owner mismatch')

def _identity(value):
    return GatewayIdentity(**value) if value is not None else None

def _reservation(value):
    if value is None:return None
    if not isinstance(value,dict) or set(value)!={'id','expected','launched','started_monotonic'}:raise ValueError('Invalid reservation')
    if not isinstance(value['id'],str) or not re.fullmatch('[a-f0-9]{32}',value['id']):raise ValueError('Invalid attempt identity')
    if _identity(value['expected']) is None:raise ValueError('Missing expected identity')
    _identity(value['launched'])
    if not finite(value['started_monotonic']):raise ValueError('Invalid reservation time')
    return value

def decode(value):
    if not isinstance(value,dict):raise ValueError('Invalid recovery schema')
    version=value.pop('version',None)
    if type(version) is not int or version!=1:raise ValueError('Invalid recovery schema')
    if set(value)!=set(History.__dataclass_fields__):raise ValueError('Invalid recovery fields')
    value['identity']=_identity(value['identity'])
    value['reservation']=_reservation(value['reservation'])
    if not isinstance(value['attempts'],list):raise ValueError('Invalid attempt array')
    value['attempts']=tuple(value['attempts'])
    history=History(**value)
    if tuple(sorted(history.attempts))!=history.attempts:raise ValueError('Unordered attempts')
    return history

@contextmanager
def file_lock(path):
    safe_path(path)
    with path.open('a+b') as stream:
        stream.seek(0);stream.write(b'0');stream.flush();stream.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:raise StateError('Recovery lock unavailable') from exc
        try:yield
        finally:
            stream.seek(0)
            if os.name=='nt':msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)

class Journal:
    def __init__(self,directory,protect=None):
        self.directory=Path(directory).absolute()
        self.path=self.directory/'state.json'
        self.protect=protect or protect_directory

    def _directory(self):
        safe_path(self.directory)
        fresh=not self.directory.exists()
        self.directory.mkdir(parents=True,exist_ok=True)
        self.protect(self.directory,initialize=fresh)
        safe_path(self.directory)

    def read(self):
        try:
            safe_path(self.path)
            if not self.path.exists():return History()
            self._directory()
            with self.path.open('rb') as stream:raw=stream.read(65537)
            if len(raw)>65536:raise ValueError('Oversized journal')
            return decode(json.loads(raw.decode('utf-8')))
        except (OSError,ValueError,TypeError,KeyError,subprocess.SubprocessError) as exc:
            raise StateError('Recovery journal unavailable') from exc

    def write(self,history):
        temporary=None
        try:
            value={'version':1,**asdict(history)}
            raw=json.dumps(value,allow_nan=False,separators=(',',':')).encode()
            decode(json.loads(raw))
            if len(raw)>65536:raise ValueError('Oversized journal')
            self._directory();safe_path(self.path)
            temporary=self.directory/(uuid.uuid4().hex+'.tmp')
            with temporary.open('xb') as stream:
                if os.name!='nt':os.fchmod(stream.fileno(),0o600)
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
            safe_path(self.path);os.replace(temporary,self.path)
        except (OSError,ValueError,TypeError,KeyError,subprocess.SubprocessError) as exc:
            raise StateError('Recovery journal write failed') from exc
        finally:
            if temporary is not None:temporary.unlink(missing_ok=True)

    def set_armed(self,armed):
        h=self.read()
        self.write(replace(h,armed=armed))

    def reserve(self,identity,now,jitter_seconds,*,started_monotonic=0):
        h=self.read();p=Policy()
        attempts=self._eligible(h,p,now,jitter_seconds)
        token=uuid.uuid4().hex
        reservation={'id':token,'expected':asdict(identity),'launched':None,'started_monotonic':started_monotonic}
        self.write(replace(h,state='recovering',reason='dead',identity=identity,attempts=attempts+(float(now),),
                           last_wall_time=now,last_monotonic_time=started_monotonic,
                           next_attempt_wall_time=now+p.cooldown_seconds+jitter_seconds,reservation=reservation))
        return token

    def _eligible(self,h,p,now,jitter_seconds):
        if not h.armed or h.state=='held' or h.reservation is not None:raise StateError('Recovery not authorized')
        self._clock(h,p,now,jitter_seconds)
        attempts=tuple(t for t in h.attempts if now-t<p.window_seconds)
        if any(t>now for t in attempts) or len(attempts)>=p.attempt_limit:raise StateError('Recovery attempt limit held')
        return attempts

    def _clock(self,h,p,now,jitter_seconds):
        if not finite(now) or now<h.last_wall_time or now<h.next_attempt_wall_time:raise StateError('Recovery clock or cooldown held')
        if not finite(jitter_seconds) or jitter_seconds>p.jitter_max_seconds:raise StateError('Recovery jitter invalid')

    def record_launch(self,attempt_id,identity):
        h=self.read()
        if h.reservation is None or h.reservation['id']!=attempt_id:raise StateError('Recovery reservation mismatch')
        self.write(replace(h,reservation={**h.reservation,'launched':asdict(identity)}))

    def finish(self,reason):
        h=self.read()
        state='observing' if reason=='recovered' else 'held'
        self.write(replace(h,state=state,reason=reason,dead_count=0,reservation=None if state=='observing' else h.reservation))

    def singleton(self):
        try:self._directory()
        except (OSError,subprocess.SubprocessError) as exc:raise StateError('Recovery state permissions unavailable') from exc
        return file_lock(self.directory/'supervisor.lock')
