"""Owner-only offline report; does not edit source data or contact publishers."""
import json
from pathlib import Path
import sys
from collections import Counter
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.provenance import read
from runtime.freshness import assess

root = Path(__file__).resolve().parents[1]
entries = read(root / 'knowledge')
rows = [{'id': sid, 'title': item.get('title'), **assess(item)} for sid, item in entries.items()]
output = root / 'data/source-freshness.json'
output.write_text(json.dumps({'version': 1, 'sources': rows}, indent=2) + '\n', encoding='utf8')
print(json.dumps({'sources': len(rows), 'signals': dict(Counter(signal for row in rows for signal in row['signals'])), 'report': str(output)}))
