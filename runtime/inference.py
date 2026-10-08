"""Server-owned inference service shared only through the local MCP interface."""
import json
import threading
from runtime.agents import load_personas, messages_for
from runtime.local_ollama import ollama
from runtime.text_filter import TextHeld
from runtime.skills import summaries
from runtime.dlp import gate

PERSONAS=load_personas()
LOCK=threading.Lock()

def personas():
    return {'personas':[{key:p.get(key,[]) for key in ('id','name','description','model','skills')} for p in PERSONAS.values()],'skills':summaries()}

def health():
    try:
        result=ollama('/api/tags',timeout=2)
        models=[m['name'] for m in result['models'] if isinstance(m['name'],str)]
        return {'ollama':'online','models':models,'voice':'stub','transport':'local-mcp-stdio'}
    except (OSError,ValueError,KeyError,TypeError):
        return {'ollama':'offline','models':[],'voice':'stub','transport':'local-mcp-stdio'}

def chat(persona, messages, skill=None):
    try:
        if len(json.dumps({'persona':persona,'messages':messages}).encode())>65536:
            raise ValueError('Input too large')
        selected=PERSONAS.get(persona) if isinstance(persona,str) else None
        if selected is None:
            raise ValueError('Unknown persona')
        prepared=messages_for(selected,messages,skill)
    except TextHeld as exc:
        return {'status':503 if exc.unavailable else 422,'error':'Text held by the local input filter. Remove hidden controls or instruction overrides and try again.','reason':exc.reason,'message_index':exc.index}
    except (ValueError,TypeError):
        return {'status':400,'error':'Invalid persona or conversation'}
    if not LOCK.acquire(blocking=False):
        return {'status':409,'error':'Inference busy. Try again shortly.'}
    try:
        result=ollama('/api/chat',{'model':selected['model'],'messages':prepared,'stream':False,'options':{'temperature':selected['temperature'],'num_ctx':4096,'num_predict':1024}})
        content=result['message']['content']
        if not isinstance(content,str) or not content.strip():
            raise ValueError('Empty model response')
        return gate(content,prepared[0]['content'])
    except (OSError,ValueError,KeyError,TypeError):
        return {'status':502,'error':'Local Ollama unavailable or model missing. No cloud fallback is used.'}
    finally:
        LOCK.release()
