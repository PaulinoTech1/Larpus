"""Owner-only offline metadata export and non-destructive saved-note audit."""
from contextlib import closing
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime.provenance import date_value,validate_relations,section
ROOT=Path(__file__).resolve().parents[1]

def load(path):return json.loads(path.read_text(encoding='utf8')) if path.exists() else {}

def build(root=ROOT):
    directory=root/'knowledge';entries={}
    manifest=load(directory/'manifest.json')
    pins={s['id']:s for s in manifest.get('sources',[])}
    for doc in load(directory/'sources.json').get('documents',[]):
        entries[doc['id']]={'id':doc['id'],'title':doc['title'],'source_url':doc['url'],
            'document_authors':doc.get('authors',[]),'document_authors_status':'reviewed metadata' if doc.get('authors') else 'unknown',
            'published_on':date_value(doc.get('published_on')),'revised_on':date_value(doc.get('revised_on')),
            'retrieved_at':doc.get('fetched_at'),'snapshot_on':doc.get('snapshot'),
            'version_scope':doc.get('version_scope'),'source_sha256':doc.get('sha256'),
            'metadata_basis':'knowledge/sources.json reviewed catalog; dates absent unless explicitly recorded'}
    for doc in load(root/'research/catalog.json').get('entries',[]):
        entries[doc['id']]={'id':doc['id'],'title':doc['title'],'source_url':doc['source_url'],
            'document_authors':doc.get('authors',[]),'document_authors_status':'reviewed repository metadata' if doc.get('authors') else 'unknown',
            'published_on':date_value(doc.get('year')),'revised_on':date_value(doc.get('revised_on')),
            'retrieved_at':doc.get('fetched_at'),'source_sha256':doc.get('sha256'),
            'metadata_evidence_url':doc.get('degree_evidence_url',doc['source_url']),
            'metadata_basis':'research/catalog.json: repository author/date metadata, not bibliography extraction'}
    if (directory/'approved.sqlite').exists():
        with closing(sqlite3.connect((directory/'approved.sqlite').resolve().as_uri()+'?mode=ro',uri=True)) as db:
            for identifier,title,url,snapshot in db.execute('SELECT DISTINCT source_id,title,url,snapshot FROM chunks'):
                if identifier not in entries:
                    pin=pins.get(identifier,{})
                    entries[identifier]={'id':identifier,'title':title,'source_url':url,'document_authors':[],
                        'document_authors_status':'unknown','published_on':date_value(pin.get('publication')),
                        'snapshot_on':snapshot,'source_sha256':pin.get('sha256'),
                        'metadata_basis':'approved index identity; snapshot is not a publication date'}
    for item in entries.values():
        authors=item['document_authors']
        if not isinstance(authors,list) or any(not isinstance(a,str) or not 1<=len(a)<=300 for a in authors):raise ValueError('Invalid reviewed authors')
    links=validate_relations(load(root/'config/source-relationships.json'),entries)
    for link in links:
        entries[link['old']].setdefault('relationships',[]).append(link)
        entries[link['new']].setdefault('relationships',[]).append(link)
    value={'version':1,'policy':'Unknown dates/authors stay unknown. Dates do not establish correctness or supersession. Bibliography names never establish document authorship.',
           'index_sha256':manifest.get('database_sha256'),'entries':dict(sorted(entries.items()))}
    raw=json.dumps(value,indent=2,ensure_ascii=False)+'\n'
    if len(raw.encode())>1_000_000:raise ValueError('Provenance exceeds runtime bound')
    return value,raw

def audit(root=ROOT):
    directory=root/'knowledge';entries=load(directory/'provenance.json').get('entries',{})
    with closing(sqlite3.connect((directory/'approved.sqlite').resolve().as_uri()+'?mode=ro',uri=True)) as db:
        sources={r[0] for r in db.execute('SELECT DISTINCT source_id FROM chunks')}
    import importlib.util
    spec=importlib.util.spec_from_file_location('audit_notes',root/'scripts/study-notes.py');notes=importlib.util.module_from_spec(spec);spec.loader.exec_module(notes)
    original_root=notes.ROOT;notes.ROOT=root
    try:current={key:(sid,text) for key,sid,_,_,_,text in notes.windows(None)}
    finally:notes.ROOT=original_root
    findings=[];count=0
    with closing(sqlite3.connect((directory/'notes.build.sqlite').resolve().as_uri()+'?mode=ro',uri=True)) as db:
        integrity=db.execute('PRAGMA quick_check').fetchone()[0]
        for rowid,key,sid,locator,quote,context in db.execute('SELECT rowid,key,source_id,locator,quote,context FROM notes'):
            count+=1;reasons=[]
            if sid not in sources:reasons.append('source outside current index')
            if not key.startswith('skill-'):
                window=current.get(key)
                if window is None:reasons.append('window outside current queue; retain historical record')
                elif window[0]!=sid or ' '.join(quote.split()).casefold() not in ' '.join(window[1].split()).casefold():reasons.append('quote/current passage review')
            if sid not in entries:reasons.append('provenance unknown')
            if section(context) in ('bibliography','mixed bibliography','possible bibliography'):reasons.append('bibliography attribution review')
            if not quote or ' '.join(quote.split()).casefold() not in ' '.join(context.split()).casefold():reasons.append('quote/context review')
            if reasons:findings.append({'rowid':rowid,'window_key':key,'source_id':sid,'locator':locator,'reasons':reasons})
    return {'version':1,'kind':'non-destructive provenance audit','notes_checked':count,'database_quick_check':integrity,
            'suspect_notes':len(findings),'findings':findings,'limits':'Heuristic candidates, not proven errors. No notes deleted or requeued; review originals before excluding or rebuilding. No inferred author names.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','check','audit']);p.add_argument('--output',type=Path,default=ROOT/'data/provenance-audit.json');a=p.parse_args()
    if a.action=='audit':
        value=audit();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in value.items() if k!='findings'}));return
    value,raw=build();path=ROOT/'knowledge/provenance.json'
    if a.action=='check':
        if not path.exists() or path.read_text(encoding='utf8')!=raw:raise SystemExit('Provenance drift; rebuild reviewed metadata before release')
    else:
        temp=path.with_suffix('.tmp');temp.write_text(raw,encoding='utf8');temp.replace(path)
    print(json.dumps({'sources':len(value['entries']),'dated':sum(bool(i.get('published_on')) for i in value['entries'].values()),'sha256':hashlib.sha256(raw.encode()).hexdigest()}))
if __name__=='__main__':main()
