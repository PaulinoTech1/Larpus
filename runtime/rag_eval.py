"""Owner-only A/B capability probe inside the sealed agent; no MCP registration."""
import json
import sys
import time

from runtime.agents import messages_for, require_persona
from runtime.inference import chat
from runtime.knowledge import augment

MAX_REQUEST=65536
MAX_REPLY=200000


def evaluate(request):
    if type(request) is not dict or set(request)!={'task','persona','messages','fixed_selectors'}:
        raise ValueError('Invalid evaluation request')
    task=request['task']
    if task not in ('A','B') or type(request['persona']) is not str:
        raise ValueError('Invalid evaluation task')
    persona=require_persona(request['persona'])
    messages=request['messages']
    prepared=messages_for(persona,messages)  # Same input validation and filtering as chat.
    selectors=request['fixed_selectors']
    if task=='A':
        if selectors is not None:raise ValueError('Retrieval task cannot select evidence')
        started=time.perf_counter()
        _,passages=augment(prepared,persona['id'])
        elapsed=round(time.perf_counter()-started,3)
        return {'status':200,'seconds':elapsed,'passages':[
            {'id':p['id'],'locator':p['locator']} for p in passages]}
    if selectors is None:raise ValueError('Generation task requires explicit fixed evidence')
    # chat() reselects exact approved passages before making any model request.
    started=time.perf_counter()
    result=chat(persona['id'],messages,fixed_selectors=selectors)
    elapsed=round(time.perf_counter()-started,3)
    if result.get('status')!=200:
        return {'status':result.get('status'),'seconds':elapsed,'error':result.get('code') or result.get('diagnostic_code') or result.get('error','held')}
    return {'status':200,'seconds':elapsed,'answer':result['content'],
            'sources':[{'id':s['id'],'locator':s['locator'],'preview':s['preview']} for s in result['sources']],
            'context':result.get('context')}


def main():
    raw=sys.stdin.buffer.read(MAX_REQUEST+1)
    if len(raw)>MAX_REQUEST:raise ValueError('Oversized evaluation request')
    response=json.dumps(evaluate(json.loads(raw)),ensure_ascii=False).encode()
    if len(response)>MAX_REPLY:raise ValueError('Oversized evaluation response')
    sys.stdout.buffer.write(response)


if __name__=='__main__':main()
