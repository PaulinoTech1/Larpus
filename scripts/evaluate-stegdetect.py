"""Offline labeled-corpus accounting; no model, network or sample text in reports."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from runtime import text_filter as gate
import stegdetect

def load(path):
    raw=path.read_bytes()
    if len(raw)>4*1024*1024:raise ValueError('Corpus exceeds 4 MiB')
    corpus=json.loads(raw);ids=set();validate_catalog(corpus)
    for case in corpus['cases']:
        validate_case(case,ids,corpus['families'])
    return corpus,hashlib.sha256(raw).hexdigest()

def validate_catalog(corpus):
    import re
    if not isinstance(corpus,dict) or corpus.get('version')!=1:raise ValueError('Invalid corpus version')
    cases=corpus.get('cases');families=corpus.get('families')
    if not isinstance(cases,list) or not 1<=len(cases)<=5000:raise ValueError('Expected 1-5000 cases')
    if not isinstance(families,list) or not 1<=len(families)<=64:raise ValueError('Expected 1-64 families')
    if any(not isinstance(f,str) or not re.fullmatch('[a-z0-9_-]{1,64}',f) for f in families):raise ValueError('Invalid opaque family name')
    if len(set(families))!=len(families):raise ValueError('Duplicate family')
    validate_metadata(corpus)

def validate_metadata(corpus):
    if corpus.get('evidence') not in ('authored-synthetic','independently-labeled','unspecified'):raise ValueError('Invalid evidence category')
    if corpus.get('label_review') not in ('not independently reviewed','independently human reviewed','unknown'):raise ValueError('Invalid label-review category')

def validate_case(case,ids,families):
    import re
    for key in ('id','family'):
        if not isinstance(case.get(key),str) or not re.fullmatch('[a-z0-9_-]{1,64}',case[key]):raise ValueError('Invalid opaque case identity')
    if case['id'] in ids or case['family'] not in families:raise ValueError('Duplicate ID or unknown family')
    if not isinstance(case.get('text'),str) or len(case['text'])>16000:raise ValueError('Invalid sample size/type')
    if any(type(case.get(k)) is not bool for k in ('carrier','hold')):raise ValueError('Labels must be booleans')
    ids.add(case['id'])

def observe(text):
    try:
        scan=gate.inspect_text(text,policy=gate.Policy.CONTEXTUAL,limits=gate.LIMITS)
        carrier=(scan.action!='allow' or scan.candidate_text!=text) if scan.status=='complete' and scan.scan_complete else None
    except Exception:carrier=None
    try:gate.inspect_message(text);held=False;reason='allow'
    except gate.TextHeld as exc:
        held=None if exc.unavailable or exc.scan_complete is False else True
        reason=exc.reason
    except Exception:held=None;reason='unexpected_error'
    return carrier,held,reason

def metrics(rows,layer):
    counts=Counter({'TP':0,'FP':0,'TN':0,'FN':0,'inconclusive':0})
    for row in rows:
        expected=row['carrier_label' if layer=='stegdetect' else 'hold_label'];actual=row[layer]
        key='inconclusive' if actual is None else ('T' if actual==expected else 'F')+('P' if actual else 'N')
        counts[key]+=1
    tp,fp,tn,fn=(counts[k] for k in ('TP','FP','TN','FN'))
    ratio=lambda n,d:n/d if d else None
    return {**counts,'total':len(rows),'conclusive':tp+fp+tn+fn,
            'detection_rate':ratio(tp,tp+fn),'false_negative_rate':ratio(fn,tp+fn),
            'false_positive_rate':ratio(fp,fp+tn),'precision':ratio(tp,tp+fp),
            'positive_denominator':tp+fn,'negative_denominator':fp+tn}

def evaluate(corpus,digest):
    rows=[]
    for case in corpus['cases']:
        carrier,held,reason=observe(case['text'])
        rows.append({'id':case['id'],'family':case['family'],'carrier_label':case['carrier'],
                     'hold_label':case['hold'],'stegdetect':carrier,'larpus_gate':held,'gate_reason':reason})
    groups={family:[r for r in rows if r['family']==family] for family in corpus['families']}
    stats={layer:metrics(rows,layer) for layer in ('stegdetect','larpus_gate')}
    coverage={f:{layer:metrics(items,layer) for layer in stats} for f,items in groups.items()}
    package=Path(stegdetect.__file__).parent
    fingerprints={p.relative_to(package).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(package.rglob('*.py'))}
    return {'schema':'larpus.steg-eval/v1','run_id':uuid.uuid4().hex,'time':datetime.now(timezone.utc).isoformat(),
            'evidence':corpus.get('evidence','unspecified'),'label_review':corpus.get('label_review','unknown'),
            'production_claim_supported':False,'dataset_sha256':digest,'stegdetect_version':importlib.metadata.version('stegdetect'),
            'scanner_source_hashes':fingerprints,'gate_sha256':hashlib.sha256(Path(gate.__file__).read_bytes()).hexdigest(),
            'metrics':stats,'coverage':coverage,'untested_families':[f for f,v in groups.items() if not v],
            'rows':rows,'limits':vars(gate.LIMITS) if hasattr(gate.LIMITS,'__dict__') else repr(gate.LIMITS),
            'gaps':['Authored labels need independent human review','Synthetic corpus is not representative traffic',
                    'Carrier presence is not proof of malicious intent','No model-level attack-success measurement',
                    'Incomplete/error scans excluded from classification rates; fail-closed holds are not detections',
                    'No decoding, image/audio scanning or production sampling performed']}

def summary(report):
    lines=['# Stegdetect evaluation','','Evidence: '+report['evidence']+'. Independent review: '+report['label_review']+'. No production-rate claim.','',
           '| Layer | TP | FP | TN | FN | Inconclusive | Detection rate | FPR | FNR |','| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for layer,m in report['metrics'].items():
        cells=[str(m[k]) for k in ('TP','FP','TN','FN','inconclusive')]+['unknown' if m[k] is None else f'{m[k]:.1%}' for k in ('detection_rate','false_positive_rate','false_negative_rate')]
        lines.append('| '+layer+' | '+' | '.join(cells)+' |')
    lines+=['','Untested families: '+', '.join(report['untested_families'])+'.','','Per-family denominators and mismatch IDs are recorded in the JSON report. Samples are never included.','']
    lines += ['- '+gap for gap in report['gaps']]
    return '\n'.join(lines)+'\n'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--corpus',type=Path,default=ROOT/'evals/stegdetect.json');args=parser.parse_args()
    corpus,digest=load(args.corpus);report=evaluate(corpus,digest)
    folder=ROOT/'data/evals/stegdetect';folder.mkdir(parents=True,exist_ok=True)
    (folder/(report['run_id']+'.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    (folder/'latest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    (folder/'latest.md').write_text(summary(report),encoding='utf8')
    with (folder/'history.jsonl').open('a',encoding='utf8') as log:
        log.write(json.dumps({k:report[k] for k in ('run_id','time','dataset_sha256','gate_sha256','stegdetect_version','metrics')})+'\n')
    print(summary(report));return 0

if __name__=='__main__':raise SystemExit(main())
