"""Server-owned inference service shared only through the local MCP interface."""
import json
import re
import threading
from runtime.agents import load_personas, messages_for
from runtime.local_ollama import ollama, chat_stream
from runtime.text_filter import TextHeld
from runtime.skills import summaries
from runtime.dlp import gate, stream_pending
from runtime.knowledge import augment
from runtime.context import CAPACITY,OUTPUT_LIMIT,INPUT_BOUND,COMPRESS_PREFIX,SUMMARY_SYSTEM,ContextPressure,upper_bound,compression_data,compression_envelope,summary_result,encoded,validate_record

PERSONAS=load_personas()
LOCK=threading.Lock()

def gpu_placement(tag):
    """Require Ollama's full GPU residency report, not host RAM/usage guesses."""
    loaded=next((m for m in ollama('/api/ps',timeout=5)['models'] if m.get('name')==tag),None)
    if loaded is None:
        return 'unloaded'
    size=loaded.get('size');vram=loaded.get('size_vram')
    if type(size) is not int or type(vram) is not int or size<=0 or vram<0:
        raise ValueError('Invalid GPU placement report')
    return 'GPU' if vram>=size else 'CPU/GPU' if vram else 'CPU'

def personas():
    return {'personas':[{key:p.get(key,[]) for key in ('id','name','description','model','skills')} for p in PERSONAS.values()],'skills':summaries()}

def health():
    try:
        result=ollama('/api/tags',timeout=2)
        models=[m['name'] for m in result['models'] if isinstance(m['name'],str)]
        placements={tag:gpu_placement(tag) for tag in sorted({p['model'] for p in PERSONAS.values()})}
        return {'ollama':'online','models':models,'model_processors':placements,'voice':'gateway-offline-worker','transport':'local-mcp-stdio'}
    except (OSError,ValueError,KeyError,TypeError):
        return {'ollama':'offline','models':[],'voice':'gateway-offline-worker','transport':'local-mcp-stdio'}

def context_usage(frame, omitted=0):
    # Ollama reports actual tokenization after generation. Return counts only;
    # instruction and evidence text never belong in these diagnostics.
    prompt=frame.get('prompt_eval_count');output=frame.get('eval_count')
    if type(prompt) is not int or type(output) is not int or not 0<=prompt<=CAPACITY or not 0<=output<=CAPACITY:
        return None
    return {'capacity':CAPACITY,'prompt_tokens':prompt,'output_tokens':output,
            'output_limit':OUTPUT_LIMIT,'omitted_messages':omitted,'measurement':'ollama-final'}

def citation_check(content,evidence):
    selected={s['id'] for s in evidence}
    identifiers=set(re.findall(r'\[([a-z][a-z0-9-]{2,80})\]',content))
    unknown=sorted(identifiers-selected)
    return {'status':'unknown-identifiers' if unknown else 'identified' if identifiers else 'no-citations',
            'cited':sorted(identifiers & selected),'unknown':unknown,'selected':len(selected)}

def chat(persona, messages, skill=None, on_chunk=None):
    try:
        if len(json.dumps({'persona':persona,'messages':messages}).encode())>524288:
            raise ValueError('Input too large')
        selected=PERSONAS.get(persona) if isinstance(persona,str) else None
        if selected is None:
            raise ValueError('Unknown persona')
        prepared=messages_for(selected,messages,skill)
        validate_record(messages)
        compression=compression_envelope(messages)
    except TextHeld as exc:
        return {'status':503 if exc.unavailable else 422,'error':'Text held by the local input filter. Remove hidden controls or instruction overrides and try again.','reason':exc.reason,'message_index':exc.index}
    except (ValueError,TypeError):
        return {'status':400,'error':'Invalid persona or conversation'}
    try:
        if compression is not None:
            prepared[0]['content']=SUMMARY_SYSTEM
            evidence=[]
            if upper_bound(prepared)>INPUT_BOUND:raise ContextPressure('Compression batch exceeds context')
        else:prepared,evidence=augment(prepared,persona)
    except ContextPressure:
        return {'status':413,'code':'context_pressure','error':'Conversation needs compression before continuing. Use COMPRESS or shorten the latest message.'}
    except Exception:
        return {'status':503,'error':'Approved local evidence unavailable, rejected or exceeds the context budget. Shorten the question or check the library; no internet fallback is used.'}
    if not LOCK.acquire(blocking=False):
        return {'status':409,'error':'Inference busy. Try again shortly.'}
    try:
        def release(text, frame):
            result=gate(text,prepared[0]['content'])
            if result.get('status')==200:
                if compression is not None:
                    try:record=summary_result(result['content'],compression)
                    except (ValueError,TypeError,KeyError,TextHeld):return {'status':422,'error':'Summary failed validation. Original conversation retained; retry compression.'}
                    result=gate(encoded(record),prepared[0]['content'])
                    if result.get('status')!=200:return result
                    result['handoff']=record
                usage=context_usage(frame,max(0,len(messages)+1-len(prepared)))
                if usage is not None:result['context']=usage
                result['citation_check']=citation_check(text,evidence)
                result['sources']=[]
                for source in evidence:
                    preview=gate(source['text'],prepared[0]['content'])
                    result['sources'].append({**{k:source[k] for k in ('id','title','url','snapshot','locator')},
                        'preview':preview['content'] if preview.get('status')==200 else 'Preview withheld by local output screening.'})
            return result
        if on_chunk is not None:
            content='';released=0;placed=False;final_frame={}
            for frame in chat_stream({'model':selected['model'],'messages':prepared,'think':False,'keep_alive':-1,'options':{'temperature':selected['temperature'],'num_ctx':CAPACITY,'num_predict':OUTPUT_LIMIT,'num_gpu':99}},timeout=900):
                delta=frame.get('message',{}).get('content','')
                if not isinstance(delta,str):
                    raise ValueError('Invalid model content')
                content+=delta
                if len(content.encode())>65536:
                    return {'status':422,'error':'Output held by local DLP.'}
                done=frame.get('done') is True
                if done:final_frame=frame
                boundaries=list(re.finditer(r'[.!?]["\x27)\]]*\s+|\n\n',content[released:]))
                cut=len(content) if done else released+boundaries[-1].end() if boundaries else released
                if cut<=released or (not done and stream_pending(content,prepared[0]['content'])):
                    continue
                if not placed or done:
                    if gpu_placement(selected['model'])!='GPU':
                        return {'status':503,'error':'Full GPU model placement unavailable. CPU fallback replies are disabled.'}
                    placed=True
                # Stage and inspect the ENTIRE generated prefix, including
                # lookahead; never inspect isolated token fragments.
                checked=gate(content,prepared[0]['content'])
                if checked.get('status')!=200:
                    return checked
                on_chunk(content[released:cut]);released=cut
            if not content.strip():
                raise ValueError('Empty model response')
            if gpu_placement(selected['model'])!='GPU':
                return {'status':503,'error':'Full GPU model placement unavailable. CPU fallback replies are disabled.'}
            return release(content,final_frame)
        result=ollama('/api/chat',{'model':selected['model'],'messages':prepared,'stream':False,'think':False,'keep_alive':-1,'options':{'temperature':selected['temperature'],'num_ctx':CAPACITY,'num_predict':OUTPUT_LIMIT,'num_gpu':99}},timeout=900)
        if gpu_placement(selected['model'])!='GPU':
            return {'status':503,'error':'Full GPU model placement unavailable. Free GPU memory and retry; CPU fallback replies are disabled.'}
        content=result['message']['content']
        if not isinstance(content,str) or not content.strip():
            raise ValueError('Empty model response')
        return release(content,result)
    except (OSError,ValueError,KeyError,TypeError):
        return {'status':502,'error':'Local Ollama unavailable or model missing. No cloud fallback is used.'}
    finally:
        LOCK.release()
