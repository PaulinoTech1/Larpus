"""Read-only MCP Skills extension over the reviewed local registry."""
import base64
import hashlib
import json
from typing import Literal
from mcp.server.extension import Extension, MethodBinding
from mcp.server.mcpserver import Context
from mcp.shared.exceptions import MCPError
from mcp.types import RequestParams, PaginatedRequestParams, CacheableResult, PaginatedResult
from runtime.skill_resources import verified_catalog, resolve_skill, skill_entry


class GetSkillParams(RequestParams):
    uri: str

class ListSkillsResult(PaginatedResult, CacheableResult):
    result_type: Literal['complete']='complete'
    skills: list[dict]

class GetSkillResult(CacheableResult):
    result_type: Literal['complete']='complete'
    skill: dict

def _entries(catalog):
    return [skill_entry(catalog[key]) for key in sorted(catalog)]

def list_skill_page(catalog,cursor):
    entries=_entries(catalog)
    digest=hashlib.sha256(json.dumps(entries,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    offset=_offset(cursor,digest,len(entries)) if cursor is not None else 0
    end=offset+16
    return entries[offset:end],_cursor(digest,end) if end<len(entries) else None

def _offset(cursor,digest,length):
    try:
        if not isinstance(cursor,str) or not 1<=len(cursor)<=256:
            raise ValueError('Invalid cursor')
        decoded=base64.b64decode(cursor+'='*((-len(cursor))%4),altchars=b'-_',validate=True)
        token=json.loads(decoded)
        offset=token['offset']
        valid=(set(token)=={'version','digest','offset'} and token['version']==1 and token['digest']==digest)
        if not valid or type(offset) is not int or offset<=0 or offset%16 or offset>=length:
            raise ValueError('Invalid cursor')
        if _cursor(digest,offset)!=cursor:
            raise ValueError('Noncanonical cursor')
        return offset
    except (ValueError,TypeError,KeyError,UnicodeError) as exc:
        raise ValueError('Invalid skill cursor') from exc

def _cursor(digest,offset):
    raw=json.dumps({'version':1,'digest':digest,'offset':offset},sort_keys=True,separators=(',',':')).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')

def _catalog():
    try:
        return verified_catalog()
    except Exception as exc:
        raise MCPError(-32603,'Local skill verification failed') from exc

async def _list(ctx,params):
    catalog=_catalog()
    try:
        entries,cursor=list_skill_page(catalog,params.cursor)
    except ValueError as exc:
        raise MCPError(-32602,'Invalid skill cursor') from exc
    return ListSkillsResult(skills=entries,next_cursor=cursor,ttl_ms=0,cache_scope='private')

async def _get(ctx,params):
    catalog=_catalog()
    try:
        entry=skill_entry(resolve_skill(params.uri,catalog))
    except ValueError as exc:
        raise MCPError(-32602,'Unknown local skill resource') from exc
    return GetSkillResult(skill=entry,ttl_ms=0,cache_scope='private')

class LocalSkillsExtension(Extension):
    identifier='io.modelcontextprotocol/skills'

    def methods(self):
        versions=frozenset({'2026-07-28'})
        return (MethodBinding('skills/list',PaginatedRequestParams,_list,versions),
                MethodBinding('skills/get',GetSkillParams,_get,versions))

def register_skill_resource(server):
    @server.resource('skill://{identifier}/SKILL.md',mime_type='text/markdown')
    def read_skill(identifier: str, ctx: Context) -> str:
        catalog=_catalog()
        try:
            uri=ctx.request_context.params.get('uri')
            return resolve_skill(uri,catalog).raw.decode('utf-8')
        except ValueError as exc:
            raise MCPError(-32602,'Unknown local skill resource') from exc
