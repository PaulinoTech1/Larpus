import functools
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import test_streaming
from runtime import dlp, inference
from runtime.text_filter import TextHeld


class ExecutionSecurityTests(unittest.TestCase):
    def setUp(self):
        # These are inference/release contract tests, not corpus benchmarks.
        retrieval=patch.object(inference,'augment',side_effect=lambda messages,persona,timings=None:(messages,[]))
        retrieval.start()
        self.addCleanup(retrieval.stop)

    def test_existing_prefix_security_for_each_profile(self):
        methods=('test_sentences_released_before_generation_finishes',
                 'test_private_phrase_across_sentence_boundary_is_not_partially_released',
                 'test_fragmented_credentials_addresses_and_paths_held',
                 'test_later_hold_stops_future_release_and_quarantines_prefix',
                 'test_gpu_required_before_first_release')
        original=inference.chat
        for profile in ('verified','ultra-fast','diagnostic'):
            with self.subTest(profile=profile), patch.object(inference,'chat',functools.partial(original,execution={'profile':profile})):
                case=test_streaming.StreamingTests()
                for method in methods:getattr(case,method)()

    def test_failed_input_evidence_and_storage_cannot_release(self):
        for profile in ('verified','ultra-fast','diagnostic'):
            kwargs={'execution':{'profile':profile}}
            with self.subTest(profile=profile),patch.object(inference,'ollama') as model:
                with patch.object(inference,'messages_for',side_effect=TextHeld('scanner_unavailable',unavailable=True)):
                    self.assertEqual(inference.chat('home-assistant',[{'role':'user','content':'Hello'}],**kwargs)['status'],503)
                with patch.object(inference,'augment',side_effect=ValueError('corrupt index')):
                    self.assertEqual(inference.chat('home-assistant',[{'role':'user','content':'Hello'}],**kwargs)['status'],503)
                model.assert_not_called()
            with patch.object(inference,'active_model',return_value='qwen3.5:27b-q4_K_M'),patch.object(inference,'gpu_placement',return_value='GPU'),patch.object(inference,'ollama',return_value={'message':{'content':'Useful response.'}}),patch.object(dlp,'secure_directory',side_effect=OSError('denied')):
                result=inference.chat('home-assistant',[{'role':'user','content':'Hello'}],**kwargs)
                self.assertEqual(result['status'],503)
                self.assertNotIn('content',result)

    def test_identical_output_replay_keeps_approved_bytes(self):
        original=inference.chat
        results=[]
        for profile in ('verified','ultra-fast','diagnostic'):
            with patch.object(inference,'chat',functools.partial(original,execution={'profile':profile})):
                result,chunks,_=test_streaming.StreamingTests().run_stream(['Good morning. ','A second sentence. ','Done.'])
                if profile=='diagnostic':
                    self.assertIn('model_first_text',result['execution_trace_ms'])
                    self.assertIn('first_approved',result['execution_trace_ms'])
                results.append((result['status'],result['content'],chunks,result['citation_check']))
        self.assertEqual(results[0],results[1])
        self.assertEqual(results[0],results[2])

    def test_policy_and_clean_delete_failure_for_every_profile(self):
        for profile in ('verified','ultra-fast','diagnostic'):
            with tempfile.TemporaryDirectory() as temporary,patch.object(dlp,'QUARANTINE',Path(temporary)/'quarantine'),patch.object(inference,'active_model',return_value='qwen3.5:27b-q4_K_M'),patch.object(inference,'gpu_placement',return_value='GPU'),patch.object(inference,'ollama',return_value={'message':{'content':'Useful response.'}}):
                for failure in ('policy','delete'):
                    guard=patch.object(dlp,'policy',side_effect=ValueError()) if failure=='policy' else patch.object(Path,'unlink',side_effect=OSError())
                    with guard:
                        result=inference.chat('home-assistant',[{'role':'user','content':'Hello'}],execution={'profile':profile})
                        self.assertEqual(result['status'],503)
                        self.assertNotIn('content',result)

    def test_cancel_or_truncation_then_next_request_is_clean(self):
        for profile in ('verified','ultra-fast','diagnostic'):
            for failure in ('cancel','truncation'):
                chunks=[]
                def frames():
                    yield {'message':{'content':'First sentence. '}}
                    if failure=='truncation':raise OSError('upstream ended')
                    yield {'message':{'content':'Second sentence. '},'done':True}
                def approved(text):
                    chunks.append(text)
                    if failure=='cancel':raise OSError('cancelled')
                with tempfile.TemporaryDirectory() as temporary,patch.object(dlp,'QUARANTINE',Path(temporary)/'quarantine'),patch.object(inference,'active_model',return_value='qwen3.5:27b-q4_K_M'),patch.object(inference,'gpu_placement',return_value='GPU'),patch.object(inference,'chat_stream',return_value=frames()):
                    result=inference.chat('home-assistant',[{'role':'user','content':'Hello'}],on_chunk=approved,execution={'profile':profile})
                    self.assertEqual(result['status'],502)
                    self.assertNotIn('content',result)
                fresh=[]
                with tempfile.TemporaryDirectory() as temporary,patch.object(dlp,'QUARANTINE',Path(temporary)/'quarantine'),patch.object(inference,'active_model',return_value='qwen3.5:27b-q4_K_M'),patch.object(inference,'gpu_placement',return_value='GPU'),patch.object(inference,'chat_stream',return_value=iter([{'message':{'content':'New reply.'},'done':True}])):
                    result=inference.chat('home-assistant',[{'role':'user','content':'Hello'}],on_chunk=fresh.append,execution={'profile':profile})
                    self.assertEqual(result['status'],200)
                    self.assertEqual(fresh,['New reply.'])
