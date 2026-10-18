import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from runtime import voice


class VoiceAdmissionTests(unittest.TestCase):
    def test_replay_waits_for_unfinished_synthesis(self):
        entered=threading.Event();release=threading.Event();calls=[]
        def run(*args,**kwargs):
            calls.append(json.loads(kwargs['input']))
            if len(calls)==1:
                entered.set()
                if not release.wait(3):raise TimeoutError('test timeout')
            return SimpleNamespace(stdout=b'{"audio":"AAA="}')
        with tempfile.TemporaryDirectory() as temporary:
            profile=Path(temporary)/'profile.json';profile.write_text('{}')
            with patch.object(voice,'PROFILE',profile),patch.object(voice,'LOCK',threading.Lock()),patch.object(voice,'preflight'),patch.object(voice,'wsl_command',return_value=['fixed-worker']),patch.object(voice.subprocess,'run',side_effect=run),ThreadPoolExecutor(max_workers=2) as pool:
                first=pool.submit(voice.call,{'action':'synthesize','text':'Prepared sentence.'})
                self.assertTrue(entered.wait(1))
                second=pool.submit(voice.call,{'action':'synthesize','text':'Manual replay.'})
                try:
                    threading.Event().wait(.1)
                    self.assertFalse(second.done(),'replay must wait rather than report worker busy')
                    self.assertEqual(len(calls),1,'worker operations must remain serial')
                finally:release.set()
                self.assertIn('audio',first.result(timeout=2))
                self.assertIn('audio',second.result(timeout=2))
                self.assertEqual([r['text'] for r in calls],['Prepared sentence.','Manual replay.'])


if __name__=='__main__':unittest.main()
