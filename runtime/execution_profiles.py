"""Strict request values. Profiles never confer authority or choose a backend."""
from dataclasses import dataclass

PROFILES=('verified','ultra-fast','diagnostic')
INTERACTIONS=('conversation','analysis','coding')

@dataclass(frozen=True)
class ExecutionContext:
    profile: str
    interaction: str
    base: str

def resolve(value: object = None) -> ExecutionContext:
    if value is None:value={}
    if type(value) is not dict or set(value)-{'profile','interaction','base'}:
        raise ValueError('Invalid execution fields')
    profile=value.get('profile','verified');interaction=value.get('interaction','conversation')
    if not valid_choice(profile,PROFILES) or not valid_choice(interaction,INTERACTIONS):
        raise ValueError('Invalid execution selection')
    if profile!='diagnostic' and 'base' in value:raise ValueError('Base is diagnostic-only')
    base=value.get('base','verified') if profile=='diagnostic' else profile
    if type(base) is not str or base not in ('verified','ultra-fast'):raise ValueError('Invalid execution base')
    return ExecutionContext(profile,interaction,base)

def to_wire(context: ExecutionContext) -> dict:
    value={'profile':context.profile,'interaction':context.interaction}
    if context.profile=='diagnostic':value['base']=context.base
    checked=resolve(value)
    if checked!=context:raise ValueError('Inconsistent execution context')
    return value

def valid_choice(value,choices):
    return type(value) is str and value in choices
