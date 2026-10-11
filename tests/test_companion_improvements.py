import socket,struct,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
from runtime import voice_worker
from runtime.voice_worker import receive,send_frame
from runtime.inference import citation_check
class CompanionTests(unittest.TestCase):
    def test_framing_roundtrip(self):
        a,b=socket.socketpair()
        with a,b:
            send_frame(a,{'text':'local'},100)
            self.assertEqual(receive(b,100),{'text':'local'})
    def test_framing_bound(self):
        a,b=socket.socketpair()
        with a,b:
            a.sendall(struct.pack('!I',101))
            with self.assertRaises(ValueError):receive(b,100)
    def test_framing_truncated(self):
        a,b=socket.socketpair()
        with a,b:
            a.sendall(struct.pack('!I',4)+b'{}');a.shutdown(socket.SHUT_WR)
            with self.assertRaises(ValueError):receive(b,100)
    def test_identifier_check_is_not_entailment(self):
        result=citation_check('Claim [known-source] and [invented-source]',[{'id':'known-source'}])
        self.assertEqual(result['status'],'unknown-identifiers')
        self.assertIn('invented-source',result['unknown'])

    def test_cpu_voice_model_is_loaded_once(self):
        voice=object();loader=Mock(return_value=voice)
        with patch.dict(voice_worker.MODELS,{},clear=True),patch.dict('sys.modules',{'piper':SimpleNamespace(PiperVoice=SimpleNamespace(load=loader))}):
            self.assertIs(voice_worker.speech_models('tts'),voice)
            self.assertIs(voice_worker.speech_models('tts'),voice)
            loader.assert_called_once_with('/models/en_GB-alan-medium.onnx')

    def test_held_source_preview_does_not_leak_or_hold_safe_answer(self):
        from runtime import inference
        source={'id':'safe-source','title':'A reference','url':'https://example.com','snapshot':'2026-10-09','locator':'page 1','text':'private preview'}
        frame={'message':{'content':'A useful reply [safe-source].'}}
        with patch.object(inference,'augment',side_effect=lambda p,r:(p,[source])),patch.object(inference,'gpu_placement',return_value='GPU'),patch.object(inference,'ollama',return_value=frame),patch.object(inference,'gate',side_effect=[{'status':200,'content':frame['message']['content']},{'status':422,'error':'held'}]):
            result=inference.chat('home-assistant',[{'role':'user','content':'Hello'}])
        self.assertEqual(result['status'],200)
        self.assertEqual(result['citation_check']['status'],'identified')
        self.assertNotIn('private preview',str(result))
        self.assertIn('withheld',result['sources'][0]['preview'])
