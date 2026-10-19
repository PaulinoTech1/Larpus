"""Reference test peer: approvals bind origin, URI, manifest and raw content."""
import hashlib
from runtime.skill_resources import parse_frontmatter

def verify(origin,approved_origin,entry,raw):
    if origin!=approved_origin:
        raise ValueError('Origin approval mismatch')
    resources=entry.get('resources')
    if not isinstance(resources,list) or len(resources)!=1:
        raise ValueError('Incomplete prompt-only manifest')
    resource=resources[0]
    if resource.get('uri')!=entry['uri'] or resource.get('size')!=len(raw):
        raise ValueError('Resource identity or size mismatch')
    if resource.get('digest')!='sha256:'+hashlib.sha256(raw).hexdigest():
        raise ValueError('Resource digest mismatch')
    name=entry['frontmatter']['name']
    if entry['uri']!='skill://'+name+'/SKILL.md' or parse_frontmatter(raw,name)!=entry['frontmatter']:
        raise ValueError('Frontmatter mismatch')
    return raw
