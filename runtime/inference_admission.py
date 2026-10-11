"""Owner-host cooperative inference admission; never an MCP/model tool."""
from contextlib import contextmanager
import os
from pathlib import Path
import time

class Busy(TimeoutError):pass

class Admission:
    def __init__(self,directory):self.directory=Path(directory)

    @contextmanager
    def lock(self,name):
        self.directory.mkdir(parents=True,exist_ok=True)
        with (self.directory/(name+'.lock')).open('a+b') as handle:
            handle.seek(0);handle.write(b'0');handle.flush();handle.seek(0)
            try:
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError as exc:raise Busy('Inference admission busy') from exc
            try:yield
            finally:
                handle.seek(0)
                if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
                else:fcntl.flock(handle,fcntl.LOCK_UN)

    @contextmanager
    def interactive(self,timeout=60):
        # Hold priority while waiting: no new background request may jump ahead.
        deadline=time.monotonic()+timeout
        with self.lock('interactive'):
            while True:
                ticket=self.lock('inference')
                try:ticket.__enter__();break
                except Busy:
                    if time.monotonic()>=deadline:raise
                    time.sleep(.1)
            try:yield
            finally:ticket.__exit__(None,None,None)

    @contextmanager
    def background(self,deadline):
        while time.time()<deadline:
            ticket=self.lock('inference')
            try:
                with self.lock('interactive'):ticket.__enter__()
                break
            except Busy:time.sleep(min(.25,max(0,deadline-time.time())))
        else:raise Busy('Background deadline reached')
        try:yield
        finally:ticket.__exit__(None,None,None)
