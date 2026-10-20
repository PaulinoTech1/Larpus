"""Local stdio MCP: no HTTP listener, remote tools, sampling, or shell access."""
import time
IMPORT_STARTED=time.perf_counter()
import threading
import asyncio
from typing import Any
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from runtime import inference
from runtime.execution_profiles import resolve, to_wire
from runtime.mcp_skills import LocalSkillsExtension, register_skill_resource

server=MCPServer('larpus-local',version='0.1.0',log_level='CRITICAL',extensions=[LocalSkillsExtension()],
    instructions='Local-only Larpus inference. No web, filesystem, or shell tools are available.')
register_skill_resource(server)
RATE_LOCK=threading.Lock()
WINDOW_START=0.0
CALLS=0
IMPORT_MS=round(max(0.,min(90.,time.perf_counter()-IMPORT_STARTED))*1000,3)

def startup_timing(result,execution):
    if execution['profile']=='diagnostic' and result.get('status')==200:
        result['timing_ms']={**result.get('timing_ms',{}),'mcp_child_import':IMPORT_MS}
    return result

def allowed():
    global WINDOW_START,CALLS
    with RATE_LOCK:
        now=time.monotonic()
        if now-WINDOW_START>=60:
            WINDOW_START,CALLS=now,0
        if CALLS>=30:
            return False
        CALLS+=1
        return True

@server.tool(structured_output=True)
def list_personas() -> dict[str, Any]:
    """List configured local personas and their installed-model targets."""
    return inference.personas()

@server.tool(structured_output=True)
def local_status() -> dict[str, Any]:
    """Check only the fixed host-loopback Ollama model service."""
    if not allowed():
        return {'status':429,'error':'Local MCP rate limit reached'}
    return inference.health()

@server.tool(structured_output=True)
async def chat_local(persona: str, messages: list[dict], skill: str | None = None, ctx: Context = None) -> dict[str, Any]:
    """Send bounded, filtered conversation to a server-configured local model."""
    if not allowed():
        return {'status':429,'error':'Local MCP rate limit reached'}
    meta=ctx.request_context.meta if ctx else None
    try:execution=to_wire(resolve(meta.get('larpus_execution') if meta else None))
    except (ValueError,TypeError,AttributeError):return {'status':400,'error':'Invalid execution context'}
    if meta is None or meta.get('larpus_stream') is not True:
        return startup_timing(await asyncio.to_thread(inference.chat,persona,messages,skill,execution=execution),execution)
    loop=asyncio.get_running_loop();cancelled=threading.Event();count=0
    def approved(text):
        nonlocal count
        if cancelled.is_set():
            raise OSError('Local stream cancelled')
        count+=len(text)
        future=asyncio.run_coroutine_threadsafe(ctx.report_progress(count,message=text),loop)
        future.result(timeout=10)
    try:
        return startup_timing(await asyncio.to_thread(inference.chat,persona,messages,skill,approved,execution=execution),execution)
    finally:
        cancelled.set()

def main():
    server.run(transport='stdio')

if __name__=='__main__':
    main()
