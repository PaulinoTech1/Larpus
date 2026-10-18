"""Offline freshness signals. Age requests review; reviewed links establish change."""
from datetime import date
import re


def complete_date(value):
    if not value:
        return None
    # Use the end of an imprecise period to avoid prematurely marking it stale.
    if len(value) == 4:
        return date(int(value), 12, 31)
    if len(value) == 7:
        year, month = map(int, value.split('-'))
        from calendar import monthrange
        return date(year, month, monthrange(year, month)[1])
    return date.fromisoformat(value)


def review_interval(item):
    identity = (item.get('title', '') + ' ' + item.get('source_url', '')).lower()
    if re.search(r'pricing|subscription|plan limits|model availability', identity):
        return 30, 'volatile product information'
    if re.search(r'kernel|security|vulnerability|intune|entra|azure|microsoft 365|support lifecycle|cryptographic|crypto.agility', identity):
        return 180, 'operational or security guidance'
    return 730, 'general research review'


def assess(item, today=None):
    today = today or date.today()
    limit, category = review_interval(item)
    value = reference_date(item)
    baseline = complete_date(value)
    flags = lifecycle(item)
    if baseline is None:
        flags.append('freshness_unknown')
    elif value > today.isoformat()[:len(value)]:
        flags.append('future_date_review')
    elif (today - baseline).days > limit:
        flags.append('review_due')
    return {'checked_on': today.isoformat(), 'signals': flags or ['no_known_change'],
            'review_interval_days': limit, 'category': category,
            'date_basis': 'reviewed_on' if item.get('reviewed_on') else 'publication_or_revision',
            'basis_date': baseline.isoformat() if baseline else None}


def lifecycle(item):
    mapping = {'supersedes': 'superseded_in_scope', 'corrects': 'corrected_in_scope',
               'conflicts': 'conflicting_evidence'}
    return sorted({mapping[link['kind']] for link in item.get('relationships', [])
                   if link.get('old') == item.get('id') and link.get('kind') in mapping})


def reference_date(item):
    return item.get("reviewed_on") or item.get("revised_on") or item.get("published_on")
