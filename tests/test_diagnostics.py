import contextlib
import io
import json
import unittest
from unittest.mock import patch
from runtime import diagnostics

class DiagnosticTests(unittest.TestCase):
    def test_cause_chain_is_useful_without_message_or_secret(self):
        try:
            try:raise OSError(13,'SECRET prompt C:/owner/private')
            except OSError as cause:raise ValueError('SECRET transcript') from cause
        except ValueError as exc:
            sink=io.StringIO();out=io.StringIO()
            with contextlib.redirect_stderr(sink),contextlib.redirect_stdout(out):
                error=diagnostics.failure('LARP-MCP-UNAVAILABLE',exc,'Agent unavailable')
        record=json.loads(sink.getvalue())
        self.assertNotIn('SECRET',sink.getvalue())
        self.assertNotIn('C:/owner',sink.getvalue())
        self.assertEqual(out.getvalue(),'')
        self.assertEqual(record['error_id'],error.error_id)
        self.assertRegex(error.error_id,r'^[a-f0-9]{16}$')
        self.assertEqual([c['type'] for c in record['causes']],['ValueError','PermissionError'])
        self.assertEqual(record['causes'][1]['errno'],13)
        self.assertTrue(record['causes'][0]['frames'])
        self.assertIn('next_step',record)

    def test_cycle_is_bounded_and_links_existing_id(self):
        exc=diagnostics.DiagnosticError('LARP-NOTES-WORKER','a'*16,'private')
        exc.__cause__=exc
        sink=io.StringIO()
        with contextlib.redirect_stderr(sink):diagnostics.report('LARP-NOTES-TRANSPORT',exc)
        record=json.loads(sink.getvalue())
        self.assertEqual(len(record['causes']),1)
        self.assertEqual(record['causes'][0]['related_error_id'],'a'*16)

    def test_broken_sink_preserves_failure(self):
        with patch('runtime.diagnostics.sys.stderr') as sink:
            sink.write.side_effect=OSError('sink unavailable')
            error=diagnostics.failure('LARP-VOICE-UNAVAILABLE',TimeoutError('secret'),'Voice unavailable')
        self.assertIsInstance(error,OSError)
        self.assertRegex(error.error_id,r'^[a-f0-9]{16}$')

    def test_unknown_code_rejected(self):
        with self.assertRaises(ValueError):diagnostics.report('untrusted',ValueError())

    def test_exact_known_message_has_specific_reason_and_action(self):
        detail=diagnostics.describe(ValueError('Model stream ended without completion'))
        self.assertEqual(detail['message'],'Model stream ended without completion')
        self.assertEqual(detail['message_source'],'reviewed-literal')
        self.assertIn('framing',detail['action'])

    def test_unknown_message_cannot_smuggle_known_text(self):
        detail=diagnostics.describe(ValueError('Invalid model content SECRET token'))
        self.assertEqual(detail['reason'],'UNCLASSIFIED')
        self.assertNotIn('SECRET',json.dumps(detail))

    def test_json_coordinates_without_raw_document(self):
        try:json.loads('{"SECRET":\n broken}')
        except json.JSONDecodeError as exc:detail=diagnostics.describe(exc)
        self.assertEqual(detail['reason'],'INVALID-JSON')
        self.assertEqual(detail['json_line'],2)
        self.assertNotIn('SECRET',json.dumps(detail))

    def test_timeout_is_actionable_without_subprocess_command(self):
        import subprocess
        detail=diagnostics.describe(subprocess.TimeoutExpired(['private-command','SECRET'],120))
        self.assertEqual(detail['reason'],'TIMEOUT')
        self.assertNotIn('SECRET',json.dumps(detail))

    def test_notes_stdout_stays_protocol_only(self):
        from runtime import notes_worker
        source=io.StringIO(json.dumps({'model':'local','messages':[]})+'\n')
        output=io.StringIO();errors=io.StringIO()
        with patch('runtime.notes_worker.sys.stdin',source),patch('runtime.notes_worker.ollama',side_effect=OSError('SECRET job')):
            with contextlib.redirect_stdout(output),contextlib.redirect_stderr(errors):notes_worker.main()
        reply=json.loads(output.getvalue());record=json.loads(errors.getvalue())
        self.assertEqual(reply['error_id'],record['error_id'])
        self.assertEqual(reply['diagnostic_code'],'LARP-NOTES-WORKER')
        self.assertNotIn('SECRET',output.getvalue()+errors.getvalue())
