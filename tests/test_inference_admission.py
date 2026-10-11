import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from runtime.inference_admission import Admission,Busy

CHILD="""
import sys,time
from pathlib import Path
from runtime.inference_admission import Admission
root=Path(sys.argv[1]);mode=sys.argv[2];a=Admission(root)
if mode=='foreground':
    with a.interactive(timeout=5):
        (root/'foreground').touch()
        while not (root/'release').exists():time.sleep(.02)
elif mode=='background':
    with a.background(time.time()+5):(root/'background').touch()
else:
    with a.lock('interactive'):
        (root/'held').touch();time.sleep(30)
"""

class AdmissionTests(unittest.TestCase):
    def wait(self,predicate):
        deadline=time.monotonic()+5
        while not predicate():
            if time.monotonic()>deadline:self.fail('Child synchronization timeout')
            time.sleep(.02)

    def child(self,root,mode):
        p=subprocess.Popen([sys.executable,'-c',CHILD,str(root),mode],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.addCleanup(lambda:p.poll() is None and p.kill())
        return p

    def test_waiting_chat_gets_next_slot_before_background(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);a=Admission(root)
            held=a.background(time.time()+5);held.__enter__()
            foreground=self.child(root,'foreground')
            def reserved():
                try:
                    with a.lock('interactive'):return False
                except Busy:return True
            self.wait(reserved)
            background=self.child(root,'background')
            held.__exit__(None,None,None)
            self.wait(lambda:(root/'foreground').exists())
            self.assertFalse((root/'background').exists())
            (root/'release').touch()
            for child in (foreground,background):
                out,err=child.communicate(timeout=5);self.assertEqual(child.returncode,0,err.decode())
            self.assertTrue((root/'background').exists())

    def test_timeout_and_exception_release_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            a=Admission(directory)
            with a.lock('inference'):
                with self.assertRaises(Busy):
                    with a.interactive(timeout=0):pass
                with a.lock('interactive'):pass
            with self.assertRaises(ValueError):
                with a.interactive():raise ValueError('failed request')
            with a.background(time.time()+1):pass
            with self.assertRaises(Busy):
                with a.background(0):pass

    def test_process_death_releases_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);child=self.child(root,'hold')
            self.wait(lambda:(root/'held').exists())
            child.kill();child.communicate(timeout=5)
            with Admission(root).interactive(timeout=0):pass

if __name__=='__main__':unittest.main()
