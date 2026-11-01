"""Gateway client for the resident Larpus Horizon classifier."""
import json
import os
import struct
import subprocess
import threading
from pathlib import Path

from runtime.station_paths import ROOT
from runtime.text_filter import TextHeld

CONFIG = ROOT / 'config' / 'horizon.json'
WORKER = ROOT / 'runtime' / 'horizon_worker.py'
REMOTE = '/home/larpus/horizon_guard_worker.py'
_LOCK = threading.Lock()
_STATE = {'installed': False, 'process': None, 'config': None}

def configured():
    if not CONFIG.is_file():
        return None
    data = json.loads(CONFIG.read_text(encoding='utf-8'))
    files = data.get('files')
    if data.get('enabled') is not True or data.get('threads') != 6 or data.get('window') != 4096 or data.get('overlap') != 64 or data.get('injection_threshold') != 0.5:
        raise ValueError('Horizon deployment must stay at 6 threads, a 4096 window, and the 0.5 model label boundary')
    if data.get('distribution') != 'Larpus' or data.get('user') != 'larpus':
        raise ValueError('Horizon worker must use the Larpus distribution')
    if data.get('python') != '/home/larpus/train-venv/bin/python' or data.get('source') != '/home/larpus/train-models/prompt-guard-eval/horizon-small-0e377453':
        raise ValueError('Horizon source pin does not match the measured snapshot')
    if not isinstance(files, dict) or set(files) != {'model.safetensors', 'tokenizer.json', 'config.json'}:
        raise ValueError('Horizon file pins are incomplete')
    if any(not isinstance(item, str) or len(item) != 64 for item in files.values()):
        raise ValueError('Horizon file pin is not a sha256')
    return data

def installed():
    return _STATE['installed']

def _wsl():
    return str(Path(os.environ['SYSTEMROOT']) / 'System32' / 'wsl.exe')

def _command(config):
    return [_wsl(), '--distribution', config['distribution'], '--user', config['user'], '--exec', config['python']]

def _environment(config):
    files = config['files']
    return [
        'HORIZON_SOURCE=' + config['source'],
        'HORIZON_THREADS=' + str(config['threads']),
        'HORIZON_WINDOW=' + str(config['window']),
        'HORIZON_OVERLAP=' + str(config['overlap']),
        'HORIZON_INJECTION_THRESHOLD=' + str(config['injection_threshold']),
        'HORIZON_SHA_MODEL=' + files['model.safetensors'],
        'HORIZON_SHA_TOKENIZER=' + files['tokenizer.json'],
        'HORIZON_SHA_CONFIG=' + files['config.json'],
    ]

def _publish(config):
    payload = WORKER.read_bytes().replace(b'\r\n', b'\n')
    copy = subprocess.run(_command(config)[:-1] + ['/usr/bin/tee', REMOTE], input=payload, capture_output=True, timeout=30)
    if copy.returncode != 0 or not payload:
        raise OSError('Horizon worker was not published')

def _readline(process, timeout):
    box = []
    def read():
        box.append(process.stdout.readline())
    thread = threading.Thread(target=read, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive() or not box or not box[0]:
        raise OSError('Horizon worker timed out')
    return box[0].decode('ascii', 'replace').strip()

def _open(config):
    _publish(config)
    process = subprocess.Popen(
        _command(config)[:-1] + ['/usr/bin/env', *_environment(config), config['python'], '-u', REMOTE],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    status = _readline(process, 120)
    if status != 'ready':
        process.kill()
        raise OSError('Horizon worker did not become ready')
    return process

def install():
    config = configured()
    if config is None:
        return
    with _LOCK:
        if _STATE['installed']:
            return
        _STATE['config'] = config
        _STATE['process'] = _open(config)
        _STATE['installed'] = True

def shutdown():
    with _LOCK:
        process = _STATE['process']
        _STATE['process'] = None
        _STATE['installed'] = False
    if process is not None and process.poll() is None:
        process.kill()

def _ask(text):
    data = text.encode('utf-8')
    if not 0 < len(data) <= 32000:
        raise OSError('Horizon input is outside the chat bound')
    process = _STATE['process']
    if process is None or process.poll() is not None:
        _STATE['process'] = process = _open(_STATE['config'])
    try:
        process.stdin.write(struct.pack('>I', len(data)) + data)
        process.stdin.flush()
        return _readline(process, 30)
    except Exception:
        if process.poll() is None:
            process.kill()
        _STATE['process'] = None
        raise

def check(text):
    if not _STATE['installed']:
        return
    with _LOCK:
        try:
            status = _ask(text)
        except Exception as exc:
            raise TextHeld('horizon_unavailable', unavailable=True) from exc
    if status == 'allow':
        return
    if status == 'hold':
        raise TextHeld('prompt_injection')
    raise TextHeld('horizon_unavailable', unavailable=True)
