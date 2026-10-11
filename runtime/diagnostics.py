"""Bounded owner diagnostics: no exception messages, locals, requests or secrets."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import sys
import threading
import uuid

LOCK=threading.Lock()
RECOVERY={
 'LARP-MCP-UNAVAILABLE':'Inspect owner gateway stderr and frozen release/source/OCI pins; no direct model fallback.',
 'LARP-MCP-STREAM':'Inspect matching error ID; retain transcript, mark partial reply incomplete, retry only after boundary checks.',
 'LARP-VOICE-UNAVAILABLE':'Check pinned CPU voice service and protocol; text remains usable, no cloud fallback.',
 'LARP-NOTES-TRANSPORT':'Check worker stderr, process exit and active notes container; current window remains pending.',
 'LARP-NOTES-WORKER':'Inspect cause chain and notes-only broker status; do not save partial JSON.',
 'LARP-EVIDENCE-UNAVAILABLE':'Check approved-index, manifest/provenance binding and text screening; do not infer without evidence.',
 'LARP-INFERENCE-UNAVAILABLE':'Check selected broker readiness and pinned model; no direct or cloud fallback.'
}
CODES={'LARP-MCP-UNAVAILABLE','LARP-MCP-STREAM','LARP-VOICE-UNAVAILABLE',
       'LARP-NOTES-TRANSPORT','LARP-NOTES-WORKER','LARP-EVIDENCE-UNAVAILABLE',
       'LARP-INFERENCE-UNAVAILABLE'}

def safe_name(value):
    return value if isinstance(value,str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.<>-]{0,100}',value) else 'unknown'

def report(code,exc):
    if code not in CODES:raise ValueError('Unknown diagnostic code')
    identifier=uuid.uuid4().hex[:16];causes=[];seen=set();current=exc
    while isinstance(current,BaseException) and id(current) not in seen and len(causes)<8:
        seen.add(id(current));frames=[];tb=current.__traceback__
        while tb is not None:
            frames.append({'file':safe_name(Path(tb.tb_frame.f_code.co_filename).name),
                           'line':tb.tb_lineno,'function':safe_name(tb.tb_frame.f_code.co_name)})
            tb=tb.tb_next
        item={'type':safe_name(type(current).__name__),'frames':frames[-16:]}
        for name in ('errno','winerror','returncode'):
            value=getattr(current,name,None)
            if type(value) is int:item[name]=value
        if isinstance(current,DiagnosticError):item['related_error_id']=current.error_id
        causes.append(item)
        current=current.__cause__ or (None if current.__suppress_context__ else current.__context__)
    record={'schema':'larpus.diagnostic/v1','time':datetime.now(timezone.utc).isoformat(),
            'severity':'ERROR','code':code,'next_step':RECOVERY[code],'error_id':identifier,'pid':os.getpid(),'causes':causes,
            'omitted':'Exception messages, absolute paths, source lines, locals, stdin/stdout, prompts and credentials intentionally omitted.'}
    # stderr is captured by the owner gateway/notes logs; never the MCP/notes stdout protocol.
    try:
        with LOCK:sys.stderr.write(json.dumps(record,separators=(',',':'))+'\n');sys.stderr.flush()
    except (OSError,ValueError):
        # The failure must still propagate even when its diagnostic sink is broken.
        pass
    return identifier

class DiagnosticError(OSError):
    def __init__(self,code,error_id,message):
        super().__init__(message);self.code=code if code in CODES else 'LARP-NOTES-TRANSPORT'
        self.error_id=error_id if isinstance(error_id,str) and re.fullmatch(r'[a-f0-9]{16}',error_id) else 'unavailable'

def failure(code,exc,message):
    return DiagnosticError(code,report(code,exc),message)
