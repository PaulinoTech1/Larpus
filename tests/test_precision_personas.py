"""Configuration contracts; these do not measure model reasoning accuracy."""
import json
from pathlib import Path
import unittest
from runtime.agents import load_personas, messages_for


class PrecisionPersonaTests(unittest.TestCase):
    def test_verification_guidance_survives_skill_selection(self):
        personas = load_personas()
        for role in ('mathematician', 'quantum-mechanics-professor'):
            persona = personas[role]
            for skill in [None, *persona['skills']]:
                history = [{'role': 'user', 'content': 'Explain the assumptions.'}]
                messages = messages_for(persona, history, skill)
                self.assertIn('Verification status:', messages[0]['content'])
                self.assertIn('not independent evidence', messages[0]['content'])
                self.assertEqual(messages[1:], history)

    def test_failure_cases_have_expected_results_and_status_rubrics(self):
        root = Path(__file__).resolve().parents[1]
        cases = json.loads((root / 'evals/companion.json').read_text())['cases']
        for role, prefix in [('mathematician', 'math-'), ('quantum-mechanics-professor', 'quantum-')]:
            rows = [c for c in cases if c['id'].startswith(prefix) and 'Verification status' in c['rubric'][-1]]
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(c['persona'] == role and len(c['rubric']) == 3 for c in rows))
            self.assertTrue(all('Verification status' in c['rubric'][-1] for c in rows))
