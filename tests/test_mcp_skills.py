import importlib
import unittest
import json
import subprocess
import threading
import sys
from pathlib import Path
from pydantic import TypeAdapter
from runtime.skill_resources import VerifiedSkill, verified_catalog, resolve_skill
from runtime.mcp_skills import GetSkillParams
from mcp.shared.exceptions import MCPError


class MCPScaffoldingTests(unittest.TestCase):
    def test_pages_complete_and_bound_to_catalog(self):
        api=importlib.import_module('runtime.mcp_skills')
        catalog={f'skill-{i:02}':VerifiedSkill(f'skill-{i:02}',b'body',{'name':f'skill-{i:02}','description':'Test'}) for i in range(35)}
        first,cursor=api.list_skill_page(catalog,None)
        self.assertEqual(len(first),16)
        second,last=api.list_skill_page(catalog,cursor)
        third,end=api.list_skill_page(catalog,last)
        self.assertEqual(len(second),16);self.assertEqual(len(third),3);self.assertIsNone(end)
        self.assertEqual(len({x['uri'] for x in first+second+third}),35)
        for bad in ('', 'garbage', cursor+'x', 'x'*257):
            with self.subTest(bad=bad),self.assertRaises(ValueError):api.list_skill_page(catalog,bad)
        catalog.pop('skill-00')
        with self.assertRaises(ValueError):api.list_skill_page(catalog,cursor)

    def test_extension_registration_is_lazy_and_versioned(self):
        api=importlib.import_module('runtime.mcp_skills')
        from unittest.mock import patch
        from mcp.server import MCPServer
        with patch.object(api,'verified_catalog',side_effect=AssertionError('Eager loading')):
            extension=api.LocalSkillsExtension()
            server=MCPServer('test',extensions=[extension])
            api.register_skill_resource(server)
        self.assertEqual(extension.identifier,'io.modelcontextprotocol/skills')
        self.assertEqual({x.method for x in extension.methods()},{'skills/list','skills/get'})
        self.assertTrue(all(x.protocol_versions==frozenset({'2026-07-28'}) for x in extension.methods()))
        self.assertEqual(extension.tools(),())


class MCPWireTests(unittest.IsolatedAsyncioTestCase):
    async def test_mutation_reverified_and_errors_sanitized(self):
        import tempfile
        from unittest.mock import patch
        from mcp import Client
        from mcp.server import MCPServer
        from runtime import skills, inference
        from runtime.mcp_skills import LocalSkillsExtension,register_skill_resource
        from tests.test_skill_resources import SkillResourceTests
        import mcp.types as types
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);SkillResourceTests().fixture(root)
            server=MCPServer('fixture',extensions=[LocalSkillsExtension()]);register_skill_resource(server)
            with patch.object(skills,'SKILLS',root),patch.object(skills,'REGISTRY',root/'registry.json'),patch.object(inference,'ollama') as model:
                async with Client(server) as client:
                    await client.session.send_request(types.Request(method='skills/list',params={}),TypeAdapter(dict))
                    (root/'example/SKILL.md').write_bytes(b'changed')
                    listed=await client.session.send_request(types.Request(method='skills/list',params={}),TypeAdapter(dict))
                    self.assertEqual(listed['skills'],[])
                    self.assertIn('example',skills.skill_rejections())
                    for method in ('skills/get','resources/read'):
                        with self.subTest(method=method),self.assertRaises(MCPError) as error:
                            params=GetSkillParams(uri='skill://example/SKILL.md') if method!='skills/list' else types.PaginatedRequestParams()
                            await client.session.send_request(types.Request(method=method,params=params),TypeAdapter(dict))
                        self.assertEqual(error.exception.code,-32602)
                        self.assertNotIn(str(root),str(error.exception))
                model.assert_not_called()

    async def test_existing_server_modern_and_legacy_surface(self):
        from mcp import Client
        from runtime.mcp_client import child_parameters
        from unittest.mock import patch
        with patch.dict('os.environ', {'LARPUS_ISOLATION':'host'}):
            server=child_parameters()
        import mcp.types as types
        async with Client(server) as client:
            self.assertEqual(client.protocol_version,'2026-07-28')
            caps=client.server_capabilities.model_dump(by_alias=True)
            self.assertIn('io.modelcontextprotocol/skills',caps.get('extensions',{}))
            tools=await client.list_tools()
            approved=json.loads((Path(__file__).resolve().parents[1]/'config/mcp-approved.json').read_text())['tools']
            self.assertEqual(sorted([t.model_dump(mode='json',exclude_none=True) for t in tools.tools],key=lambda t:t['name']),approved)
            result=await client.session.send_request(types.Request(method='skills/list',params={}),TypeAdapter(dict))
            self.assertEqual(result['resultType'],'complete')
            self.assertEqual(result['ttlMs'],0);self.assertEqual(result['cacheScope'],'private')
            self.assertEqual(len(result['skills']),16)
            entries=list(result['skills']);page=result
            while page.get('nextCursor'):
                page=await client.session.send_request(types.Request(method='skills/list',params=types.PaginatedRequestParams(cursor=page['nextCursor'])),TypeAdapter(dict))
                entries.extend(page['skills'])
            self.assertEqual(len(entries),69)
            self.assertEqual(len({e['uri'] for e in entries}),69)
            uri=result['skills'][0]['uri']
            single=await client.session.send_request(types.Request(method='skills/get',params=GetSkillParams(uri=uri)),TypeAdapter(dict))
            self.assertEqual(single['skill'],result['skills'][0])
            content=await client.read_resource(uri)
            self.assertEqual(content.contents[0].text.encode(),resolve_skill(uri,verified_catalog()).raw)
        async with Client(server,mode='legacy') as client:
            self.assertEqual(client.protocol_version,'2025-11-25')
            self.assertEqual(len((await client.list_tools()).tools),3)
            from mcp.shared.exceptions import MCPError
            with self.assertRaises(MCPError) as error:
                await client.session.send_request(types.Request(method='skills/list',params={}),TypeAdapter(dict))
            self.assertEqual(error.exception.code,-32601)


class RawEnvelopeTests(unittest.TestCase):
    def request(self,method,params):
        request={'jsonrpc':'2.0','id':1,'method':method,'params':params}
        from runtime.mcp_client import child_parameters
        from unittest.mock import patch
        with patch.dict('os.environ',{'LARPUS_ISOLATION':'host'}):
            env=child_parameters().env
        process=subprocess.Popen([sys.executable,'-m','runtime.mcp_server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,env=env)
        timer=threading.Timer(20,process.kill);timer.start()
        try:
            process.stdin.write(json.dumps(request)+'\n');process.stdin.flush()
            return json.loads(process.stdout.readline())
        finally:
            timer.cancel();process.kill();process.wait(timeout=5)
            process.stdin.close();process.stdout.close()

    def test_metadata_errors_and_sanitized_unknown_resources(self):
        meta={'io.modelcontextprotocol/protocolVersion':'2026-07-28','io.modelcontextprotocol/clientCapabilities':{}}
        for bad in ({},{'_meta':{}},{'_meta':{'io.modelcontextprotocol/protocolVersion':42}}):
            with self.subTest(bad=bad):
                self.assertEqual(self.request('skills/list',bad)['error']['code'],-32602)
        for uri in ('skill://unknown/SKILL.md','skill://%68ome-planning/SKILL.md','skill://home%2Dplanning/SKILL.md','skill://home-planning/%53KILL.md','skill://home-planning/SKILL.md?x=1','skill://../SKILL.md','https://example/SKILL.md'):
            for method in ('skills/get','resources/read'):
                with self.subTest(uri=uri,method=method):
                    reply=self.request(method,{'_meta':meta,'uri':uri})
                    self.assertEqual(reply['error']['code'],-32602)
                    self.assertNotIn(str(Path.cwd()),json.dumps(reply))
        unsupported=dict(meta,**{'io.modelcontextprotocol/protocolVersion':'2026-12-31'})
        self.assertEqual(self.request('skills/list',{'_meta':unsupported})['error']['code'],-32022)
        canonical=self.request('resources/read',{'_meta':meta,'uri':'skill://home-planning/SKILL.md'})['result']
        self.assertEqual(canonical['resultType'],'complete');self.assertEqual(canonical['ttlMs'],0)
        self.assertEqual(canonical['cacheScope'],'private')
        self.assertEqual(canonical['contents'][0]['text'].encode(),verified_catalog()['home-planning'].raw)
        reply=self.request('skills/list',{'_meta':meta})['result']
        self.assertEqual(reply['resultType'],'complete')
        self.assertEqual(reply['ttlMs'],0);self.assertEqual(reply['cacheScope'],'private')
        reply=self.request('skills/list',{'_meta':meta,'cursor':'invalid'})
        self.assertEqual(reply['error']['code'],-32602)
