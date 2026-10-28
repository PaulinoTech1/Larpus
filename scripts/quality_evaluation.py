"""Offline evidence-bound review accounting. Citation IDs are not claim entailment."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
BOUND=('case_id','case_sha256','response_sha256','evidence_sha256')

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def load_cases(path=None):
    value=json.loads((Path(path) if path else ROOT/'evals/quality-support.json').read_text(encoding='utf-8'))
    if type(value.get('version')) is not int or value['version']!=1:raise ValueError('Unknown quality schema')
    return validate_cases(value['cases'])

def validate_cases(cases):
    if not isinstance(cases,list) or not 1<=len(cases)<=200:raise ValueError('Invalid quality catalogue')
    ids=set();families={}
    for case in cases:
        _case(case)
        if case['id'] in ids:raise ValueError('Duplicate quality case')
        ids.add(case['id']);families.setdefault(case['family'],set()).add(case['split'])
    if any(len(splits)!=1 for splits in families.values()):raise ValueError('Family split leakage')
    return cases

def _case(case):
    if not isinstance(case,dict) or set(case)!={'id','family','split','messages','sources','rubric'}:raise ValueError('Invalid case fields')
    if case['split'] not in {'development','held-out'}:raise ValueError('Invalid split')
    for name in ('id','family'):
        if not isinstance(case[name],str) or not re.fullmatch('[a-z0-9-]{1,80}',case[name]):raise ValueError('Invalid case identity')
    _messages(case['messages'])
    if not isinstance(case['rubric'],list) or not case['rubric']:raise ValueError('Missing support rubric')
    _sources(case['sources'])

def _messages(messages):
    if not isinstance(messages,list) or not 3<=len(messages)<=15 or len(messages)%2!=1:raise ValueError('Invalid history')
    for i,message in enumerate(messages):
        if set(message)!={'role','content'} or message['role']!=('user' if i%2==0 else 'assistant'):raise ValueError('Invalid turn')
        if not isinstance(message['content'],str) or not 1<=len(message['content'])<=8000:raise ValueError('Invalid message')

def _sources(sources):
    if not isinstance(sources,list) or not 1<=len(sources)<=30:raise ValueError('Invalid source inventory')
    ids=[]
    for source in sources:
        if not isinstance(source,dict) or not isinstance(source.get('id'),str):raise ValueError('Missing source identity')
        ids.append(source['id'])
    if len(set(ids))!=len(ids) or len(json.dumps(sources).encode())>400000:raise ValueError('Invalid source receipt')
    return ids

def attempt(case,result):
    _case(case)
    content=result.get('content','');sources=result.get('sources',[])
    if not isinstance(content,str) or len(content.encode())>65536:raise ValueError('Invalid answer size')
    if sources:_sources(sources)
    complete=type(result.get('status')) is int and result['status']==200 and bool(content.strip())
    return {'case_id':case['id'],'family':case['family'],'split':case['split'],'case_sha256':digest(case),
            'response_sha256':digest(content),'evidence_sha256':digest(sources),
            'evidence_ids':[s['id'] for s in sources],'complete':complete}

def _review(review,attempts):
    if not isinstance(review,dict) or set(review)!=set(BOUND)|{'reviewer_kind','claims'}:raise ValueError('Invalid review fields')
    row=attempts.get(review['case_id'])
    if row is None or not row['complete'] or any(review[k]!=row[k] for k in BOUND):raise ValueError('Stale or incomplete review binding')
    if review['reviewer_kind'] not in {'human','agent'}:raise ValueError('Unknown reviewer kind')
    claims=review['claims']
    if not isinstance(claims,list) or not 1<=len(claims)<=100:raise ValueError('Missing claim review')
    ids=set()
    for claim in claims:
        _claim(claim,row)
        if claim['id'] in ids:raise ValueError('Duplicate claim review')
        ids.add(claim['id'])

def _claim(claim,row):
    if not isinstance(claim,dict) or set(claim)!={'id','verdict','evidence_ids'}:raise ValueError('Invalid claim fields')
    if not isinstance(claim['id'],str) or not re.fullmatch('[a-z0-9-]{1,80}',claim['id']):raise ValueError('Invalid claim identity')
    if claim['verdict'] not in {'supported','unsupported','uncertain'}:raise ValueError('Invalid support verdict')
    if not isinstance(claim['evidence_ids'],list) or not set(claim['evidence_ids']).issubset(row['evidence_ids']):
        raise ValueError('Unknown reviewed evidence')
    if claim['verdict']=='supported' and not claim['evidence_ids']:raise ValueError('Support requires evidence')

def summarize(attempts,reviews):
    indexed={row['case_id']:row for row in attempts}
    if len(indexed)!=len(attempts):raise ValueError('Duplicate attempt identity')
    seen=set();groups={'human':[],'agent':[]};uncertain=0
    for review in reviews:
        _review(review,indexed);key=(review['reviewer_kind'],review['case_id'])
        if key in seen:raise ValueError('Duplicate answer review')
        seen.add(key);groups[key[0]].extend(c['verdict'] for c in review['claims'])
        uncertain+=sum(c['verdict']=='uncertain' for c in review['claims'])
    return _summary(attempts,seen,groups,uncertain)

def _summary(attempts,seen,groups,uncertain):
    counts={kind:len([key for key in seen if key[0]==kind]) for kind in groups}
    ratios={kind:(values.count('supported')/len(values) if values else None) for kind,values in groups.items()}
    return {'attempts':len(attempts),'completed':sum(row['complete'] for row in attempts),
            'human_reviewed_answers':counts['human'],'agent_reviewed_answers':counts['agent'],
            'human_claim_support':ratios['human'],'agent_claim_support':ratios['agent'],
            'uncertain_claims':uncertain,'human_review_complete':bool(attempts) and counts['human']==len(attempts),
            'promotion_eligible':False,'reason':'Review accounting alone does not establish quality parity or promotion'}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true',required=True)
    parser.parse_args(argv);cases=load_cases()
    print(json.dumps({'cases':len(cases),'catalogue_sha256':digest(cases),'human_claim_support':None,'scope':'fixtures validated; no answers generated or reviewed'}))
    return 0

if __name__=='__main__':raise SystemExit(main())
