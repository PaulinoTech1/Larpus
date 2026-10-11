"""Owner-local diagnostic lookup. No HTTP endpoint or model access."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]

def lookup(identifier,root=ROOT):
    if not re.fullmatch(r'[a-f0-9]{16}',identifier):raise ValueError('Expected a 16-character lowercase hexadecimal diagnostic ID')
    paths=list((root/'data/releases').glob('*.gateway.log'))
    paths += [root/'data/study-notes.log',root/'data/study-notes-worker.log']
    matches=[]
    for path in paths:
        if not path.is_file():continue
        with path.open('rb') as source:
            # Bounded recent tail; no recursive scan of owner data.
            size=path.stat().st_size;source.seek(max(0,size-16*1024*1024))
            if source.tell():source.readline()
            for raw in source:
                if len(raw)>65536 or identifier.encode() not in raw:continue
                record=matching_record(raw,identifier)
                if record is not None:matches.append({'log':path.name,'diagnostic':record})
                if len(matches)>=50:return matches
    return matches

def matching_record(raw,identifier):
    try:record=json.loads(raw)
    except (ValueError,UnicodeError):return None
    if not isinstance(record,dict) or record.get('schema')!='larpus.diagnostic/v1':return None
    causes=record.get('causes',[])
    linked=isinstance(causes,list) and any(isinstance(c,dict) and c.get('related_error_id')==identifier for c in causes)
    return record if record.get('error_id')==identifier or linked else None

def main():
    parser=argparse.ArgumentParser(description='Find exact or linked diagnostic IDs in recent owner logs.')
    parser.add_argument('error_id');args=parser.parse_args()
    try:matches=lookup(args.error_id)
    except (OSError,ValueError) as exc:
        print('Diagnostic lookup failed: '+type(exc).__name__+'. Check ID and owner log permissions.',file=sys.stderr);return 2
    print(json.dumps({'matches':matches,'scope':'Up to 50 matches in the last 16 MiB of each fixed gateway/notes log; missing does not prove no failure.'},indent=2))
    return 0 if matches else 1

if __name__=='__main__':raise SystemExit(main())
