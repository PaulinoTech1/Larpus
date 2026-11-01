"""Resident local Horizon classifier. No network, no prompt logging."""
import hashlib
import os
import struct
import sys
from pathlib import Path

def segments(tokens, payload, overlap):
    if not tokens or payload <= 0 or not 0 <= overlap < payload:
        raise ValueError('Invalid payload/overlap or empty message')
    result = []
    start = 0
    while True:
        end = min(len(tokens), start + payload)
        result.append((start, end, tokens[start:end]))
        if end == len(tokens):
            break
        start = end - overlap
    if result[0][0] != 0 or result[-1][1] != len(tokens):
        raise RuntimeError('Incomplete coverage')
    if any(left[1] < right[0] for left, right in zip(result, result[1:])):
        raise RuntimeError('Coverage gap')
    return result

def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def decide(probability, threshold):
    if type(probability) not in (int, float) or type(threshold) not in (int, float):
        return 'unavailable'
    if not 0 <= probability <= 1 or not 0 < threshold < 1:
        return 'unavailable'
    return 'hold' if probability >= threshold else 'allow'

def judge(text, tokenizer, model, torch, window, overlap, injection_id, threshold):
    tokens = tokenizer.encode(text, add_special_tokens=False)
    if not tokens:
        return 'unavailable'
    for _start, _end, chunk in segments(tokens, window - 2, overlap):
        ids = torch.tensor([[tokenizer.cls_token_id, *chunk, tokenizer.sep_token_id]], dtype=torch.long)
        with torch.inference_mode():
            logits = model(input_ids=ids, attention_mask=torch.ones_like(ids)).logits
        probability = float(torch.softmax(logits, dim=-1)[0, injection_id])
        decision = decide(probability, threshold)
        if decision != 'allow':
            return decision
    return 'allow'

def load():
    os.environ.update(CUDA_VISIBLE_DEVICES='', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      HF_HUB_DISABLE_TELEMETRY='1', TOKENIZERS_PARALLELISM='false',
                      OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    source = Path(os.environ['HORIZON_SOURCE'])
    threads = int(os.environ['HORIZON_THREADS'])
    window = int(os.environ['HORIZON_WINDOW'])
    overlap = int(os.environ['HORIZON_OVERLAP'])
    expected = {
        'model.safetensors': os.environ['HORIZON_SHA_MODEL'],
        'tokenizer.json': os.environ['HORIZON_SHA_TOKENIZER'],
        'config.json': os.environ['HORIZON_SHA_CONFIG'],
    }
    for name, digest in expected.items():
        if sha256(source / name) != digest:
            raise RuntimeError('checksum')
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    available = sorted(os.sched_getaffinity(0))
    if len(available) < threads:
        raise RuntimeError('cpus')
    os.sched_setaffinity(0, available[-threads:])
    os.nice(19)
    torch.set_num_interop_threads(1)
    torch.set_num_threads(threads)
    tokenizer = AutoTokenizer.from_pretrained(source, local_files_only=True, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        source, local_files_only=True, trust_remote_code=False, device_map='cpu').eval()
    if any(param.device.type != 'cpu' for param in model.parameters()):
        raise RuntimeError('device')
    if None in (tokenizer.cls_token_id, tokenizer.sep_token_id) or window > model.config.max_position_embeddings:
        raise RuntimeError('layout')
    labels = {int(key): value for key, value in model.config.id2label.items()}
    if set(labels.values()) != {'SAFE', 'INJECTION'}:
        raise RuntimeError('labels')
    threshold = float(os.environ['HORIZON_INJECTION_THRESHOLD'])
    if abs(threshold - 0.5) > 1e-9:
        raise RuntimeError('threshold')
    injection_id = next(key for key, value in labels.items() if value == 'INJECTION')
    return tokenizer, model, torch, window, overlap, injection_id, threshold

def serve():
    try:
        tokenizer, model, torch, window, overlap, injection_id, threshold = load()
    except Exception:
        sys.stdout.write('failed\n')
        sys.stdout.flush()
        return 1
    sys.stdout.write('ready\n')
    sys.stdout.flush()
    stdin = sys.stdin.buffer
    while True:
        header = stdin.read(4)
        if not header:
            return 0
        if len(header) != 4:
            sys.stdout.write('unavailable\n')
            sys.stdout.flush()
            return 1
        size = struct.unpack('>I', header)[0]
        if not 0 < size <= 32000:
            sys.stdout.write('unavailable\n')
            sys.stdout.flush()
            continue
        blob = stdin.read(size)
        if len(blob) != size:
            sys.stdout.write('unavailable\n')
            sys.stdout.flush()
            return 1
        try:
            status = judge(blob.decode('utf-8'), tokenizer, model, torch, window, overlap, injection_id, threshold)
        except Exception:
            status = 'unavailable'
        sys.stdout.write(status + '\n')
        sys.stdout.flush()

if __name__ == '__main__':
    sys.exit(serve())
