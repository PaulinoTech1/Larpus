from datetime import date
import unittest
from runtime.freshness import assess


class FreshnessTests(unittest.TestCase):
    def test_age_never_proves_deprecation(self):
        result = assess({'id': 'old', 'published_on': '1990'}, date(2026, 10, 12))
        self.assertEqual(result['signals'], ['review_due'])

    def test_pricing_review_is_more_frequent_than_math(self):
        item = {'published_on': '2026-08-01'}
        now = date(2026, 10, 12)
        self.assertIn('review_due', assess({**item, 'title': 'API pricing'}, now)['signals'])
        self.assertEqual(assess({**item, 'title': 'Calculus'}, now)['signals'], ['no_known_change'])

    def test_missing_dates_and_snapshot_do_not_prove_freshness(self):
        self.assertEqual(assess({'retrieved_at': '2026-10-12'})['signals'], ['freshness_unknown'])

    def test_correction_applies_only_to_old_identity(self):
        link = {'old': 'a', 'new': 'b', 'kind': 'corrects', 'scope': 'one calculation'}
        self.assertIn('corrected_in_scope', assess({'id': 'a', 'relationships': [link]})['signals'])
        self.assertNotIn('corrected_in_scope', assess({'id': 'b', 'relationships': [link]})['signals'])

    def test_recent_review_and_partial_year(self):
        self.assertEqual(assess({'published_on': '1990', 'reviewed_on': '2026-10-01'}, date(2026, 10, 12))['signals'], ['no_known_change'])
        self.assertEqual(assess({'published_on': '2025'}, date(2026, 1, 1))['basis_date'], '2025-12-31')

    def test_future_date_is_a_review_signal(self):
        self.assertEqual(assess({'published_on': '2027'}, date(2026, 10, 12))['signals'], ['future_date_review'])
