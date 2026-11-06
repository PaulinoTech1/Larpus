"""Research-archive and reuse helpers for prepare-knowledge. Owner curation only."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from runtime.knowledge import database
from scripts.research_policy import vet

KNOWLEDGE=ROOT/'knowledge'
CACHE=ROOT/'data/knowledge'
PDF_CONTROL_NORMALIZATION='pdf-control-format-to-fffd-v1'

def carried_rejections(previous,reused):
    # Reuse mode re-parses every non-reused source and records its rejections again, so earlier rows
    # are kept only for reused sources; a reused source has indexed text, so its old parse failures are stale.
    return [r for r in previous if r.get('source_id') in reused and r.get('reason')!='parse_failed']

def candidate_reused_ids(previous_sources,research_entries):
    research_ids={e['id']:e['sha256'] for e in research_entries}
    renormalized={e['id'] for e in research_entries if e.get('text_normalization')}  # always parsed again
    return {e['id'] for e in previous_sources if research_ids.get(e['id'])==e['sha256'] and e['id'] not in renormalized}

def filter_reused_rows(records,reused):
    reusable={r[0] for r in records if r[4]!='metadata only'}
    reused=reused & reusable
    return [r for r in records if r[0] in reused], reused

def reused_index(reuse_research):
    """Return (records, rejected, reused_ids) from the previous index when reuse is requested."""
    if not reuse_research:
        return [], [], set()
    previous=json.loads((KNOWLEDGE/'manifest.json').read_text())
    rejected=json.loads((CACHE/'rejected-passages.json').read_text())
    research_entries=json.loads((ROOT/'research/catalog.json').read_text())['entries']
    reused=candidate_reused_ids(previous['sources'],research_entries)
    with closing(database()) as old:
        records=[row for row in old.execute('SELECT source_id,title,url,snapshot,locator,text,role FROM chunks') if row[0] in reused]
    records,reused=filter_reused_rows(records,reused)
    return records, carried_rejections(rejected,reused), reused

def research_document(source):
    """Load one downloaded research archive entry as (entry, raw, mime)."""
    vet(source)  # Unreviewed publishers or unpinned files never reach the index.
    fmt=source.get('format','pdf')
    path=ROOT/'data/research'/source['role']/source['level']/(source['id']+'.'+fmt)
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError('Research PDF checksum mismatch: '+source['id'])
    if source.get('ocr_sha256'):
        # Image-only PDF with an owner-approved offline OCR sidecar pinned in the catalog (no OCR runs here).
        ocr=path.with_name(source['id']+'.ocr.txt').read_bytes()
        if hashlib.sha256(ocr).hexdigest()!=source['ocr_sha256']:raise ValueError('OCR sidecar checksum mismatch: '+source['id'])
        raw,fmt=ocr,'ocr'
    entry={'id':source['id'],'title':source['title'],'url':source['source_url'],'roles':[source['role']],'snapshot':source.get('fetched_at','')[:10],'publication':source['year'],'sha256':source['sha256'],'topics':source.get('topics',[])}
    if source.get('text_normalization'):
        if source['text_normalization']!=PDF_CONTROL_NORMALIZATION or fmt!='pdf':raise ValueError('Unknown text normalization: '+source['id'])
        entry['text_normalization']=source['text_normalization']
    mime={'html':'text/html','txt':'text/plain','ocr':'text/x-larpus-ocr-pages'}.get(fmt,'application/pdf')
    return entry, raw, mime

def research_documents():
    """Every downloaded research archive entry as (entry, raw, mime) triples."""
    research=json.loads((ROOT/'research/catalog.json').read_text(encoding='utf-8'))
    documents=[]
    for source in research['entries']:
        if source.get('full_text_status')!='downloaded':
            continue
        documents.append(research_document(source))
    return documents
