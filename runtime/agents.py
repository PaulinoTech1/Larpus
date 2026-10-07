"""AEI kickoff: configuration-driven inference, no tool execution."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_personas():
    personas = {}
    for path in sorted((ROOT / 'agents/personas').glob('*.json')):
        p = json.loads(path.read_text(encoding='utf-8'))
        if set(p) != {'version', 'id', 'name', 'description', 'system_prompt', 'model', 'temperature', 'voice'}:
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
        if p['id'] in personas:
            raise ValueError('Duplicate persona')
        personas[p['id']] = p
    if not personas:
        raise ValueError('No personas configured')
    return personas

def messages_for(persona, history):
    if not isinstance(history, list) or not 1 <= len(history) <= 40:
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
    return [{'role': 'system', 'content': persona['system_prompt']}] + clean
