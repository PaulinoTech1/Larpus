"""Owner-injected raw-model timer. Never imported by the gateway or MCP server."""
import json
import time
import urllib.request


def finish(row,frame,started,clock):
    row['total_seconds']=clock()-started
    row['ok']=frame.get('done') is True and bool(row['answer']) and 'error' not in row
    if not row['ok']:row.setdefault('error','empty_answer' if frame.get('done') else 'missing_done')
    for key in ('prompt_eval_count','prompt_eval_duration','eval_count','eval_duration','load_duration'):
        if type(frame.get(key)) is int:row[key]=frame[key]
    duration=row.get('eval_duration',0)
    row['tokens_per_second']=row['eval_count']/(duration/1e9) if duration>0 and 'eval_count' in row else None
    return row


def read_frame(line):
    if len(line)>65536:raise ValueError('Oversized model frame')
    frame=json.loads(line)
    if not isinstance(frame,dict):raise ValueError('Invalid model frame')
    return frame


def measure(response,clock=time.perf_counter,started=None):
    started=clock() if started is None else started
    row={'ok':False,'first_text_seconds':None,'answer':''};frame={}
    try:
        for _ in range(8192):
            line=response.readline(65537)
            if not line:break
            frame=read_frame(line);elapsed=clock()-started
            if frame.get('error'):row['error']='model_error';break
            text=frame.get('message',{}).get('content','')
            if not isinstance(text,str):raise ValueError('Invalid model text')
            if text:
                if row['first_text_seconds'] is None:row['first_text_seconds']=elapsed
                row['answer']+=text
            if len(row['answer'])>65536:raise ValueError('Oversized model output')
            if frame.get('done') is True:break
        else:row['error']='frame_limit'
    except (ValueError,TypeError,AttributeError):row['error']='invalid_stream'
    return finish(row,frame if isinstance(frame,dict) else {},started,clock)


def main():
    import sys
    value=json.load(sys.stdin)
    request=urllib.request.Request('http://127.0.0.1:11434/api/chat',data=json.dumps(value).encode(),headers={'Content-Type':'application/json'})
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    started=time.perf_counter()
    try:
        with opener.open(request,timeout=180) as response:row=measure(response,started=started)
    except (OSError,ValueError):row={'ok':False,'error':'direct_model_transport','first_text_seconds':None,'total_seconds':time.perf_counter()-started,'answer':''}
    print(json.dumps(row,allow_nan=False))


if __name__=='__main__':main()
