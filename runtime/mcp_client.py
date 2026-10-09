"""Fixed local child process; never accepts a server URL or executable from input."""
import asyncio
import os
import sys
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from runtime.agents import ROOT
from runtime.isolation import mode,child_args

def child_parameters():
    # Do not inherit credentials, proxies, or telemetry exporter configuration.
    env={key:os.environ[key] for key in ('SYSTEMROOT','WINDIR','PATH','TEMP','TMP','HOME','USERPROFILE') if key in os.environ}
    env.update({'PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1','OLLAMA_NO_CLOUD':'1','OTEL_SDK_DISABLED':'true'})
    if mode()=='wsl-podman':
        command=child_args()
        return StdioServerParameters(command=command[0],args=command[1:],cwd=str(ROOT),env=env)
    return StdioServerParameters(command=sys.executable,args=['-m','runtime.mcp_server'],cwd=str(ROOT),env=env)

async def call_async(tool, arguments=None, on_chunk=None):
    if tool not in ('chat_local','list_personas','local_status'):
        raise ValueError('MCP tool is not allowed')
    async with Client(child_parameters(),read_timeout_seconds=130) as client:
        chunks=[]
        async def progress(_progress,_total,message):
            if not isinstance(message,str) or len(message.encode())>65536 or sum(len(s.encode()) for s in chunks)+len(message.encode())>65536:
                raise ValueError('Invalid approved chunk')
            chunks.append(message)
            on_chunk(message)
        result=await client.call_tool(tool,arguments or {},progress_callback=progress if on_chunk else None,meta={'larpus_stream':True} if on_chunk else None)
        if result.is_error or not isinstance(result.structured_content,dict):
            raise OSError('Local MCP operation failed')
        if on_chunk and result.structured_content.get('status')==200 and ''.join(chunks)!=result.structured_content.get('content'):
            raise OSError('Incomplete local MCP stream')
        return result.structured_content

def call(tool, arguments=None):
    try:
        return asyncio.run(asyncio.wait_for(call_async(tool,arguments),timeout=140))
    except Exception as exc:
        raise OSError('Local MCP unavailable; no direct inference fallback') from exc

def chat(persona,messages,skill=None):
    return call('chat_local',{'persona':persona,'messages':messages,'skill':skill})

def stream_chat(persona,messages,skill,on_chunk):
    try:
        return asyncio.run(asyncio.wait_for(call_async('chat_local',{'persona':persona,'messages':messages,'skill':skill},on_chunk),timeout=140))
    except Exception as exc:
        raise OSError('Local MCP stream unavailable') from exc

def health():
    return call('local_status')
