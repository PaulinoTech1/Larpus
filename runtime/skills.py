"""Only explicitly registered, local, prompt-only skills; never execute files."""
import hashlib
import json
import re
from pathlib import Path
from runtime.text_filter import inspect_message

ROOT=Path(__file__).resolve().parents[1]
SKILLS=ROOT/'skills'
REGISTRY=SKILLS/'registry.json'

def _regular_bytes(path, limit):
    if path.is_symlink() or getattr(path.lstat(),'st_file_attributes',0)&1024 or not path.is_file():
        raise ValueError('Local skill input must be a regular file')
    with path.open('rb') as stream:
        raw=stream.read(limit+1)
    if len(raw)>limit:
        raise ValueError('Local skill input exceeds size limit')
    return raw

def parse_frontmatter(raw, identifier):
    """Accept only the two plain scalar fields used by reviewed local skills."""
    text=raw.decode('utf-8')
    parts=text.split('\n---\n',1)
    if len(parts)!=2 or not parts[0].startswith('---\n') or '\r' in parts[0]:
        raise ValueError('Invalid local skill frontmatter')
    lines=parts[0][4:].split('\n')
    if len(lines)!=2 or lines[0]!='name: '+identifier or not lines[1].startswith('description: '):
        raise ValueError('Invalid local skill frontmatter fields')
    description=lines[1][13:]
    if (not re.fullmatch(r'[A-Za-z][^\r\n]*',description) or description!=description.strip()
            or re.search(r':\s|\s#|[\x00-\x1f\x7f]',description)
            or description.lower() in {'true','false','null','yes','no','on','off'}):
        raise ValueError('Invalid local skill description scalar')
    return {'name':identifier,'description':description}

def load_skills():
    registry=json.loads(_regular_bytes(REGISTRY,1000000).decode('utf-8'))
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
        if folder.is_symlink() or getattr(folder.lstat(),'st_file_attributes',0)&1024 or not path.resolve().is_relative_to(SKILLS.resolve()):
            raise ValueError('Skill path escapes local registry')
        if {p.name for p in folder.iterdir()}!={'SKILL.md'}:
            raise ValueError('Skills must be prompt-only; ancillary executables are not allowed')
        raw=_regular_bytes(path,16000)
        if len(raw)>16000 or hashlib.sha256(raw).hexdigest()!=entry['sha256']:
            raise ValueError('Skill changed; local review and registration required')
        text=raw.decode('utf-8')
        inspect_message(text)
        parse_frontmatter(raw,identifier)
        if any(not isinstance(entry[key],str) or not entry[key].strip() for key in ('name','description')):
            raise ValueError('Invalid skill metadata')
        result[identifier]={**entry,'text':text}
    if {p.name for p in SKILLS.iterdir()}!=set(result)|{'registry.json'}:
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
