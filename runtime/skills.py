"""Only explicitly registered, local, prompt-only skills; never execute files."""
import hashlib
import json
import re
from pathlib import Path
from runtime.text_filter import inspect_message

ROOT=Path(__file__).resolve().parents[1]
SKILLS=ROOT/'skills'
REGISTRY=SKILLS/'registry.json'

def load_skills():
    registry=json.loads(REGISTRY.read_text(encoding='utf-8'))
    if set(registry)!={'version','skills'} or registry['version']!=1 or not isinstance(registry['skills'],list):
        raise ValueError('Invalid local skill registry')
    if len(registry['skills'])>128:
        raise ValueError('Too many local skills')
    result={}
    for entry in registry['skills']:
        if not isinstance(entry,dict) or set(entry)!={'id','name','description','origin','sha256'}:
            raise ValueError('Invalid skill registration')
        identifier=entry['id']
        if not isinstance(identifier,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',identifier) or identifier in result:
            raise ValueError('Invalid or duplicate skill ID')
        if entry['origin']!='local-authored':
            raise ValueError('Only locally authored skills are allowed')
        folder=SKILLS/identifier
        path=folder/'SKILL.md'
        if folder.is_symlink() or path.is_symlink() or not path.resolve().is_relative_to(SKILLS.resolve()):
            raise ValueError('Skill path escapes local registry')
        if {p.name for p in folder.iterdir()}!={'SKILL.md'}:
            raise ValueError('Skills must be prompt-only; ancillary executables are not allowed')
        raw=path.read_bytes()
        if len(raw)>16000 or hashlib.sha256(raw).hexdigest()!=entry['sha256']:
            raise ValueError('Skill changed; local review and registration required')
        text=raw.decode('utf-8')
        inspect_message(text)
        if not text.startswith('---\nname: '+identifier+'\n'):
            raise ValueError('Skill identity mismatch')
        if any(not isinstance(entry[key],str) or not entry[key].strip() for key in ('name','description')):
            raise ValueError('Invalid skill metadata')
        result[identifier]={**entry,'text':text}
    if {p.name for p in SKILLS.iterdir() if p.is_dir()}!=set(result):
        raise ValueError('Unregistered local skill folder')
    return result

def selected_prompt(persona,identifier):
    if identifier is None:
        return ''
    if not isinstance(identifier,str) or identifier not in persona.get('skills',[]):
        raise ValueError('Skill not allowed for this persona')
    skills=load_skills()
    if identifier not in skills:
        raise ValueError('Unknown local skill')
    return '\n\nLocal authored skill:\n'+skills[identifier]['text']

def summaries():
    return [{k:s[k] for k in ('id','name','description')} for s in load_skills().values()]
