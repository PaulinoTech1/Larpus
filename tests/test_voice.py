import io
import wave
import unittest
from unittest.mock import patch
from runtime.voice_worker import validate_wav
from runtime import gateway

class VoiceTests(unittest.TestCase):
    def audio(self,rate=16000,frames=1600):
        out=io.BytesIO()
        with wave.open(out,'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(b'\0\0'*frames)
        return out.getvalue()

    def test_audio_boundaries(self):
        validate_wav(self.audio())
        for raw in (b'',b'bad wav',self.audio(rate=44100),self.audio(frames=480001),self.audio()[:-2]):
            with self.assertRaises((ValueError,EOFError,wave.Error)):
                validate_wav(raw)

if __name__=='__main__':
    unittest.main()
