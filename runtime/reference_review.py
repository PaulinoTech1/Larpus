"""Exact owner-reviewed reference exceptions; never applied to user messages."""
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from runtime.text_filter import inspect_message, TextHeld, RULES


def inspect_reference(text, source_id):
    try:
        return inspect_message(text)
    except TextHeld as exc:
        if exc.unavailable or exc.scan_complete is False or exc.reason not in ('hidden_control', 'hidden_format', 'unicode_carrier_or_incomplete_scan'):
            raise
        reason = exc.reason
    path = Path(__file__).resolve().parents[1] / 'config/reference-reviews.json'
    if not path.exists():
        raise TextHeld(reason)
    value = json.loads(path.read_text(encoding='utf8'))
    digest = hashlib.sha256(text.encode()).hexdigest()
    if digest not in value.get('sources', {}).get(source_id, {}).get('text_sha256', []):
        raise TextHeld(reason)
    shadow = unicodedata.normalize('NFKC', text).casefold()
    for name, pattern in RULES:
        if pattern.search(shadow) or pattern.search(re.sub(r'\s+', ' ', shadow)):
            raise TextHeld(name)
    return text
