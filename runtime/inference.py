"""Server-owned inference service shared only through the local MCP interface."""
from runtime.diagnostics import catalog_failure, report
from runtime.execution_profiles import resolve
from runtime.execution_trace import Trace
import json
import re
import threading
import time
from runtime.agents import ROOT, load_personas, messages_for, require_persona
from runtime.local_ollama import ollama, chat_stream, BrokerRejected
from runtime.text_filter import TextHeld
from runtime.skills import CatalogRejected, summaries
from runtime.dlp import gate, stream_pending
from runtime.knowledge import augment, NOTE_TIER
from runtime.context import CAPACITY,OUTPUT_LIMIT,INPUT_BOUND,COMPRESS_PREFIX,SUMMARY_SYSTEM,ContextPressure,upper_bound,compression_data,compression_envelope,summary_result,encoded,validate_record

PERSONAS=load_personas()
LOCK=threading.Lock()

def active_model(default):
    status=ollama('/api/tags',timeout=5)
    tag=status.get('active_model',default)
    if tag not in ('qwen3.5:27b-q4_K_M','larpus3.8:27b-q4'):raise ValueError('Unapproved selected model')
    return tag

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
    from runtime.agents import persona_rejections
    from runtime.skills import skill_rejections
    try:
        current=load_personas();listed=summaries()
    except CatalogRejected as exc:return catalog_failure(exc)
    return {'personas':[{key:p.get(key,[]) for key in ('id','name','description','model','skills')} for p in current.values()],'skills':listed,
            'rejected':{'personas':persona_rejections(),'skills':skill_rejections()}}

def health():
    try:
        result=ollama('/api/tags',timeout=2)
        models=[m['name'] for m in result['models'] if isinstance(m['name'],str)]
        active=result.get('active_model')
        configured={active} if active else {p['model'] for p in PERSONAS.values()}
        placements={tag:gpu_placement(tag) for tag in sorted(configured)}
        return {'ollama':'online','active_model':active,'switching':result.get('switching',False),'models':models,'model_processors':placements,'voice':'gateway-offline-worker','transport':'local-mcp-stdio'}
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

def checked_content(result):
    content=result['message']['content']
    if not isinstance(content,str) or not content.strip():raise ValueError('Empty model response')
    return content

def chat(persona, messages, skill=None, on_chunk=None, execution=None, *, fixed_selectors=None):
    started=time.perf_counter();timing={}
    try:context=resolve(execution)
    except ValueError:return {'status':400,'error':'Invalid execution context'}
    trace=Trace(context.profile=='diagnostic',time.perf_counter)
    try:
        if len(json.dumps({'persona':persona,'messages':messages}).encode())>524288:
            raise ValueError('Input too large')
        selected=require_persona(persona)
        prepared=messages_for(selected,messages,skill)
        validate_record(messages)
        compression=compression_envelope(messages)
        if fixed_selectors is not None and compression is not None:
            raise ValueError('Fixed evidence cannot be used for compression')
    except TextHeld as exc:
        return {'status':503 if exc.unavailable else 422,'error':'Text held by the local input filter. Remove hidden controls or instruction overrides and try again.','reason':exc.reason,'message_index':exc.index}
    except CatalogRejected as exc:return catalog_failure(exc)
    except (ValueError,TypeError):
        return {'status':400,'error':'Invalid persona or conversation'}
    trace.mark('input')
    timing['input']=round((time.perf_counter()-started)*1000,3)
    retrieval_started=time.perf_counter()
    try:
        if compression is not None:
            prepared[0]['content']=SUMMARY_SYSTEM
            evidence=[]
            if upper_bound(prepared)>INPUT_BOUND:raise ContextPressure('Compression batch exceeds context')
        elif fixed_selectors is not None:
            prepared,evidence=augment(prepared,persona,fixed_selectors=fixed_selectors)
        elif context.profile!='ultra-fast':prepared,evidence=augment(prepared,persona,timings=timing)
        else:prepared,evidence=augment(prepared,persona)
    except ContextPressure:
        return {'status':413,'code':'context_pressure','error':'Conversation needs compression before continuing. Use COMPRESS or shorten the latest message.'}
    except CatalogRejected as exc:return catalog_failure(exc)
    except Exception as exc:
        error_id=report('LARP-EVIDENCE-UNAVAILABLE',exc)
        return {'status':503,'error_id':error_id,'diagnostic_code':'LARP-EVIDENCE-UNAVAILABLE','error':'Approved local evidence was unavailable or rejected during screening. Check the library diagnostic; no internet fallback is used.'}
    trace.mark('retrieval')
    timing['retrieval']=round((time.perf_counter()-retrieval_started)*1000,3)
    if not LOCK.acquire(blocking=False):
        return {'status':409,'error':'Inference busy. Try again shortly.'}
    try:
        selection_started=time.perf_counter()
        selected=dict(selected,model=active_model(selected['model']))
        timing['model_selection']=round((time.perf_counter()-selection_started)*1000,3)
        trace.mark('model_selection')
        def release(text, frame):
            result=trace.screen(gate,text,prepared[0]['content'])
            if result.get('status')==200:
                if compression is not None:
                    try:record=summary_result(result['content'],compression)
                    except (ValueError,TypeError,KeyError,TextHeld):return {'status':422,'error':'Summary failed validation. Original conversation retained; retry compression.'}
                    result=trace.screen(gate,encoded(record),prepared[0]['content'])
                    if result.get('status')!=200:return result
                    result['handoff']=record
                usage=context_usage(frame,max(0,len(messages)+1-len(prepared)))
                if usage is not None:result['context']=usage
                result['citation_check']=citation_check(text,evidence)
                result['sources']=[]
                for source in evidence:
                    derived=source.get('tier')==NOTE_TIER
                    preview=trace.screen(gate,source['original_passage'] if derived else source['text'],prepared[0]['content'])
                    result['sources'].append({**{k:source[k] for k in ('id','title','url','locator')},
                        'snapshot':source.get('snapshot','derived study note') if derived else source['snapshot'],
                        **({'tier':NOTE_TIER} if derived else {}),
                        **({'provenance':{k:v for k,v in source['provenance'].items() if k in ('document_authors','document_authors_status','published_on','revised_on','snapshot_on','retrieved_at','section')}} if 'provenance' in source else {}),
                        'preview':preview['content'] if preview.get('status')==200 else 'Preview withheld by local output screening.'})
                timing['inference_total']=round((time.perf_counter()-started)*1000,3)
                result['timing_ms']=dict(timing)
                result['execution']=execution_receipt(context,selected['model'])
                trace.attach(result)
            return result
        if on_chunk is not None:return stream_reply(selected,prepared,release,on_chunk,timing,started,trace)
        result=ollama('/api/chat',{'model':selected['model'],'messages':prepared,'stream':False,'think':False,'keep_alive':-1,'options':{'temperature':selected['temperature'],'num_ctx':CAPACITY,'num_predict':OUTPUT_LIMIT,'num_gpu':99}},timeout=900)
        if gpu_placement(selected['model'])!='GPU':
            return {'status':503,'error':'Full GPU model placement unavailable. Free GPU memory and retry; CPU fallback replies are disabled.'}
        content=checked_content(result)
        return release(content,result)
    except CatalogRejected as exc:return catalog_failure(exc)
    except BrokerRejected as exc:
        status=429 if exc.status==429 else 503
        code=exc.code if exc.code in ('inference_budget','queue_full','admission_timeout','cancellation_unconfirmed','inference_deadline','model_switching') else 'broker_held'
        return {'status':status,'code':code,'error':'Local inference is busy or held by the broker. Retry shortly; no direct fallback is used.'}
    except (OSError,ValueError,KeyError,TypeError) as exc:
        error_id=report('LARP-INFERENCE-UNAVAILABLE',exc)
        return {'status':502,'error_id':error_id,'diagnostic_code':'LARP-INFERENCE-UNAVAILABLE','error':'Local Ollama unavailable or model missing. No cloud fallback is used.'}
    finally:
        LOCK.release()


def stream_cut(content,released,done,system):
    boundaries=list(re.finditer(r'[.!?]["\x27)\]]*\s+|\n\n',content[released:]))
    cut=len(content) if done else released+boundaries[-1].end() if boundaries else released
    return released if cut<=released or (not done and stream_pending(content,system)) else cut

def execution_receipt(context,model):
    # Sealed deployment is immutable and checked freshly by host preflight.
    # Owner host fixtures have no served-source receipt, so cannot be accepted
    # as secure benchmark evidence.
    deployment=ROOT/'deployment.json'
    pin=None
    if deployment.is_file():
        pin=json.loads(deployment.read_text(encoding='utf-8'))['source_fingerprint']
        if not isinstance(pin,str) or not re.fullmatch('[a-f0-9]{64}',pin):raise ValueError('Invalid sealed source receipt')
    return {'profile':context.profile,'interaction':context.interaction,'base':context.base,'model':model,'source_fingerprint':pin}


def mark_first_text(timing,released,started):
    if not released:timing['first_checked_text']=round((time.perf_counter()-started)*1000,3)


def stream_reply(selected,prepared,release,on_chunk,timing,started,trace=None):
    trace=trace or Trace(False,time.perf_counter)
    content='';released=0;placed=False;final_frame={}
    model_started=time.perf_counter()
    for frame in chat_stream({'model':selected['model'],'messages':prepared,'think':False,'keep_alive':-1,'options':{'temperature':selected['temperature'],'num_ctx':CAPACITY,'num_predict':OUTPUT_LIMIT,'num_gpu':99}},timeout=900):
        timing.setdefault('model_first_frame',round((time.perf_counter()-model_started)*1000,3))
        delta=frame.get('message',{}).get('content','')
        if not isinstance(delta,str):
            raise ValueError('Invalid model content')
        trace.model_text(delta)
        content+=delta
        if len(content.encode())>65536:
            return {'status':422,'error':'Output held by local DLP.'}
        done=frame.get('done') is True
        final_frame=frame
        cut=stream_cut(content,released,done,prepared[0]['content'])
        if cut<=released:
            continue
        if not placed or done:
            if gpu_placement(selected['model'])!='GPU':
                return {'status':503,'error':'Full GPU model placement unavailable. CPU fallback replies are disabled.'}
            placed=True
        # Stage and inspect the ENTIRE generated prefix, including
        # lookahead; never inspect isolated token fragments.
        checked=trace.screen(gate,content,prepared[0]['content'])
        if checked.get('status')!=200:
            return checked
        mark_first_text(timing,released,started)
        trace.approved()
        on_chunk(content[released:cut]);released=cut
    if not content.strip():
        raise ValueError('Empty model response')
    if gpu_placement(selected['model'])!='GPU':
        return {'status':503,'error':'Full GPU model placement unavailable. CPU fallback replies are disabled.'}
    return release(content,final_frame)
