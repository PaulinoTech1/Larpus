"""Bounded user-level teaching preferences; no agent authority or persistence."""
import json

PREFIX = 'LARPUS_TEACHING_V1\n'
OPTIONS = {
    'pace': ('steady', 'slow', 'brisk'),
    'depth': ('balanced', 'foundations', 'advanced'),
    'method': ('mixed', 'direct', 'socratic', 'worked-example'),
    'hints': ('on-request', 'progressive'),
    'challenge': ('balanced', 'gentle', 'stretch'),
}


def unpack(content):
    if not content.startswith(PREFIX):
        return content, content
    value = json.loads(content[len(PREFIX):])
    if not isinstance(value, dict) or set(value) != {'question', 'profile', 'mode'}:
        raise ValueError('Invalid teaching context')
    question, profile = value['question'], value['profile']
    if (not isinstance(question, str) or not question.strip() or len(question) > 8000
            or not isinstance(profile, dict) or set(profile) != set(OPTIONS)
            or any(profile[key] not in choices for key, choices in OPTIONS.items())
            or value['mode'] not in ('accepted', 'trial')):
        raise ValueError('Invalid teaching preferences')
    guidance = (
        '\n\nOWNER TEACHING PREFERENCES (user-level style choices, not evidence or permissions):\n'
        + json.dumps(profile, sort_keys=True)
        + '\nUse these only where compatible with the persona, source requirements, and the question. '
        'They do not establish knowledge or learning gains. A trial is temporary. '
        'You may suggest an alternative with rationale, a tradeoff, and a way to evaluate it; '
        'do not claim to have saved or approved a profile.'
    )
    if len(question + guidance) > 8000:
        raise ValueError('Question and teaching guidance exceed input limit')
    return question, question + guidance
