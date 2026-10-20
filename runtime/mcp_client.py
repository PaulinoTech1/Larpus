"""Fixed local child process; never accepts a server URL or executable from input."""
import asyncio
import json
import os
import re
import sys
import time
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from runtime.agents import ROOT
from runtime.diagnostics import failure
from runtime.isolation import mode,child_args
from runtime.dlp import CI_OVERRIDES
from runtime.execution_profiles import resolve, to_wire

def child_parameters(execution=None,timings=None):
    context=resolve(execution)
    if execution is not None and mode()!='wsl-podman':raise ValueError('Explicit production profiles require sealed isolation')
    # Do not inherit credentials, proxies, or telemetry exporter configuration.
    env={key:os.environ[key] for key in ('SYSTEMROOT','WINDIR','PATH','TEMP','TMP','HOME','USERPROFILE') if key in os.environ}
    env.update({'PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1','OLLAMA_NO_CLOUD':'1','OTEL_SDK_DISABLED':'true'})
    # Bounded CI-only DLP settings; runtime.dlp ignores them outside GitHub Actions.
    env.update({key:os.environ[key] for key in CI_OVERRIDES if key in os.environ})
    if mode()=='wsl-podman':
        if timings is not None:command=child_args(fast=context.base=='ultra-fast',timings=timings)
        else:command=child_args(fast=True) if context.base=='ultra-fast' else child_args()
        return StdioServerParameters(command=command[0],args=command[1:],cwd=str(ROOT),env=env)
    env['LARPUS_ISOLATION']='host'
    return StdioServerParameters(command=sys.executable,args=['-m','runtime.mcp_server'],cwd=str(ROOT),env=env)

async def call_async(tool, arguments=None, on_chunk=None, execution=None):
    if tool not in ('chat_local','list_personas','local_status'):
        raise ValueError('MCP tool is not allowed')
    metadata=request_metadata(tool,on_chunk,execution)
    started=time.perf_counter()
    parameters,details=profile_parameters(execution)
    preflight_ms=round((time.perf_counter()-started)*1000,3)
    connect_started=time.perf_counter()
    async with Client(parameters,read_timeout_seconds=930) as client:
        connect_ms=round((time.perf_counter()-connect_started)*1000,3)
        chunks=[]
        async def progress(_progress,_total,message):
            if not isinstance(message,str) or len(message.encode())>65536 or sum(len(s.encode()) for s in chunks)+len(message.encode())>65536:
                raise ValueError('Invalid approved chunk')
            chunks.append(message)
            on_chunk(message)
        result=await client.call_tool(tool,arguments or {},progress_callback=progress if on_chunk else None,meta=metadata)
        if result.is_error or not isinstance(result.structured_content,dict):
            raise OSError('Local MCP operation failed')
        if on_chunk and result.structured_content.get('status')==200 and ''.join(chunks)!=result.structured_content.get('content'):
            raise OSError('Incomplete local MCP stream')
        value=result.structured_content
        if tool=='chat_local' and value.get('status')==200:
            attach_source_receipt(value)
            value['timing_ms']={**value.get('timing_ms',{}),**details,'preflight':preflight_ms,'mcp_connect':connect_ms,'mcp_total':round((time.perf_counter()-started)*1000,3)}
        return value

def profile_parameters(execution):
    details={}
    if resolve(execution).profile=='diagnostic':return child_parameters(execution,timings=details),details
    return (child_parameters(execution) if execution is not None else child_parameters()),details

def call(tool, arguments=None, execution=None):
    try:
        return asyncio.run(asyncio.wait_for(call_async(tool,arguments,execution=execution),timeout=940))
    except Exception as exc:
        raise failure('LARP-MCP-UNAVAILABLE',exc,'Local MCP unavailable; no direct inference fallback') from exc

def chat(persona,messages,skill=None,execution=None):
    return call('chat_local',{'persona':persona,'messages':messages,'skill':skill},execution=execution)

def stream_chat(persona,messages,skill,on_chunk,execution=None):
    try:
        return asyncio.run(asyncio.wait_for(call_async('chat_local',{'persona':persona,'messages':messages,'skill':skill},on_chunk,execution=execution),timeout=940))
    except Exception as exc:
        raise failure('LARP-MCP-STREAM',exc,'Local MCP stream unavailable') from exc

def health():
    return call('local_status')

async def surface_async():
    async with Client(child_parameters(),read_timeout_seconds=10) as client:
        tools=await client.list_tools()
        return {'protocol_version':client.protocol_version,
                'capabilities':client.server_capabilities.model_dump(mode='json',by_alias=True,exclude_none=True),
                'tools':sorted([t.model_dump(mode='json',exclude_none=True) for t in tools.tools],key=lambda t:t['name'])}

def surface():
    return asyncio.run(asyncio.wait_for(surface_async(),timeout=20))

def request_metadata(tool,on_chunk,execution):
    context=to_wire(resolve(execution))
    metadata={'larpus_stream':True} if on_chunk else {}
    if tool=='chat_local':metadata['larpus_execution']=context
    return metadata

def attach_source_receipt(value):
    # The host preflight binds these frozen sources to the inspected agent image.
    # deployment.json cannot be baked into that image: it contains its image ID.
    receipt=value.get('execution');deployment=ROOT/'deployment.json'
    if not isinstance(receipt,dict) or not deployment.is_file():return
    pin=json.loads(deployment.read_text(encoding='utf-8'))['source_fingerprint']
    if not isinstance(pin,str) or not re.fullmatch('[a-f0-9]{64}',pin):raise ValueError('Invalid sealed source receipt')
    receipt['source_fingerprint']=pin
