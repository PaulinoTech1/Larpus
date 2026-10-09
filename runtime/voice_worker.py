"""Offline CPU speech worker, invoked over stdio inside a sealed container."""
import base64
import importlib.util
import io
import json
import sys
import wave

MAX_AUDIO = 960044  # 30 seconds, mono PCM16 at 16 kHz plus WAV header

def validate_wav(raw):
    if not 44 <= len(raw) <= MAX_AUDIO:
        raise ValueError('Audio must be at most 30 seconds')
    with wave.open(io.BytesIO(raw), 'rb') as audio:
        if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getcomptype()) != (1, 2, 16000, 'NONE'):
            raise ValueError('Expected mono PCM16 WAV at 16 kHz')
        if not 1600 <= audio.getnframes() <= 480000 or len(audio.readframes(audio.getnframes())) != audio.getnframes()*2:
            raise ValueError('Invalid audio duration or truncated frames')

def run(request):
    if request.get('action') == 'transcribe' and set(request) == {'action','audio'}:
        raw = base64.b64decode(request['audio'], validate=True)
        validate_wav(raw)
        from faster_whisper import WhisperModel
        spec = importlib.util.spec_from_file_location('voicestudio_asr', '/studio/asr.py')
        studio = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(studio)
        studio._model = WhisperModel('/models/whisper-small.en', device='cpu', compute_type='int8', cpu_threads=8, local_files_only=True)
        import numpy as np
        with wave.open(io.BytesIO(raw),'rb') as wav:
            samples = np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(np.float32)/32768
        result = studio._transcribe(samples, False, {'beam_size':1}, {'language':'en'})
        text = result['text'].strip()
        if not text or len(text)>8000:
            raise ValueError('No clear speech detected')
        return {'transcript':text}
    if request.get('action') == 'synthesize' and set(request) == {'action','text'}:
        text = request['text']
        if not isinstance(text,str) or not text.strip() or len(text)>2200:
            raise ValueError('Invalid speech text')
        from piper import PiperVoice
        voice = PiperVoice.load('/models/en_GB-alan-medium.onnx')
        output = io.BytesIO()
        with wave.open(output,'wb') as wav:
            voice.synthesize_wav(text,wav)
        return {'audio':base64.b64encode(output.getvalue()).decode(), 'mime':'audio/wav'}
    raise ValueError('Unsupported voice operation')

def main():
    try:
        raw = sys.stdin.buffer.read(1400001)
        if len(raw)>1400000:
            raise ValueError('Voice request too large')
        result = run(json.loads(raw))
        print(json.dumps(result))
    except Exception:
        print(json.dumps({'error':'Local voice processing failed; check installed artifacts and audio format.'}))
        raise SystemExit(1)

if __name__ == '__main__':
    main()
