"""Owner-run offline response evaluation; mechanical checks never certify expertise."""
import argparse,json,re,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime.agents import load_personas
from runtime.mcp_client import chat
ROOT=Path(__file__).resolve().parents[1]

def catalog():
    cases=json.loads((ROOT/'evals/companion.json').read_text(encoding='utf-8'))['cases'];personas=load_personas();ids=set()
    for case in cases:
        assert case['id'] not in ids and case['persona'] in personas and case['rubric'];ids.add(case['id'])
        assert case['skill'] is None or case['skill'] in personas[case['persona']]['skills']
    assert {c['persona'] for c in cases}==set(personas)
    return cases

def run(live=False,limit=None):
    cases=catalog();report={'version':1,'mode':'live-local-model' if live else 'catalog-contract','cases':[],'manual_review':'required; keyword and identifier checks are not factual scoring'}
    for case in cases[:limit]:
        row={'id':case['id'],'persona':case['persona'],'rubric':case['rubric']}
        if live:
            start=time.monotonic();result=chat(case['persona'],[{'role':'user','content':case['prompt']}],case['skill'])
            content=result.get('content','');row.update(status=result.get('status'),seconds=round(time.monotonic()-start,2),response=content,sources=result.get('sources',[]),citation_check=result.get('citation_check'),checks={'response_released':result.get('status')==200,'nonempty':bool(content.strip()),'under_120_words':len(content.split())<=120,'no_claimed_live_action':not bool(re.search(r"I (?:have )?(?:installed|deployed|changed your|accessed your tenant)",content,re.I))},manual_scores=None)
            print(case['id']+': '+str(row['status']),flush=True)
        report['cases'].append(row)
    path=ROOT/'data/evals'/('companion-live.json' if live else 'companion-contract.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'mode':report['mode'],'cases':len(report['cases']),'manual_review':report['manual_review']}))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--limit',type=int);args=parser.parse_args()
    if args.limit is not None and not 1<=args.limit<=len(catalog()):parser.error('limit must be within the catalog case count')
    run(args.live,args.limit)
