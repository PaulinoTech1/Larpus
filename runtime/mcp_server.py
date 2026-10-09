"""Local stdio MCP: no HTTP listener, remote tools, sampling, or shell access."""
import threading
import asyncio
import time
from typing import Any
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from runtime import inference

server=MCPServer('larpus-local',version='0.1.0',log_level='CRITICAL',
    instructions='Local-only Larpus inference. No web, filesystem, or shell tools are available.')
RATE_LOCK=threading.Lock()
WINDOW_START=0.0
CALLS=0

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
    if meta is None or meta.get('larpus_stream') is not True:
        return await asyncio.to_thread(inference.chat,persona,messages,skill)
    loop=asyncio.get_running_loop();cancelled=threading.Event();count=0
    def approved(text):
        nonlocal count
        if cancelled.is_set():
            raise OSError('Local stream cancelled')
        count+=len(text)
        future=asyncio.run_coroutine_threadsafe(ctx.report_progress(count,message=text),loop)
        future.result(timeout=10)
    try:
        return await asyncio.to_thread(inference.chat,persona,messages,skill,approved)
    finally:
        cancelled.set()

def main():
    server.run(transport='stdio')

if __name__=='__main__':
    main()
