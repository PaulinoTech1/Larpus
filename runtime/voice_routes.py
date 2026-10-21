"""Local /api/voice route: bounded speech requests with output-side screening.

Speech synthesis receives assistant reply text (streamed or replayed). It is
screened like model output: isolated output DLP (secrets, protected/system
prompt values, private hosts and paths) plus hidden control/format characters.
It is deliberately not screened by the inbound prompt-injection filter, whose
instruction-override patterns match ordinary security prose ("never disable
security updates") and silently ended speech. TTS gives text no model access.
"""
from runtime import voice
from runtime.diagnostics import report
from runtime.dlp import inspect_output
from runtime.text_filter import TextHeld, hidden_format

SPEECH_LIMIT=2200
COMMANDS={'larpus mute':'Microphone muted. Even I know when to stop talking.',
          'mute voice':'Microphone muted. Even I know when to stop talking.',
          'larpus reset chat':'Fresh conversation. A clean slate, without the chalk dust.'}

def speech_reasons(text,system_prompt):
    """Sorted reason codes that hold speech text; empty means speakable."""
    if not isinstance(text,str) or not text.strip() or len(text)>SPEECH_LIMIT:
        raise ValueError('Invalid speech text')
    hidden=hidden_format(text)
    return sorted(set(([hidden] if hidden else [])+inspect_output(text,system_prompt=system_prompt)))

def held(reasons):
    """Log reason codes only (never the text) and return the HTTP refusal."""
    error_id=report('LARP-VOICE-HELD',ValueError('Speech held by output screening'),reasons)
    return 422,{'error':'Speech held by local output DLP.','code':'speech_held','error_id':error_id}

def synthesize(text,personas):
    reasons=speech_reasons(text,'\n'.join(p['system_prompt'] for p in personas.values()))
    if reasons:return held(reasons)
    return 200,voice.call({'action':'synthesize','text':text})

def confirmation(phrase,personas):
    if phrase in COMMANDS:return COMMANDS[phrase]
    if phrase.startswith('larpus switch to '):
        selected=next((p for p in personas.values() if p['name'].lower()==phrase[17:]),None)
        if selected:return 'Switching to '+selected['name']+'. Let us get into character.'
    return None

def transcribe(data,personas):
    if not isinstance(data,dict) or set(data)!={'action','audio'} or data['action']!='transcribe' or not isinstance(data['audio'],str):
        raise ValueError('Expected a bounded audio request')
    result=voice.call(data)
    spoken=confirmation(result['transcript'].lower().rstrip('.!?').strip(),personas)
    if spoken:
        try:
            result.update(voice.call({'action':'synthesize','text':spoken}))
        except OSError:
            result['voice_error']='Local speech unavailable.'
    return 200,result

def handle(data,personas):
    """Return (status, body[, headers]) for one parsed /api/voice request."""
    try:
        if isinstance(data,dict) and set(data)=={'action','text'} and data['action']=='synthesize':
            return synthesize(data['text'],personas)
        return transcribe(data,personas)
    except TextHeld:
        return 422,{'error':'Speech held by local text filter.'}
    except (ValueError,TypeError):
        return 400,{'error':'Invalid voice request. Use mono 16 kHz PCM WAV, at most 30 seconds.'}
    except OSError:
        return 503,{'error':'Local voice worker unavailable. No cloud fallback.'},{'Retry-After':'2'}
