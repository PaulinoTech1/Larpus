import io
import json
import contextlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from runtime import diagnostics, inference, knowledge, retrieval
from runtime.agents import load_personas, messages_for, persona_known
from runtime.skills import CatalogRejected

HISTORY=[{'role':'user','content':'Hello'}]

class CatalogIsolationTests(unittest.TestCase):
    def test_non_object_persona_is_rejected_without_removing_valid_personas(self):
        from runtime import agents
        valid=agents.ROOT/'agents/personas/home-assistant.json'
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);folder=root/'agents/personas';folder.mkdir(parents=True)
            (folder/'home-assistant.json').write_bytes(valid.read_bytes())
            for value in (None,[],[{}],True,7,'persona'):
                with self.subTest(value=value),patch.object(agents,'ROOT',root):
                    (folder/'broken.json').write_text(json.dumps(value),encoding='utf-8')
                    self.assertEqual(set(agents.load_personas()),{'home-assistant'})
                    self.assertEqual(agents.persona_rejections(),{'broken':'Invalid persona fields'})

    def test_skill_catalog_failure_is_not_a_bad_request_or_an_evidence_failure(self):
        sink=io.StringIO()
        with patch('runtime.skills.load_skills',side_effect=CatalogRejected('Skill changed; local review and registration required')),contextlib.redirect_stderr(sink):
            rejected=inference.chat('home-assistant',HISTORY,'home-planning')
        self.assertEqual(rejected['status'],503)
        self.assertEqual(rejected['diagnostic_code'],'LARP-CATALOG-REJECTED')
        self.assertNotIn('Skill changed',rejected['error'])
        record=json.loads(sink.getvalue())
        self.assertEqual(record['code'],'LARP-CATALOG-REJECTED')
        self.assertEqual(record['causes'][0]['reason'],'CATALOG-REJECTED')
        self.assertEqual(record['causes'][0]['message_source'],'reviewed-literal')
        malformed=inference.chat('home-assistant',[{'role':'user','content':''}])
        self.assertEqual(malformed['status'],400)
        self.assertNotIn('diagnostic_code',malformed)
        denied=inference.chat('home-assistant',HISTORY,'it-interview')
        self.assertEqual(denied['status'],400)
        with patch('runtime.inference.summaries',side_effect=CatalogRejected('Unregistered local skill folder')):
            listed=inference.personas()
        self.assertEqual(listed['diagnostic_code'],'LARP-CATALOG-REJECTED')
        self.assertNotIn('personas',listed)
        self.assertNotIn('Unregistered',listed['error'])

    def test_evidence_exception_keeps_its_own_code(self):
        with patch('runtime.inference.augment',side_effect=RuntimeError('index missing SECRET')):
            failed=inference.chat('home-assistant',HISTORY)
        self.assertEqual(failed['diagnostic_code'],'LARP-EVIDENCE-UNAVAILABLE')
        self.assertNotIn('SECRET',failed['error'])
        with patch('runtime.inference.augment',side_effect=CatalogRejected('Invalid local skill registry')):
            catalog=inference.chat('home-assistant',HISTORY)
        self.assertEqual(catalog['diagnostic_code'],'LARP-CATALOG-REJECTED')
        self.assertNotEqual(catalog['diagnostic_code'],'LARP-EVIDENCE-UNAVAILABLE')

    def test_unreviewed_catalog_text_is_not_copied(self):
        sink=io.StringIO()
        with contextlib.redirect_stderr(sink):
            body=diagnostics.catalog_failure(CatalogRejected('SECRET path C:/owner/skill'))
        self.assertNotIn('SECRET',sink.getvalue()+json.dumps(body))
        self.assertEqual(json.loads(sink.getvalue())['causes'][0]['reason'],'UNCLASSIFIED')

    def test_one_rejected_skill_does_not_remove_the_persona(self):
        from runtime import agents, skills as skills_module
        real=agents.require_persona('home-assistant')
        kept=next(item for item in real['skills'] if item!='home-planning')
        saved=skills_module.load_skills()
        def partial():
            skills_module._REJECTED.clear()
            skills_module._REJECTED['home-planning']='Skill changed; local review and registration required'
            return {key:value for key,value in saved.items() if key!='home-planning'}
        with patch('runtime.skills.load_skills',side_effect=partial),patch('runtime.agents.load_skills',side_effect=partial):
            persona=agents.require_persona('home-assistant')
            self.assertNotIn('home-planning',persona['skills'])
            self.assertIn(kept,persona['skills'])
            self.assertEqual(skills_module.skill_rejections()['home-planning'],'Skill changed; local review and registration required')
            rejected=inference.chat('home-assistant',HISTORY,'home-planning')
            prepared=messages_for(persona,HISTORY)
        self.assertEqual(rejected['status'],503)
        self.assertEqual(rejected['scope'],'skill')
        self.assertNotIn('Skill changed',rejected['error'])
        self.assertIn(persona['system_prompt'],prepared[0]['content'])
        self.assertFalse(persona_known('not-a-persona'))
        self.assertEqual(knowledge._retrieve('not-a-persona','hello there',100),[])

    def test_evidence_literal_is_reviewed(self):
        detail=diagnostics.describe(ValueError('Knowledge database hash mismatch'))
        self.assertEqual(detail['reason'],'EVIDENCE-REJECTED')
        self.assertEqual(detail['message_source'],'reviewed-literal')

class RetrievalAndCitationTests(unittest.TestCase):
    def setUp(self):retrieval.reset()
    def tearDown(self):retrieval.reset()

    def test_remote_miss_retries_after_thirty_seconds_without_the_exception_text(self):
        self.assertEqual(retrieval._ENGINE_RETRY_SECONDS,30.0)
        clock={'now':1000.0}
        calls=[]
        class Ready:
            pass
        def flaky():
            calls.append(1)
            if len(calls)==1:raise OSError('SECRET socket /mnt/e/private')
            return Ready()
        with patch.dict('os.environ',{'LARPUS_RETRIEVAL_WORKER':'remote'}),patch.object(retrieval,'RemoteEngine',side_effect=flaky),patch('runtime.retrieval.time.monotonic',side_effect=lambda:clock['now']):
            self.assertIsNone(retrieval.engine(knowledge.DIRECTORY))
            shown=retrieval.status(knowledge.DIRECTORY)
            self.assertEqual(shown['reason'],'OSError')
            self.assertNotIn('SECRET',json.dumps(shown))
            self.assertTrue(shown['failure_cached'])
            self.assertEqual(len(calls),1)
            clock['now']=1029.9
            self.assertIsNone(retrieval.engine(knowledge.DIRECTORY))
            self.assertEqual(len(calls),1)
            clock['now']=1030.0
            self.assertIsInstance(retrieval.engine(knowledge.DIRECTORY),Ready)
            self.assertEqual(len(calls),2)
            self.assertFalse(retrieval.status(knowledge.DIRECTORY)['failure_cached'])
            self.assertEqual(retrieval.status(knowledge.DIRECTORY)['reason'],'ready (remote)')
            self.assertEqual(len(calls),2)

    def test_author_catalog_failure_does_not_stick(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(knowledge,'DIRECTORY',root),patch.object(knowledge,'_AUTHORS',None):
                self.assertIsNone(knowledge.author_cite('x'))
                (root/'authors.json').write_text(json.dumps({'entries':{'x':{'cite':'Ada, 1843'}}}),encoding='utf-8')
                self.assertEqual(knowledge.author_cite('x'),'Ada, 1843')
                self.assertIsNone(knowledge.author_cite('missing'))

if __name__=='__main__':unittest.main()
