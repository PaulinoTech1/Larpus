"""Reviewed source identity and chronology; cited names never establish authorship."""
import hashlib
import json
from pathlib import Path
import re
from datetime import date
from runtime.freshness import assess

REFERENCE_HEADING=re.compile(r'(?im:(?:^|\n)\s*(?:references|bibliography|works cited)\s*(?:\n|$))|\b(?:REFERENCES|Bibliography|Works Cited)\b|\bReferences\b(?=\s+(?:\[?\d{1,3}[.\]]|[A-Z][a-z]+,))')
CITATIONS=re.compile(r'\[\d{1,3}\]|\bet al\.|\bdoi:|arXiv:\d|\bpp\.\s*\d')

def date_value(value):
    if value in (None,''):return None
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}(?:-\d{2}(?:-\d{2})?)?',value):raise ValueError('Invalid publication date')
    date.fromisoformat(value+('-01-01' if len(value)==4 else '-01' if len(value)==7 else ''))
    return value

def chronology(item):
    value=item.get('revised_on') or item.get('published_on')
    return (value is None,value or '9999',item.get('id',''))

def locator_order(locator):
    return tuple((0,int(x)) if x.isdigit() else (1,x) for x in re.split(r'(\d+)',locator))

def section(text):
    heading=REFERENCE_HEADING.search(text)
    if heading:return 'bibliography' if not text[:heading.start()].strip() else 'mixed bibliography'
    return 'possible bibliography' if len(CITATIONS.findall(text))>=3 else 'body or unknown'

def read(directory):
    directory=Path(directory);path=directory/'provenance.json'
    if not path.exists():return {}  # Legacy release/test fixture.
    if path.is_symlink() or path.stat().st_size>1_000_000:raise ValueError('Invalid provenance file')
    value=json.loads(path.read_text(encoding='utf8'))
    if value.get('version')!=1 or not isinstance(value.get('entries'),dict):raise ValueError('Invalid provenance')
    manifest=directory/'manifest.json'
    if manifest.exists() and value.get('index_sha256')!=json.loads(manifest.read_text(encoding='utf8')).get('database_sha256'):raise ValueError('Provenance/index mismatch')
    for identifier,item in value['entries'].items():
        if item.get('id')!=identifier:raise ValueError('Provenance identity mismatch')
        date_value(item.get('published_on'));date_value(item.get('revised_on'))
    return value['entries']

def evidence(directory,identifier,text):
    item=read(directory).get(identifier)
    result={'section':section(text)}
    if CITATIONS.search(text):result['citation_scope']='Cited works may be discussed here; their authors are distinct and their original findings are not independently verified by this passage.'
    if item:
        result.update({k:v for k,v in item.items() if k not in ('title','id') and v not in (None,[],{})})
    else:result['document_authors_status']='unknown'
    # Keep retrieval metadata compact so freshness does not crowd out passages.
    result['freshness']={'signals':assess(item or {'id':identifier})['signals']}
    return result

def validate_relations(relations,entries):
    if set(relations)!={'version','links'} or relations['version']!=1 or not isinstance(relations['links'],list):raise ValueError('Invalid source relationships')
    graph={};seen=set()
    for link in relations['links']:
        if set(link)!={'new','old','kind','scope','evidence_url','reviewed_on'}:raise ValueError('Invalid relationship fields')
        if link['new'] not in entries or link['old'] not in entries or link['new']==link['old']:raise ValueError('Unknown/self relationship')
        if link['kind'] not in ('supersedes','corrects','conflicts'):raise ValueError('Invalid relationship kind')
        if not isinstance(link['scope'],str) or not 3<=len(link['scope'])<=300 or not isinstance(link['evidence_url'],str) or not link['evidence_url'].startswith('https://'):raise ValueError('Relationship needs scope and evidence')
        date_value(link['reviewed_on'])
        if not link['reviewed_on']:raise ValueError('Relationship needs review date')
        key=(link['new'],link['old'],link['kind'],link['scope'])
        if key in seen:raise ValueError('Duplicate relationship')
        seen.add(key)
        if link['kind']!='conflicts':graph.setdefault(link['new'],[]).append(link['old'])
    def visit(node,path):
        if node in path:raise ValueError('Cyclic supersession/correction')
        for old in graph.get(node,[]):visit(old,path|{node})
    for node in graph:visit(node,set())
    return relations['links']
