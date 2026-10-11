"""Offline CPU speech worker, invoked over stdio inside a sealed container."""
import base64
import importlib.util
import io
import json
import sys
import wave
import socket
import struct
import time

MAX_AUDIO = 960044  # 30 seconds, mono PCM16 at 16 kHz plus WAV header
SOCKET='/tmp/larpus-speech.sock'
MODELS={}

def speech_models(kind):
    if kind not in MODELS:
        if kind=='tts':
            from piper import PiperVoice
            MODELS[kind]=PiperVoice.load('/models/en_GB-alan-medium.onnx')
        else:
            from faster_whisper import WhisperModel
            spec=importlib.util.spec_from_file_location('voicestudio_asr','/studio/asr.py')
            studio=importlib.util.module_from_spec(spec);spec.loader.exec_module(studio)
            studio._model=SpeechOnlyModel(WhisperModel('/models/whisper-small.en',device='cpu',compute_type='int8',cpu_threads=8,local_files_only=True))
            MODELS[kind]=studio
    return MODELS[kind]

class SpeechOnlyModel:
    """Keep the pinned VoiceStudio adapter, with local decoding policy underneath."""
    def __init__(self, model):
        self.model = model

    def transcribe(self, audio, **options):
        options.update(vad_filter=True, vad_parameters={'threshold':0.6,
            'min_speech_duration_ms':300, 'min_silence_duration_ms':500,
            'speech_pad_ms':200}, temperature=0.0, condition_on_previous_text=False,
            no_speech_threshold=0.5, log_prob_threshold=-0.8,
            compression_ratio_threshold=2.2)
        segments, info = self.model.transcribe(audio, **options)
        return (s for s in segments if s.no_speech_prob < 0.5
                and s.avg_logprob >= -0.8 and s.compression_ratio <= 2.2), info

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
        import numpy as np
        with wave.open(io.BytesIO(raw),'rb') as wav:
            samples = np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(np.float32)/32768
        # Reject digital silence before expensive decoding. VAD handles speech/noise
        # separation; neither this nor confidence thresholds guarantees accuracy.
        if float(np.sqrt(np.mean(samples*samples))) < 0.003:
            return {'transcript':'', 'no_speech':True}
        studio = speech_models('stt')
        result = studio._transcribe(samples, False, {'beam_size':3}, {'language':'en','temperature':0.0})
        text = result['text'].strip()
        if not text:
            return {'transcript':'', 'no_speech':True}
        if len(text)>8000:
            raise ValueError('Speech transcript too long')
        return {'transcript':text}
    if request.get('action') == 'synthesize' and set(request) == {'action','text'}:
        text = request['text']
        if not isinstance(text,str) or not text.strip() or len(text)>2200:
            raise ValueError('Invalid speech text')
        from piper import SynthesisConfig
        voice = speech_models('tts')
        output = io.BytesIO()
        # Natural pace plus a short breath between sentences; 0.85 sounded rushed and clipped.
        config=SynthesisConfig(length_scale=1.0,noise_scale=0.6,noise_w_scale=0.8)
        with wave.open(output,'wb') as wav:
            for index,chunk in enumerate(voice.synthesize(text,config)):
                if index==0:
                    wav.setframerate(chunk.sample_rate);wav.setsampwidth(chunk.sample_width);wav.setnchannels(chunk.sample_channels)
                else:
                    wav.writeframes(bytes(int(chunk.sample_rate*0.22)*chunk.sample_width*chunk.sample_channels))
                wav.writeframes(chunk.audio_int16_bytes)
        return {'audio':base64.b64encode(output.getvalue()).decode(), 'mime':'audio/wav'}
    raise ValueError('Unsupported voice operation')

def receive(stream,limit):
    def exact(count):
        parts=[]
        while count:
            block=stream.recv(count)
            if not block:raise ValueError('Truncated speech frame')
            parts.append(block);count-=len(block)
        return b''.join(parts)
    size=struct.unpack('!I',exact(4))[0]
    if not 0<size<=limit:raise ValueError('Speech frame exceeds limit')
    return json.loads(exact(size))

def send_frame(stream,value,limit):
    raw=json.dumps(value).encode()
    if len(raw)>limit:raise ValueError('Speech result exceeds limit')
    stream.sendall(struct.pack('!I',len(raw))+raw)

def serve():
    # Unix IPC inside one network-disabled container; no TCP listener or host mount.
    import os
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
        server.bind(SOCKET);os.chmod(SOCKET,0o600);server.listen(2)
        while True:
            connection,_=server.accept()
            with connection:
                connection.settimeout(120)
                try:
                    request=receive(connection,1400000);start=time.monotonic()
                    if request=={'action':'status'}:
                        result={'ready':True,'cached_models':sorted(MODELS)}
                    else:
                        cached=request.get('action')=='synthesize' and 'tts' in MODELS or request.get('action')=='transcribe' and 'stt' in MODELS
                        result=run(request);result['timing']={'worker_ms':round((time.monotonic()-start)*1000),'model_cached':bool(cached)}
                    send_frame(connection,result,16000000)
                except Exception:
                    try:send_frame(connection,{'error':'Local speech processing failed.'},16000000)
                    except OSError:pass

def client():
    raw=sys.stdin.buffer.read(1400001)
    if len(raw)>1400000:raise ValueError('Speech request exceeds limit')
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
        connection.settimeout(120);connection.connect(SOCKET)
        send_frame(connection,json.loads(raw),1400000)
        print(json.dumps(receive(connection,16000000)))

def main():
    try:
        if sys.argv[1:]==['--serve']:return serve()
        if sys.argv[1:]==['--client']:return client()
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
