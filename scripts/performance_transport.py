"""Fixed local HTTP streaming probes; only completed answers can enter review files."""
import json
import re
import time
import urllib.error
import urllib.request
from scripts.performance_metrics import STAGES,numeric

MAX_LINE=400000


def completed(event,state):
    timing=event.get('timing_ms',{})
    state['stage_ms']={k:v for k,v in timing.items() if k in STAGES and numeric(v)}
    state['sources_count']=len(event.get('sources',[]))
    state['unknown_citations']=len(event.get('citation_check',{}).get('unknown',[]))
    state['ok']=state['characters']>0
    if not state['ok']:state['error']='empty_answer'


def stream(response,state,started,retain):
    chunks=[]
    while True:
        line=response.readline(MAX_LINE+1)
        if not line:state['error']='missing_done';return None
        if len(line)>MAX_LINE:raise ValueError('Oversized event')
        if time.perf_counter()-started>180:raise TimeoutError('Probe deadline')
        event=json.loads(line);kind=event['type']
        if kind=='error':
            state['error']='stream_rejected'
            if re.fullmatch('[a-f0-9]{16}',str(event.get('error_id',''))):state['error_id']=event['error_id']
            return None
        if kind=='text':record_text(event,state,started,chunks,retain)
        elif kind=='done':
            completed(event,state)
            return {'answer':''.join(chunks),'sources':event.get('sources',[])} if retain and state['ok'] else None
        else:raise ValueError('Unknown event')


def record_text(event,state,started,chunks,retain):
    text=event['content']
    if not isinstance(text,str):raise ValueError('Invalid text')
    if not text:return
    if state['first_text_seconds'] is None:state['first_text_seconds']=round(time.perf_counter()-started,3)
    state['characters']+=len(text)
    if state['characters']>65536:raise ValueError('Oversized answer')
    if retain:chunks.append(text)


def probe(opener,case,retain=False):
    request=urllib.request.Request('http://127.0.0.1:8080/api/chat/stream',json.dumps({'persona':case['persona'],'messages':case['messages']}).encode(),{'Content-Type':'application/json'})
    started=time.perf_counter();answer=None
    state={'ok':False,'http_status':None,'headers_seconds':None,'first_text_seconds':None,'characters':0,'stage_ms':{}}
    try:
        with opener.open(request,timeout=180) as response:
            state['http_status']=getattr(response,'status',200);state['headers_seconds']=round(time.perf_counter()-started,3)
            answer=stream(response,state,started,retain)
    except urllib.error.HTTPError as exc:state.update(http_status=exc.code,error='http_rejected')
    except KeyboardInterrupt:state['error']='interrupted'
    except OSError as exc:
        # OSError includes socket timeout, reset and connection refusal.
        state['error']='timeout' if isinstance(exc,TimeoutError) else 'transport_error'
    except (ValueError,KeyError,TypeError,AttributeError):state['error']='invalid_protocol'
    if 'error' in state:state['ok']=False
    state['total_seconds']=round(time.perf_counter()-started,3)
    return state,answer if state['ok'] else None
