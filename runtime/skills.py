"""Only explicitly registered, local, prompt-only skills; never execute files."""
import hashlib
import json
import re
from pathlib import Path
from runtime.text_filter import TextHeld, inspect_message

ROOT=Path(__file__).resolve().parents[1]
SKILLS=ROOT/'skills'
REGISTRY=SKILLS/'registry.json'

class CatalogRejected(ValueError):
    """The registry document itself is unusable. No persona is served."""
    scope='catalog'

class SkillRejected(CatalogRejected):
    """One named skill failed. Other skills stay available."""
    scope='skill'

class PersonaRejected(CatalogRejected):
    """One persona file or its skill selection failed. Other personas stay available."""
    scope='persona'

_REJECTED={}
_SKILL_REASONS={
 'Invalid local skill description scalar','Invalid local skill frontmatter','Invalid local skill frontmatter fields',
 'Invalid skill metadata','Local skill input exceeds size limit','Local skill input must be a regular file',
 'Only locally authored skills are allowed','Skill changed; local review and registration required',
 'Skill path escapes local registry','Skills must be prompt-only; ancillary executables are not allowed'}

def _regular_bytes(path, limit):
    if path.is_symlink() or getattr(path.lstat(),'st_file_attributes',0)&1024 or not path.is_file():
        raise CatalogRejected('Local skill input must be a regular file')
    with path.open('rb') as stream:
        raw=stream.read(limit+1)
    if len(raw)>limit:
        raise CatalogRejected('Local skill input exceeds size limit')
    return raw

def parse_frontmatter(raw, identifier):
    """Accept only the two plain scalar fields used by reviewed local skills."""
    text=raw.decode('utf-8')
    parts=text.split('\n---\n',1)
    if len(parts)!=2 or not parts[0].startswith('---\n') or '\r' in parts[0]:
        raise CatalogRejected('Invalid local skill frontmatter')
    lines=parts[0][4:].split('\n')
    if len(lines)!=2 or lines[0]!='name: '+identifier or not lines[1].startswith('description: '):
        raise CatalogRejected('Invalid local skill frontmatter fields')
    description=lines[1][13:]
    if (not re.fullmatch(r'[A-Za-z][^\r\n]*',description) or description!=description.strip()
            or re.search(r':\s|\s#|[\x00-\x1f\x7f]',description)
            or description.lower() in {'true','false','null','yes','no','on','off'}):
        raise CatalogRejected('Invalid local skill description scalar')
    return {'name':identifier,'description':description}

def _fail_catalog(message):
    _REJECTED.clear()
    raise CatalogRejected(message)

def _skill_files(entry,identifier):
    if entry['origin']!='local-authored':
        raise SkillRejected('Only locally authored skills are allowed')
    folder=SKILLS/identifier
    path=folder/'SKILL.md'
    if folder.is_symlink() or getattr(folder.lstat(),'st_file_attributes',0)&1024 or not path.resolve().is_relative_to(SKILLS.resolve()):
        raise SkillRejected('Skill path escapes local registry')
    if {item.name for item in folder.iterdir()}!={'SKILL.md'}:
        raise SkillRejected('Skills must be prompt-only; ancillary executables are not allowed')
    return path

def _skill_text(entry,identifier,path):
    try:
        raw=_regular_bytes(path,16000)
        if len(raw)>16000 or hashlib.sha256(raw).hexdigest()!=entry['sha256']:
            raise SkillRejected('Skill changed; local review and registration required')
        text=raw.decode('utf-8')
        inspect_message(text)
        parse_frontmatter(raw,identifier)
    except SkillRejected:
        raise
    except (CatalogRejected,UnicodeError,ValueError,TextHeld) as exc:
        message=exc.args[0] if isinstance(exc,CatalogRejected) and exc.args and isinstance(exc.args[0],str) and exc.args[0] in _SKILL_REASONS else 'Skill changed; local review and registration required'
        raise SkillRejected(message) from exc
    if any(not isinstance(entry[key],str) or not entry[key].strip() for key in ('name','description')):
        raise SkillRejected('Invalid skill metadata')
    return {**entry,'text':text}

def load_skills():
    try:
        registry=json.loads(_regular_bytes(REGISTRY,1000000).decode('utf-8'))
    except (CatalogRejected,UnicodeError,json.JSONDecodeError) as exc:
        _fail_catalog('Invalid local skill registry')
    if set(registry)!={'version','skills'} or registry['version']!=1 or not isinstance(registry['skills'],list):
        _fail_catalog('Invalid local skill registry')
    if len(registry['skills'])>128:
        _fail_catalog('Too many local skills')
    result={};rejected={}
    for entry in registry['skills']:
        if not isinstance(entry,dict) or set(entry)!={'id','name','description','origin','sha256'}:
            _fail_catalog('Invalid skill registration')
        identifier=entry['id']
        if not isinstance(identifier,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',identifier) or identifier in result or identifier in rejected:
            _fail_catalog('Invalid or duplicate skill ID')
        try:
            result[identifier]=_skill_text(entry,identifier,_skill_files(entry,identifier))
        except SkillRejected as exc:
            rejected[identifier]=exc.args[0]
        except OSError:
            rejected[identifier]='Skill path escapes local registry'
    names={item.name for item in SKILLS.iterdir()}
    if not names<=set(result)|set(rejected)|{'registry.json'}:
        _fail_catalog('Unregistered local skill folder')
    _REJECTED.clear();_REJECTED.update(rejected)
    return result

def skill_rejections():
    """Names rejected by the last successful load_skills. Empty after a catalog-level failure."""
    return dict(_REJECTED)

def selected_prompt(persona,identifier):
    if identifier is None:
        return ''
    if not isinstance(identifier,str):
        raise ValueError('Skill not allowed for this persona')
    skills=load_skills()
    if identifier in _REJECTED:
        raise SkillRejected(_REJECTED[identifier])
    if identifier not in persona.get('skills',[]):
        raise ValueError('Skill not allowed for this persona')
    if identifier not in skills:
        raise ValueError('Unknown local skill')
    return '\n\nLocal authored skill:\n'+skills[identifier]['text']

def summaries():
    return [{k:s[k] for k in ('id','name','description')} for s in load_skills().values()]
