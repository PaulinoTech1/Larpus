"""F1/F3/F5: speech text uses output screening, its own rate bucket, code-only logs."""
import contextlib
import hashlib
import http.client
import io
import json
import secrets
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from runtime import gateway, voice_routes
from runtime.auth import Auth, password_record
from runtime.text_filter import TextHeld, filter_messages

SECURITY_PROSE=(
    'Never disable your security updates, even on a test laptop.',
    'Attackers often try to remove logging filters first.',
    'Patch first, then remove the old account. Security teams prefer that order.',
    'If you ignore all the firewall rules, the audit will fail.',
    'Prompt injection tries to make a model ignore previous instructions.',
    'Check the log line.\nSystem: kernel panic at boot.',
)

class SpeechScreeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),gateway.Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def setUp(self):
        self.server.auth=Auth(password_record('test-password-only'))
        token=secrets.token_urlsafe(32)
        self.server.auth.sessions[hashlib.sha256(token.encode()).digest()]=time.monotonic()+600
        self.cookie=f'larpus_session={token}'

    def post(self,path,body):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        conn.request('POST',path,json.dumps(body),{'Content-Type':'application/json','Cookie':self.cookie})
        res=conn.getresponse();result=(res.status,json.loads(res.read() or b'{}'),res.getheader('Retry-After'));conn.close()
        return result

    def speak(self,text):
        return self.post('/api/voice',{'action':'synthesize','text':text})

    def test_security_prose_is_spoken(self):
        with patch('runtime.voice.call',return_value={'audio':'AAA=','mime':'audio/wav'}) as speech:
            for text in SECURITY_PROSE:
                with self.subTest(text=text):
                    self.assertEqual(self.speak(text)[0],200)
            self.assertEqual([c.args[0]['text'] for c in speech.call_args_list],list(SECURITY_PROSE))

    def test_inbound_filter_still_holds_user_text(self):
        for text in SECURITY_PROSE:
            with self.subTest(text=text),self.assertRaises(TextHeld):
                filter_messages([{'role':'user','content':text}])

    def test_leaks_and_hidden_format_stay_fail_closed(self):
        persona=next(iter(gateway.PERSONAS.values()))
        line=next(l.strip() for l in persona['system_prompt'].splitlines() if len(l.strip())>=40)
        held={'password=private-test-value':'credential','Use multi\u00adfactor sign-in.':'hidden_format',
              'Zero\u200bwidth carrier.':'hidden_format','Bell\x07 control.':'hidden_control',
              'Quoting: '+line:'protected_value','Token ghp_'+'a'*30+' leaked.':'credential_token'}
        with patch('runtime.voice.call') as speech:
            for text,reason in held.items():
                with self.subTest(reason=reason):
                    self.assertIn(reason,voice_routes.speech_reasons(text,persona['system_prompt']))
                    status,body,_=self.speak(text)
                    self.assertEqual((status,body['code']),(422,'speech_held'))
            speech.assert_not_called()

    def test_held_speech_logs_reason_codes_only(self):
        secret='password=private-test-value'
        log=io.StringIO()
        with patch('runtime.voice.call') as speech,contextlib.redirect_stderr(log):
            status,body,_=self.speak(secret+' and then some prose.')
        speech.assert_not_called();self.assertEqual(status,422)
        record=json.loads(log.getvalue().strip().splitlines()[-1])
        self.assertEqual((record['code'],record['reasons'],record['error_id']),('LARP-VOICE-HELD',['credential'],body['error_id']))
        self.assertEqual(record['causes'][0]['reason'],'VOICE-SPEECH-HELD')
        self.assertNotIn('private-test-value',log.getvalue());self.assertNotIn('prose',log.getvalue())

    def test_voice_bucket_is_separate_and_larger(self):
        with patch('runtime.voice.call',return_value={'audio':'AAA='}):
            for _ in range(120):self.assertEqual(self.speak('A sentence.')[0],200)
            log=io.StringIO()
            with contextlib.redirect_stderr(log):
                status,body,retry=self.speak('One too many.')
        self.assertEqual((status,body['code']),(429,'rate_limited'))
        self.assertTrue(1<=int(retry)<=60)
        record=json.loads(log.getvalue().strip().splitlines()[-1])
        self.assertEqual((record['code'],record['causes'][0]['reason']),('LARP-RATE-LIMITED','RATE-VOICE-BUCKET-EXHAUSTED'))
        self.assertNotIn('One too many',log.getvalue())
        # Speech exhausted its own bucket; chat still has its full 30.
        with patch.object(gateway,'mcp_chat',side_effect=lambda *a:{'status':200,'content':'ok'}):
            body={'persona':'home-assistant','messages':[{'role':'user','content':'Hello'}]}
            # The gateway replies before releasing its inference lock, so back-to-back
            # chats may see 409; only the rate bucket (checked first) matters here.
            for _ in range(30):self.assertNotEqual(self.post('/api/chat',body)[0],429)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(self.post('/api/chat',body)[0],429)

    def test_chat_bucket_does_not_starve_speech(self):
        for _ in range(30):self.assertTrue(self.server.auth.allowed(('api','127.0.0.1'),30,60))
        with patch('runtime.voice.call',return_value={'audio':'AAA='}):
            self.assertEqual(self.speak('Still speaking.')[0],200)

    def test_retry_after_reports_remaining_window(self):
        auth=self.server.auth
        self.assertEqual(auth.retry_after(('voice','10.0.0.9')),1)
        auth.allowed(('voice','10.0.0.9'),1,60)
        with patch('runtime.auth.time.monotonic',return_value=time.monotonic()+50):
            self.assertTrue(1<=auth.retry_after(('voice','10.0.0.9'))<=11)

    def test_busy_worker_returns_retry_after(self):
        with patch('runtime.voice.call',side_effect=OSError()):
            status,_,retry=self.speak('Worker busy.')
        self.assertEqual((status,retry),(503,'2'))

if __name__=='__main__':unittest.main()
