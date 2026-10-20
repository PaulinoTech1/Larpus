"""Local model evaluation/selection. No automatic downloads or cloud fallback."""
import argparse
import json
import time
from runtime.station_paths import ROOT
from runtime.local_ollama import ollama
from runtime.security_scan import timestamp,write_json

PROBES=(
    'Plan a realistic evening with 45 minutes for chores and 30 minutes for reading.',
    'Ask one systems-administration interview question about diagnosing a DNS incident.',
    'Create three scene hooks for a fictional clockmaker in a floating city.',
)

def benchmark(tag):
    config=json.loads((ROOT/'config/models.json').read_text(encoding='utf-8'))
    if tag not in {m['tag'] for m in config['candidates']}:
        raise ValueError('Use a configured local candidate')
    models=ollama('/api/tags',timeout=2)['models']
    installed=next((m for m in models if m.get('name')==tag),None)
    if installed is None:
        raise ValueError('Candidate not installed; prepare it separately with Ollama')
    results=[]
    for prompt in PROBES:
        start=time.monotonic()
        response=ollama('/api/chat',{'model':tag,'messages':[{'role':'user','content':prompt}],'stream':False,'keep_alive':0,'think':False,'options':{'num_ctx':4096,'num_predict':256,'temperature':0.3}},timeout=120)
        count=response.get('eval_count',0);duration=response.get('eval_duration',0)
        content=response.get('message',{}).get('content')
        results.append({'elapsed_seconds':round(time.monotonic()-start,3),'output_tokens':count,'tokens_per_second':round(count/(duration/1e9),2) if duration else None,'nonempty_response':isinstance(content,str) and bool(content.strip())})
    report={'generated_at':timestamp(),'model':tag,'digest':installed.get('digest'),'probes':results,'context':4096,'output_cap':256,'quality_review':'NOT_RUN','vram_fit':'NOT_MEASURED','note':'Cold-load latency probes, not model quality or prompt-injection resistance evidence'}
    write_json(ROOT/'data/models/latest-benchmark.json',report)
    return report

def select(tag):
    config=json.loads((ROOT/'config/models.json').read_text(encoding='utf-8'))
    if tag not in {m['tag'] for m in config['candidates']}:
        raise ValueError('Unknown local candidate')
    if tag not in {m['name'] for m in ollama('/api/tags',timeout=2)['models']}:
        raise ValueError('Model is not installed locally')
    for path in (ROOT/'agents/personas').glob('*.json'):
        persona=json.loads(path.read_text(encoding='utf-8'))
        persona['model']=tag
        write_json(path,persona)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('operation',choices=('benchmark','select'))
    parser.add_argument('model')
    args=parser.parse_args()
    try:
        if args.operation=='benchmark':
            print(json.dumps(benchmark(args.model),indent=2))
        else:
            select(args.model)
            print('Local personas updated. Restart the gateway; health scan evidence will refresh.')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise SystemExit('Local model operation failed: '+str(exc))

if __name__=='__main__':
    main()
