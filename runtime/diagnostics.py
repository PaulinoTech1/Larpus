"""Bounded owner diagnostics with reviewed exact messages; no arbitrary secrets."""
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
 'LARP-MODEL-MAINTENANCE':'Inspect the matching model-operation diagnostic and fixed model identity; recover locally without fallback.',
 'LARP-MCP-UNAVAILABLE':'Inspect owner gateway stderr and frozen release/source/OCI pins; no direct model fallback.',
 'LARP-MCP-STREAM':'Inspect matching error ID; retain transcript, mark partial reply incomplete, retry only after boundary checks.',
 'LARP-VOICE-UNAVAILABLE':'Check pinned CPU voice service and protocol; text remains usable, no cloud fallback.',
 'LARP-NOTES-TRANSPORT':'Check worker stderr, process exit and active notes container; current window remains pending.',
 'LARP-NOTES-WORKER':'Inspect cause chain and notes-only broker status; do not save partial JSON.',
 'LARP-EVIDENCE-UNAVAILABLE':'Check approved-index, manifest/provenance binding and text screening; do not infer without evidence.',
 'LARP-EVIDENCE-NOTE-EXCLUDED':'An optional derived note failed completed screening and was excluded. Original records remain unchanged; inspect the source before rebuilding notes.',
 'LARP-INFERENCE-UNAVAILABLE':'Check selected broker readiness and pinned model; no direct or cloud fallback.',
 'LARP-CATALOG-REJECTED':'Read scope. skill or persona: only that entry stays unavailable. catalog: the registry document failed and no persona is served.',
 'LARP-VOICE-HELD':'Speech text was held by output DLP or hidden-format screening; the reply stays displayed. Inspect the listed reason codes; text is never logged.',
 'LARP-RATE-LIMITED':'A per-client request bucket was exhausted; inspect the bucket name and client pacing before raising limits.'
}
CODES={'LARP-MODEL-MAINTENANCE','LARP-MCP-UNAVAILABLE','LARP-MCP-STREAM','LARP-VOICE-UNAVAILABLE',
       'LARP-NOTES-TRANSPORT','LARP-NOTES-WORKER','LARP-EVIDENCE-UNAVAILABLE',
       'LARP-INFERENCE-UNAVAILABLE','LARP-EVIDENCE-NOTE-EXCLUDED','LARP-CATALOG-REJECTED',
       'LARP-VOICE-HELD','LARP-RATE-LIMITED'}

# Exact, reviewed literals only. Never copy arbitrary exception text into logs.
KNOWN_MESSAGES={
 'Fixed local model operation failed':('MODEL-OPERATION-FAILED','Inspect the numeric subprocess return code and pinned model service.'),
 'Owner selection state unavailable':('MODEL-STATE-UNAVAILABLE','Inspect owner WSL selection state access without editing release pins.'),
 'Model weight identity differs':('MODEL-WEIGHT-MISMATCH','Verify the approved model artifact and catalog hash.'),
 'Full GPU/context verification failed':('MODEL-GPU-CONTEXT-FAILED','Restore the prior selection; inspect GPU allocation and context configuration.'),
 'Warm-up did not complete':('MODEL-WARMUP-INCOMPLETE','Inspect local model service readiness before retrying.'),
 'Warm-up produced no text':('MODEL-WARMUP-EMPTY','Inspect local model warm-up before retrying.'),
 'Compression batch exceeds context':('INFERENCE-COMPRESSION-BATCH-EXCEEDS-CONTEXT', 'Inspect model reply schema and pinned GPU placement; preserve the conversation and reject invalid content.'),
 'Empty model response':('INFERENCE-EMPTY-MODEL-RESPONSE', 'Inspect model reply schema and pinned GPU placement; preserve the conversation and reject invalid content.'),
 'Incomplete local MCP stream':('MCP_CLIENT-INCOMPLETE-LOCAL-MCP-STREAM', 'Inspect the fixed MCP child and its stderr. Verify allowed tool and stream framing; do not bypass MCP.'),
 'Inference broker is required':('LOCAL_OLLAMA-INFERENCE-BROKER-IS-REQUIRED', 'Inspect the pinned broker socket, readiness and framing; never fall back to direct TCP inference.'),
 'Inference redirects are disabled':('LOCAL_OLLAMA-INFERENCE-REDIRECTS-ARE-DISABLED', 'Inspect the pinned broker socket, readiness and framing; never fall back to direct TCP inference.'),
 'Inference route is not allowed':('LOCAL_OLLAMA-INFERENCE-ROUTE-IS-NOT-ALLOWED', 'Inspect the pinned broker socket, readiness and framing; never fall back to direct TCP inference.'),
 'Input too large':('INFERENCE-INPUT-TOO-LARGE', 'Inspect model reply schema and pinned GPU placement; preserve the conversation and reject invalid content.'),
 'Invalid GPU placement report':('INFERENCE-INVALID-GPU-PLACEMENT-REPORT', 'Inspect model reply schema and pinned GPU placement; preserve the conversation and reject invalid content.'),
 'Invalid approved chunk':('MCP_CLIENT-INVALID-APPROVED-CHUNK', 'Inspect the fixed MCP child and its stderr. Verify allowed tool and stream framing; do not bypass MCP.'),
 'Invalid broker readiness':('LOCAL_OLLAMA-INVALID-BROKER-READINESS', 'Inspect the pinned broker socket, readiness and framing; never fall back to direct TCP inference.'),
 'Invalid job':('NOTES_WORKER-INVALID-JOB', 'Keep the window pending. Inspect notes capability, request shape and worker readiness.'),
 'Invalid model content':('INFERENCE-INVALID-MODEL-CONTENT', 'Inspect model reply schema and pinned GPU placement; preserve the conversation and reject invalid content.'),
 'Invalid model stream':('LOCAL_OLLAMA-INVALID-MODEL-STREAM', 'Inspect the pinned broker socket, readiness and framing; never fall back to direct TCP inference.'),
 'Invalid private inference socket':('LOCAL_OLLAMA-INVALID-PRIVATE-INFERENCE-SOCKET', 'Inspect the pinned broker socket, readiness and framing; never fall back to direct TCP inference.'),
 'Invalid voice identity':('VOICE-INVALID-VOICE-IDENTITY', 'Inspect CPU voice deployment pins, worker readiness and protocol. Rebuild only through a scoped voice maintenance plan.'),
 'Invalid voice response':('VOICE-INVALID-VOICE-RESPONSE', 'Inspect CPU voice deployment pins, worker readiness and protocol. Rebuild only through a scoped voice maintenance plan.'),
 'Job too large':('NOTES_WORKER-JOB-TOO-LARGE', 'Keep the window pending. Inspect notes capability, request shape and worker readiness.'),
 'LARP-MCP-STREAM':('MCP_CLIENT-LARP-MCP-STREAM', 'Inspect the fixed MCP child and its stderr. Verify allowed tool and stream framing; do not bypass MCP.'),
 'LARP-MCP-UNAVAILABLE':('MCP_CLIENT-LARP-MCP-UNAVAILABLE', 'Inspect the fixed MCP child and its stderr. Verify allowed tool and stream framing; do not bypass MCP.'),
 'LARP-VOICE-UNAVAILABLE':('VOICE-LARP-VOICE-UNAVAILABLE', 'Inspect CPU voice deployment pins, worker readiness and protocol. Rebuild only through a scoped voice maintenance plan.'),
 'Local MCP operation failed':('MCP_CLIENT-LOCAL-MCP-OPERATION-FAILED', 'Inspect the fixed MCP child and its stderr. Verify allowed tool and stream framing; do not bypass MCP.'),
 'MCP tool is not allowed':('MCP_CLIENT-MCP-TOOL-IS-NOT-ALLOWED', 'Inspect the fixed MCP child and its stderr. Verify allowed tool and stream framing; do not bypass MCP.'),
 'Model response too large':('LOCAL_OLLAMA-MODEL-RESPONSE-TOO-LARGE', 'Inspect the pinned broker socket, readiness and framing; never fall back to direct TCP inference.'),
 'Model stream ended without completion':('LOCAL_OLLAMA-MODEL-STREAM-ENDED-WITHOUT-COMPLETION', 'Inspect the pinned broker socket, readiness and framing; never fall back to direct TCP inference.'),
 'Model stream exceeded limits':('LOCAL_OLLAMA-MODEL-STREAM-EXCEEDED-LIMITS', 'Inspect the pinned broker socket, readiness and framing; never fall back to direct TCP inference.'),
 'Notes DNS/UDP reachable':('NOTES_WORKER-NOTES-DNS-UDP-REACHABLE', 'Keep the window pending. Inspect notes capability, request shape and worker readiness.'),
 'Notes broker unavailable':('NOTES_WORKER-NOTES-BROKER-UNAVAILABLE', 'Keep the window pending. Inspect notes capability, request shape and worker readiness.'),
 'Notes identity/network drift':('NOTES_WORKER-NOTES-IDENTITY-NETWORK-DRIFT', 'Keep the window pending. Inspect notes capability, request shape and worker readiness.'),
 'Notes privilege drift':('NOTES_WORKER-NOTES-PRIVILEGE-DRIFT', 'Keep the window pending. Inspect notes capability, request shape and worker readiness.'),
 'Notes raw network reachable':('NOTES_WORKER-NOTES-RAW-NETWORK-REACHABLE', 'Keep the window pending. Inspect notes capability, request shape and worker readiness.'),
 'Oversized broker status':('LOCAL_OLLAMA-OVERSIZED-BROKER-STATUS', 'Inspect the pinned broker socket, readiness and framing; never fall back to direct TCP inference.'),
 'Too many model frames':('LOCAL_OLLAMA-TOO-MANY-MODEL-FRAMES', 'Inspect the pinned broker socket, readiness and framing; never fall back to direct TCP inference.'),
 'Unexpected notes capability':('NOTES_WORKER-UNEXPECTED-NOTES-CAPABILITY', 'Keep the window pending. Inspect notes capability, request shape and worker readiness.'),
 'Unexpected voice mounts':('VOICE-UNEXPECTED-VOICE-MOUNTS', 'Inspect CPU voice deployment pins, worker readiness and protocol. Rebuild only through a scoped voice maintenance plan.'),
 'Unknown inference capability':('LOCAL_OLLAMA-UNKNOWN-INFERENCE-CAPABILITY', 'Inspect the pinned broker socket, readiness and framing; never fall back to direct TCP inference.'),
 'Unknown persona':('INFERENCE-UNKNOWN-PERSONA', 'Inspect model reply schema and pinned GPU placement; preserve the conversation and reject invalid content.'),
 'Voice boundary violated':('VOICE-VOICE-BOUNDARY-VIOLATED', 'Inspect CPU voice deployment pins, worker readiness and protocol. Rebuild only through a scoped voice maintenance plan.'),
 'Voice host devices prohibited':('VOICE-VOICE-HOST-DEVICES-PROHIBITED', 'Inspect CPU voice deployment pins, worker readiness and protocol. Rebuild only through a scoped voice maintenance plan.'),
 'Voice identity/resource limits missing':('VOICE-VOICE-IDENTITY-RESOURCE-LIMITS-MISSING', 'Inspect CPU voice deployment pins, worker readiness and protocol. Rebuild only through a scoped voice maintenance plan.'),
 'Voice image drift or stopped worker':('VOICE-VOICE-IMAGE-DRIFT-OR-STOPPED-WORKER', 'Inspect CPU voice deployment pins, worker readiness and protocol. Rebuild only through a scoped voice maintenance plan.'),
 'Voice privileges violated':('VOICE-VOICE-PRIVILEGES-VIOLATED', 'Inspect CPU voice deployment pins, worker readiness and protocol. Rebuild only through a scoped voice maintenance plan.'),
 'Voice response too large':('VOICE-VOICE-RESPONSE-TOO-LARGE', 'Inspect CPU voice deployment pins, worker readiness and protocol. Rebuild only through a scoped voice maintenance plan.'),
 'Speech held by output screening':('VOICE-SPEECH-HELD', 'Review the DLP/hidden-format reason codes; the displayed reply is unchanged and no speech text is logged.'),
 'Voice request rate limited':('RATE-VOICE-BUCKET-EXHAUSTED', 'Check HUD speech pacing; the voice bucket is separate from chat and other API requests.'),
 'API request rate limited':('RATE-API-BUCKET-EXHAUSTED', 'Check client request pacing; chat and other API requests share this bucket.'),
 'Voice worker busy':('VOICE-VOICE-WORKER-BUSY', 'Inspect CPU voice deployment pins, worker readiness and protocol. Rebuild only through a scoped voice maintenance plan.'),
 'Voice worker source changed; rebuild voice image':('VOICE-VOICE-WORKER-SOURCE-CHANGED--REBUILD-VOICE-IMAGE', 'Inspect CPU voice deployment pins, worker readiness and protocol. Rebuild only through a scoped voice maintenance plan.'),
}
_CATALOG_ACTION='Read scope. A named skill or persona stays unavailable. A registry-document failure serves no persona. Do not load a rejected skill prompt.'
for _catalog_message in (
 'Duplicate persona','Invalid local skill description scalar','Invalid local skill frontmatter',
 'Invalid local skill frontmatter fields','Invalid local skill registry','Invalid local skill selection',
 'Invalid or duplicate skill ID','Invalid persona field','Invalid persona fields','Invalid persona identity',
 'Invalid skill metadata','Invalid skill registration','Invalid temperature','Invalid voice',
 'Local skill input exceeds size limit','Local skill input must be a regular file','No personas configured',
 'Only local model identifiers allowed','Only locally authored skills are allowed','Skill changed; local review and registration required',
 'Skill path escapes local registry','Skills must be prompt-only; ancillary executables are not allowed',
 'Too many local skills','Unregistered local skill folder'):
    KNOWN_MESSAGES[_catalog_message]=('CATALOG-REJECTED',_CATALOG_ACTION)
_EVIDENCE_ACTION='Check the approved index, manifest, or notes binding named by the message. Do not infer without that evidence.'
for _evidence_message in (
 'Invalid knowledge database','Invalid knowledge manifest','Invalid notes database','Invalid notes manifest',
 'Knowledge database hash mismatch','Knowledge size changed','Notes database hash mismatch'):
    KNOWN_MESSAGES[_evidence_message]=('EVIDENCE-REJECTED',_EVIDENCE_ACTION)

_SCOPE_ERRORS={
 'catalog':'Local catalog rejected. No persona is served until the registry file is reviewed.',
 'persona':'This persona was rejected. Other personas stay available.',
 'skill':'This skill was rejected. Other personas and skills stay available.'}

def catalog_failure(exc):
    """Public catalog refusal. The exception text stays in the reviewed owner record."""
    scope=getattr(exc,'scope','catalog')
    if scope not in _SCOPE_ERRORS:scope='catalog'
    return {'status':503,'error_id':report('LARP-CATALOG-REJECTED',exc),'diagnostic_code':'LARP-CATALOG-REJECTED','scope':scope,
            'error':_SCOPE_ERRORS[scope]}

def safe_name(value):
    return value if isinstance(value,str) and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.<>-]{0,100}',value) else 'unknown'

def describe(exc):
    """Exact known messages; otherwise classify without serializing args or buffers."""
    args=exc.args
    message=args[0] if len(args)==1 and type(args[0]) is str else None
    if message in KNOWN_MESSAGES:
        reason,action=KNOWN_MESSAGES[message]
        return {'reason':reason,'message':message,'action':action,'message_source':'reviewed-literal'}
    if isinstance(exc,json.JSONDecodeError):
        return {'reason':'INVALID-JSON','message':'Response or configuration contains invalid JSON.',
                'json_line':exc.lineno,'json_column':exc.colno,
                'action':'Check producer framing/configuration at these coordinates; document contents withheld.'}
    if isinstance(exc,(TimeoutError,)) or type(exc).__name__=='TimeoutExpired':
        return {'reason':'TIMEOUT','message':'The local operation exceeded its deadline.',
                'action':'Check worker readiness, admission and resource contention before retrying.'}
    if isinstance(exc,PermissionError):
        return {'reason':'PERMISSION-DENIED','message':'The operating system denied access.',
                'action':'Inspect owner-side permissions; do not weaken sandbox boundaries to retry.'}
    if isinstance(exc,ConnectionError):
        return {'reason':'CONNECTION-FAILED','message':'The local transport failed.',
                'action':'Check the pinned service and socket readiness; do not use an external fallback.'}
    return {'reason':'UNCLASSIFIED','message':'No reviewed exact message is available; inspect type, frames and numeric error codes.',
            'action':'Reproduce locally and add a reviewed fixed message at the failing boundary.'}

def reason_field(reasons):
    """At most eight sanitized reason-code names; never free text."""
    return {'reasons':sorted({safe_name(r) for r in reasons})[:8]} if reasons else {}

def report(code,exc,reasons=()):
    """Write one bounded record; optional reasons are fixed code names, never text."""
    if code not in CODES:raise ValueError('Unknown diagnostic code')
    identifier=uuid.uuid4().hex[:16];causes=[];seen=set();current=exc
    while isinstance(current,BaseException) and id(current) not in seen and len(causes)<8:
        seen.add(id(current));frames=[];tb=current.__traceback__
        while tb is not None:
            frames.append({'file':safe_name(Path(tb.tb_frame.f_code.co_filename).name),
                           'line':tb.tb_lineno,'function':safe_name(tb.tb_frame.f_code.co_name)})
            tb=tb.tb_next
        item={'type':safe_name(type(current).__name__),'frames':frames[-16:],**describe(current)}
        for name in ('errno','winerror','returncode'):
            value=getattr(current,name,None)
            if type(value) is int:item[name]=value
        if isinstance(current,DiagnosticError):item['related_error_id']=current.error_id
        causes.append(item)
        current=current.__cause__ or (None if current.__suppress_context__ else current.__context__)
    record={'schema':'larpus.diagnostic/v1','time':datetime.now(timezone.utc).isoformat(),
            'severity':'ERROR','code':code,'next_step':RECOVERY[code],'error_id':identifier,'pid':os.getpid(),'causes':causes,
            **reason_field(reasons),
            'omitted':'Unreviewed exception messages, absolute paths, source lines, locals, stdin/stdout, prompts and credentials intentionally omitted.'}
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
