"""AEI kickoff: configuration-driven inference, no tool execution."""
import json
import re
from pathlib import Path
from runtime.text_filter import filter_messages, DEFENSE_PROMPT
from runtime.skills import CatalogRejected, PersonaRejected, load_skills, selected_prompt, skill_rejections, summaries

_KNOWN_PERSONAS=None
_REJECTED_PERSONAS={}

ROOT = Path(__file__).resolve().parents[1]
CONVERSATION_PROGRESS = (
    '\nCONVERSATION PROGRESS: Read the latest message as an update to the conversation. '
    'Answer what changed or remains unresolved, rather than restarting the explanation. '
    'Earlier assistant replies are context, not a writing template to imitate. '
    'Do not recycle previous paragraphs, closing remarks, jokes, advice lists or already-answered questions '
    'unless the user asks for repetition or a recap. If advice was tried, declined or ruled out, '
    'acknowledge that and adapt; do not prescribe it again as a new solution. '
    'Keep the user\'s stated circumstances, corrections and promotional terms distinct from public list prices; '
    'do not replace them with assumptions. Earlier assistant claims are not evidence: correct errors rather '
    'than repeat them. Do not invent novelty or new tasks merely to keep talking. A brief relevant reply is enough. '
    'For feelings or distress, be respectful and drop the jokes; avoid psychological diagnoses, labels, '
    'unsupported claims about brain chemistry or motives, and scolding. This guidance applies to style '
    'and conversational continuity, not permissions or source requirements. Do not disparage the user\'s '
    'projects or assert their performance bottlenecks without measurements. Personal learning and '
    'enjoyment can be valid goals; do not dismiss them merely because a project is optional.'
)

def _persona_identity(p):
    required={'version','id','name','description','system_prompt','model','temperature','voice'}
    if not isinstance(p,dict) or not required.issubset(p) or set(p)-required-{'skills'}:
        raise PersonaRejected('Invalid persona fields')
    if p['version']!=1 or not isinstance(p['id'],str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',p['id']):
        raise PersonaRejected('Invalid persona identity')
    return p

def _persona_values(p):
    for key in ('name','description','system_prompt','model'):
        if not isinstance(p[key],str) or not p[key].strip():
            raise PersonaRejected('Invalid persona field')
    if not re.fullmatch(r'[A-Za-z0-9_.:-]+',p['model']) or p['model'].endswith('-cloud'):
        raise PersonaRejected('Only local model identifiers allowed')
    if type(p['temperature']) not in (int,float) or not 0<=p['temperature']<=1:
        raise PersonaRejected('Invalid temperature')
    if p['voice'] is not None and not isinstance(p['voice'],str):
        raise PersonaRejected('Invalid voice')
    return p

def _persona_skills(p,skills):
    selected=p.get('skills',[])
    if not isinstance(selected,list) or any(not isinstance(item,str) for item in selected) or len(set(selected))!=len(selected):
        raise PersonaRejected('Invalid local skill selection')
    rejected=skill_rejections()
    if any(item not in skills and item not in rejected for item in selected):
        raise PersonaRejected('Invalid local skill selection')
    return {**p,'skills':[item for item in selected if item in skills]}

def _stem(path):
    return path.stem if re.fullmatch(r'[a-z][a-z0-9-]{0,63}',path.stem) else None

def load_personas():
    global _KNOWN_PERSONAS
    skills=load_skills()
    personas={};rejected={}
    for path in sorted((ROOT/'agents/personas').glob('*.json')):
        try:
            persona=_persona_skills(_persona_values(_persona_identity(json.loads(path.read_text(encoding='utf-8')))),skills)
        except PersonaRejected as exc:
            stem=_stem(path)
            if stem is None:raise CatalogRejected('Invalid persona identity') from exc
            rejected[stem]=exc.args[0];continue
        except (json.JSONDecodeError,UnicodeError,OSError):
            stem=_stem(path)
            if stem is None:raise CatalogRejected('Invalid persona fields')
            rejected[stem]='Invalid persona fields';continue
        if persona['id']!=path.stem or persona['id'] in personas or persona['id'] in rejected:
            _REJECTED_PERSONAS.clear()
            raise CatalogRejected('Duplicate persona')
        personas[persona['id']]=persona
    if not personas:
        _REJECTED_PERSONAS.clear()
        raise CatalogRejected('No personas configured')
    _KNOWN_PERSONAS=set(personas)
    _REJECTED_PERSONAS.clear();_REJECTED_PERSONAS.update(rejected)
    return personas

def persona_known(identifier):
    """True when a fresh load accepts the persona. A catalog-document failure still raises."""
    return identifier in load_personas()

def persona_rejections():
    return dict(_REJECTED_PERSONAS)

def require_persona(identifier):
    current=load_personas()
    if isinstance(identifier,str) and identifier in current:
        return current[identifier]
    reason=_REJECTED_PERSONAS.get(identifier) if isinstance(identifier,str) else None
    if reason:raise PersonaRejected(reason)
    raise ValueError('Unknown persona')

def messages_for(persona, history, skill=None):
    if not isinstance(history, list) or not 1 <= len(history) <= 402:
        raise ValueError('Send 1–40 conversation messages')
    clean = []
    for i, msg in enumerate(history):
        if not isinstance(msg, dict) or set(msg) != {'role', 'content'}:
            raise ValueError('Invalid message')
        if msg['role'] != ('user' if i % 2 == 0 else 'assistant'):
            raise ValueError('Messages must alternate user and assistant')
        if not isinstance(msg['content'], str) or not msg['content'].strip() or len(msg['content']) > 8000:
            raise ValueError('Message must contain 1–8000 characters')
        clean.append(msg)
    if clean[-1]['role'] != 'user':
        raise ValueError('Last message must be from user')
    filter_messages(clean)
    return [{'role': 'system', 'content': persona['system_prompt'] + selected_prompt(persona,skill) + DEFENSE_PROMPT + CONVERSATION_PROGRESS}] + clean
