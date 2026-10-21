"""Owner-local fixed chat probes; save timings, never prompts or generated text."""
import argparse
import json
import math
import statistics
import time
import urllib.request

PROFILES={
    'greeting':('home-assistant','Say hello in one short sentence.'),
    'learning':('home-assistant','Explain what a norm measures and how it relates to stability. Use two short sentences.'),
    'cyber':('it-larp-coach','Explain how a SOC should validate AI alert triage with human oversight. Use two short sentences.'),
}

def stage_timings(event):
    allowed=('input','retrieval','model_selection','model_first_frame','first_checked_text','inference_total','preflight','mcp_connect','mcp_total','preflight_initial_reads','preflight_namespace_reads','preflight_validation','retrieval_base','retrieval_notes','retrieval_provenance','retrieval_engine','mcp_child_import')
    return {k:v for k,v in event.get('timing_ms',{}).items() if k in allowed and type(v) in (int,float) and math.isfinite(v) and v>=0}


def probe(opener,persona,question):
    body=json.dumps({'persona':persona,'messages':[{'role':'user','content':question}]}).encode()
    request=urllib.request.Request('http://127.0.0.1:8080/api/chat/stream',body,{'Content-Type':'application/json'})
    started=time.perf_counter();first=None;characters=0;complete=False;timing={}
    with opener.open(request,timeout=180) as response:
        headers=time.perf_counter()-started
        for line in response:
            if len(line)>400000:raise ValueError('Oversized chat event')
            event=json.loads(line)
            if event['type']=='error':raise RuntimeError('Chat probe rejected')
            if event['type']=='text':
                if first is None:first=time.perf_counter()-started
                characters+=len(event['content'])
            elif event['type']=='done':
                complete=True
                timing=stage_timings(event)
    if not complete or first is None:raise RuntimeError('Incomplete chat probe')
    return {'headers_seconds':round(headers,3),'first_checked_text_seconds':round(first,3),
            'total_seconds':round(time.perf_counter()-started,3),'characters':characters,'stage_ms':timing}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats',type=int,choices=range(1,6),default=3)
    parser.add_argument('--profile',choices=PROFILES,default='greeting')
    args=parser.parse_args()
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    results=[]
    for repeat in range(args.repeats):
        result=probe(opener,*PROFILES[args.profile])
        results.append(result)
        print(json.dumps({'probe':repeat+1,**result}),flush=True)
    print(json.dumps({'median_first_checked_text_seconds':round(statistics.median(r['first_checked_text_seconds'] for r in results),3),
                      'profile':args.profile,'scope':'Fresh fixed conversations through local HTTP, MCP, retrieval, model and output screening; excludes browser rendering and speech.'}))


if __name__=='__main__':main()
