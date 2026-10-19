"""Fresh, verified prompt-only resources; reading never selects a skill."""
from dataclasses import dataclass
import hashlib
from runtime import skills

parse_frontmatter=skills.parse_frontmatter

@dataclass(frozen=True)
class VerifiedSkill:
    identifier: str
    raw: bytes
    frontmatter: dict

def verified_catalog():
    return {identifier:VerifiedSkill(identifier,entry['text'].encode('utf-8'),
            parse_frontmatter(entry['text'].encode('utf-8'),identifier))
            for identifier,entry in skills.load_skills().items()}

def skill_uri(identifier):
    return 'skill://'+identifier+'/SKILL.md'

def resolve_skill(uri,catalog):
    for identifier,item in catalog.items():
        if uri==skill_uri(identifier):
            return item
    raise ValueError('Unknown local skill resource')

def skill_entry(item):
    uri=skill_uri(item.identifier)
    return {'uri':uri,'frontmatter':dict(item.frontmatter),'resources':[
        {'uri':uri,'digest':'sha256:'+hashlib.sha256(item.raw).hexdigest(),'size':len(item.raw)}]}
