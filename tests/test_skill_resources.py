import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from runtime import skills
from runtime.agents import load_personas


class SkillResourceTests(unittest.TestCase):
    def test_reference_peer_rejects_tampered_and_foreign_content(self):
        from tests.skills_verification_peer import verify
        from copy import deepcopy
        api=self.api();item=api.verified_catalog()['home-planning'];entry=api.skill_entry(item)
        self.assertEqual(verify('local','local',entry,item.raw),item.raw)
        with self.assertRaises(ValueError):verify('other-server','local',entry,item.raw)
        with self.assertRaises(ValueError):verify('local','local',entry,item.raw[:-1])
        variants=[]
        for resources in (None,[],entry['resources']*2):
            bad=deepcopy(entry);bad['resources']=resources;variants.append(bad)
        for key,value in (('digest','sha256:'+'0'*64),('size',len(item.raw)+1)):
            bad=deepcopy(entry);bad['resources'][0][key]=value;variants.append(bad)
        bad=deepcopy(entry);bad['frontmatter']['description']='Other';variants.append(bad)
        for bad in variants:
            with self.subTest(entry=bad),self.assertRaises(ValueError):verify('local','local',bad,item.raw)

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('runtime.skill_resources'), 'Verified skill resource layer is missing')
        return importlib.import_module('runtime.skill_resources')

    def fixture(self, root, raw=None):
        folder=root/'example';folder.mkdir()
        raw=raw or b'---\nname: example\ndescription: Test\n---\nHelp plan an evening.\n'
        (folder/'SKILL.md').write_bytes(raw)
        entry={'id':'example','name':'Display title','description':'Display summary','origin':'local-authored','sha256':hashlib.sha256(raw).hexdigest()}
        (root/'registry.json').write_text(json.dumps({'version':1,'skills':[entry]}))
        return entry

    def test_all_69_entries_match_raw_bytes_and_selected_prompts(self):
        api=self.api();catalog=api.verified_catalog()
        self.assertEqual(len(catalog),69)
        for identifier,item in catalog.items():
            raw=(skills.SKILLS/identifier/'SKILL.md').read_bytes();entry=api.skill_entry(item)
            self.assertEqual(item.raw,raw)
            self.assertEqual(entry['frontmatter']['name'],identifier)
            self.assertEqual(entry['resources'],[{'uri':api.skill_uri(identifier),'digest':'sha256:'+hashlib.sha256(raw).hexdigest(),'size':len(raw)}])
        for persona in load_personas().values():
            for identifier in persona['skills']:
                self.assertEqual(skills.selected_prompt(persona,identifier).encode(),b'\n\nLocal authored skill:\n'+catalog[identifier].raw)

    def test_file_frontmatter_not_registry_display_metadata(self):
        api=self.api()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            with patch.object(skills,'SKILLS',root),patch.object(skills,'REGISTRY',root/'registry.json'):
                item=api.verified_catalog()['example']
                self.assertEqual(item.frontmatter,{'name':'example','description':'Test'})
                (root/'example/SKILL.md').write_bytes(b'changed')
                self.assertNotIn('example',api.verified_catalog())
                self.assertIn('example',skills.skill_rejections())

    def test_strict_frontmatter_rejects_ambiguous_or_privilege_fields(self):
        api=self.api()
        bad=[b'name: example\nname: example\ndescription: Test',b'name: example\ndescription: Test\t# hidden',b'name: example\ndescription: Test:\tvalue',b'name: example\ndescription: true',b'name: example\ndescription: "quoted"',b'name: example\ndescription: Test\nallowed-tools: shell',b'name: example\ndescription: |\n Test',b'name: example\ndescription: &alias Test',b'name: other\ndescription: Test',b'name: example\ndescription: Test\nhooks: run']
        for header in bad:
            with self.subTest(header=header),self.assertRaises(ValueError):api.parse_frontmatter(b'---\n'+header+b'\n---\nBody','example')
        with self.assertRaises(ValueError):api.parse_frontmatter(b'---\nname: example\ndescription: \xff\n---\n','example')

    def test_no_noncanonical_or_foreign_uri_resolution(self):
        api=self.api();catalog=api.verified_catalog()
        for uri in ('https://example/SKILL.md','skill://../SKILL.md','skill://home-planning/../SKILL.md','skill://home-planning/%53KILL.md','skill://home-planning/SKILL.md?x=1','skill://home-planning/SKILL.md#x','skill://HOME-PLANNING/SKILL.md','skill://unknown/SKILL.md'):
            with self.subTest(uri=uri),self.assertRaises(ValueError):api.resolve_skill(uri,catalog)
        with self.assertRaises(ValueError):skills.selected_prompt({'skills':[]},'home-planning')

    def test_extra_files_oversize_registry_and_filter_failure_reject(self):
        api=self.api()
        for kind in ('extra-root','extra-file','oversize','truncated','duplicate','foreign'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);entry=self.fixture(root)
                if kind=='extra-root':(root/'unexpected.txt').write_text('data')
                if kind=='extra-file':(root/'example/run.py').write_text('inert')
                if kind=='oversize':(root/'example/SKILL.md').write_bytes(b'x'*16001)
                if kind=='truncated':(root/'example/SKILL.md').write_bytes(b'---\n')
                if kind=='duplicate':(root/'registry.json').write_text(json.dumps({'version':1,'skills':[entry,entry]}))
                if kind=='foreign':entry['origin']='remote';(root/'registry.json').write_text(json.dumps({'version':1,'skills':[entry]}))
                with patch.object(skills,'SKILLS',root),patch.object(skills,'REGISTRY',root/'registry.json'):
                    if kind in ('extra-root','duplicate'):
                        with self.assertRaises((ValueError,OSError)):api.verified_catalog()
                    else:
                        self.assertEqual(api.verified_catalog(),{})
                        self.assertIn('example',skills.skill_rejections())
        with patch.object(skills,'inspect_message',side_effect=ValueError('scanner failed')):
            self.assertEqual(api.verified_catalog(),{})
            self.assertTrue(skills.skill_rejections())

    def test_symlinks_reject(self):
        api=self.api()
        for relative in ('registry.json','example/SKILL.md'):
            with self.subTest(relative=relative),tempfile.TemporaryDirectory() as temp:
                parent=Path(temp);root=parent/'skills';root.mkdir();self.fixture(root)
                target=root/relative;real=parent/'original';target.rename(real)
                try:
                    target.symlink_to(real)
                except OSError as exc:
                    self.skipTest('Symlink creation unavailable: '+str(exc))
                with patch.object(skills,'SKILLS',root),patch.object(skills,'REGISTRY',root/'registry.json'):
                    if relative=='registry.json':
                        with self.assertRaises(ValueError):api.verified_catalog()
                    else:
                        self.assertNotIn('example',api.verified_catalog())
                        self.assertIn('example',skills.skill_rejections())

    def test_failed_activation_never_reaches_model(self):
        from runtime import inference
        with patch.object(inference,'ollama') as upstream:
            reply=inference.chat('home-assistant',[{'role':'user','content':'Hello'}],'it-interview')
            self.assertEqual(reply['status'],400);upstream.assert_not_called()
            with patch.object(skills,'load_skills',side_effect=ValueError('Invalid registry')):
                reply=inference.chat('home-assistant',[{'role':'user','content':'Hello'}],'home-planning')
                self.assertEqual(reply['status'],400);upstream.assert_not_called()
