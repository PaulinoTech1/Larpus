import io
import wave
import unittest
from unittest.mock import patch
from runtime.voice_worker import validate_wav, SpeechOnlyModel
from runtime import voice_worker
from types import SimpleNamespace
from unittest.mock import Mock
from runtime import gateway

class VoiceTests(unittest.TestCase):
    def test_empty_synthesis_is_playable_and_does_not_break_next_sentence(self):
        chunk=SimpleNamespace(sample_rate=22050,sample_width=2,sample_channels=1,audio_int16_bytes=b'\1\0'*2205)
        voice=SimpleNamespace(config=SimpleNamespace(sample_rate=22050),synthesize=Mock(side_effect=[iter([]),iter([chunk])]))
        with patch.object(voice_worker,'speech_models',return_value=voice),patch.dict('sys.modules',{'piper':SimpleNamespace(SynthesisConfig=lambda **kwargs:None)}):
            for text,empty in (('...',True),('The next sentence continues.',False)):
                result=voice_worker.run({'action':'synthesize','text':text})
                import base64
                with wave.open(io.BytesIO(base64.b64decode(result['audio'])),'rb') as audio:
                    self.assertEqual((audio.getnchannels(),audio.getsampwidth(),audio.getframerate()),(1,2,22050))
                    self.assertGreater(audio.getnframes(),0)
                    self.assertEqual(result.get('no_speech',False),empty)

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

    def test_speech_policy_filters_uncertain_segments(self):
        good=SimpleNamespace(text='Real speech',no_speech_prob=0.1,avg_logprob=-0.2,compression_ratio=1.1)
        noise=SimpleNamespace(text='Invented speech',no_speech_prob=0.9,avg_logprob=-0.1,compression_ratio=1)
        uncertain=SimpleNamespace(text='Unclear',no_speech_prob=0.1,avg_logprob=-1.5,compression_ratio=1)
        repeated=SimpleNamespace(text='Echo echo',no_speech_prob=0.1,avg_logprob=-0.1,compression_ratio=3)
        model=Mock();model.transcribe.return_value=([noise,good,uncertain,repeated],'info')
        segments,info=SpeechOnlyModel(model).transcribe('samples',beam_size=3)
        self.assertEqual(list(segments),[good])
        self.assertEqual(info,'info')
        options=model.transcribe.call_args.kwargs
        self.assertTrue(options['vad_filter'])
        self.assertFalse(options['condition_on_previous_text'])
        self.assertEqual(options['temperature'],0)

if __name__=='__main__':
    unittest.main()
