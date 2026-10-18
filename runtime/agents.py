"""AEI kickoff: configuration-driven inference, no tool execution."""
import json
import re
from pathlib import Path
from runtime.text_filter import filter_messages, DEFENSE_PROMPT
from runtime.skills import load_skills, selected_prompt, summaries

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

def load_personas():
    skills=load_skills()
    personas = {}
    for path in sorted((ROOT / 'agents/personas').glob('*.json')):
        p = json.loads(path.read_text(encoding='utf-8'))
        required={'version', 'id', 'name', 'description', 'system_prompt', 'model', 'temperature', 'voice'}
        if not required.issubset(p) or set(p)-required-{'skills'}:
            raise ValueError(f'Invalid persona fields: {path.name}')
        if p['version'] != 1 or not isinstance(p['id'], str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', p['id']):
            raise ValueError('Invalid persona identity')
        for key in ('name', 'description', 'system_prompt', 'model'):
            if not isinstance(p[key], str) or not p[key].strip():
                raise ValueError(f'Invalid {key}')
        if not re.fullmatch(r'[A-Za-z0-9_.:-]+', p['model']) or p['model'].endswith('-cloud'):
            raise ValueError('Only local model identifiers allowed')
        if type(p['temperature']) not in (int, float) or not 0 <= p['temperature'] <= 1:
            raise ValueError('Invalid temperature')
        if p['voice'] is not None and not isinstance(p['voice'], str):
            raise ValueError('Invalid voice')
        if not isinstance(p.get('skills',[]),list) or any(not isinstance(s,str) or s not in skills for s in p.get('skills',[])) or len(set(p.get('skills',[])))!=len(p.get('skills',[])):
            raise ValueError('Invalid local skill selection')
        if p['id'] in personas:
            raise ValueError('Duplicate persona')
        personas[p['id']] = p
    if not personas:
        raise ValueError('No personas configured')
    return personas

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
