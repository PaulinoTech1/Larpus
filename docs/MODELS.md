# GPU model deployment

Current default (2026-11-02): **larpus3.8:27b-q4** (Qwen3.8 27B UD-Q4_K_M) for all
twelve personas, chosen through model selection; qwen3.5:27b-q4_K_M stays
selectable as larpus-3.5. See docs/DECISIONS.md and docs/MODEL_SWITCHING.md.

Original deployment: **qwen3.5:27b-q4_K_M**, the explicit 27B Q4_K_M Ollama tag, for all
twelve personas. The previous qwen2.5:14b remains cached for deliberate rollback.
Ollama 0.40.0 is pinned in the existing model container. The owner's RTX 3090 Ti
has 24,564 MiB VRAM. Voice remains on CPU: Faster Whisper uses device=cpu and
Piper runs in the separate worker without any GPU devices or driver mounts.

## Runtime settings

- Context: 131072 tokens with a q8_0 KV cache (raised from 4096 on 2026-10-09). Output cap: 1024 tokens; persona instructions favour brief
  spoken answers, while allowing technical explanations.
- Thinking: false for conversational latency. Keep-alive: -1 to retain loaded weights
  until the model server is stopped or the model is explicitly unloaded.
- GPU offload request: num_gpu=99 for this model. After inference, the fixed
  loopback /api/ps report must show size_vram >= size > 0 before a reply can pass
  to isolated DLP and the gateway. CPU/offloaded replies return 503 rather than
  silently degrading. A failed or malformed placement probe also fails closed.
- Health reports model_gpu using actual Ollama placement, separately from NVIDIA
  hardware detection. An unloaded model is unverified, not a green GPU claim.
  The HUD connection line shows the model processor on page load.

GPU residency does not mean Windows process CPU usage or system RAM is zero.
Tokenisation, scheduling, WSL and the model file cache can use CPU/system memory
while inference weights are GPU-resident. In Task Manager, inspect dedicated GPU
memory and a CUDA/compute graph rather than relying solely on the 3D graph.
LM Studio and other GPU applications can consume VRAM; they are not stopped
automatically. If memory is insufficient, free other GPU allocations and retry.

## Artifact preparation and isolation

Only the temporary owner-run larpus-qwen35-prepare container has network access
for public model retrieval. It uses the cached pinned Ollama image, no published
ports, no GPU and only /home/larpus/models mounted read-write. No conversations
or credentials enter preparation. Stop and remove this temporary container after
Ollama completes SHA-256 verification; retain the cached model files.

Production larpus-model stays in larpus-offline with network=none, read-only model
cache and only the existing NVIDIA device/library mounts. No inference port is
published. New persona/runtime/config sources require rebuilding larpus-agent
and repinning data/isolated-deployment.json. The stopped prior agent is retained
for rollback. Passwords, TLS material, voice models and quarantine are preserved.

Rebuild the cache during an explicitly online maintenance window with:

```bash
podman exec larpus-qwen35-prepare ollama pull qwen3.5:27b-q4_K_M
```

The temporary container must first be created with the boundaries described above;
never enable networking or model pulls in the production pod. The existing
deploy/windows-home/prepare-cache.sh is the full initial online preparation tool.

## Owner verification

```powershell
wsl --distribution Larpus --user larpus --exec env XDG_RUNTIME_DIR=/run/user/1000 podman exec larpus-model ollama ps
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv
```

Run `python scripts/benchmark-isolated.py` for the three fixed probes through
the sealed agent. It refuses non-GPU residency and writes a local numeric receipt.

Expected active-model processor: 100% GPU. Speech container preflight independently
verifies that voice has no GPU devices. Cold startup includes disk/model loading;
warm generation throughput is a different measurement. Local benchmark receipts
under ignored data/models record model digest, context, token counts, load/prompt/
generation durations and actual placement without saving generated answers.
The older runtime.models owner CLI targets Windows loopback and is not the sealed
WSL benchmark route.

Sources: [Ollama model](https://ollama.com/library/qwen3.5:27b-q4_K_M),
[thinking controls](https://docs.ollama.com/capabilities/thinking),
[GPU residency and keep-alive](https://docs.ollama.com/faq).

## Measured on the owner's GPU (2026-10-09)

[Benchmark receipt](QWEN35-GPU-BENCHMARK.json), manifest digest
`64ae5b1d651fb2709d5928ccb8dcfb4bb2cc9c2c8001ac34497e36a6cf905b59`:

| Probe | Complete request | Load | Generation | GPU residency |
|---|---:|---:|---:|---|
| Cold greeting | 31.587 s | 26.256 s | 39.21 tokens/s | 100% GPU |
| Warm cryptography | 3.876 s | 0.109 s | 40.86 tokens/s | 100% GPU |
| Warm enterprise | 3.361 s | 0.084 s | 41.57 tokens/s | 100% GPU |

All probes used 4096 context and emitted no thinking trace. Ollama reported
16,638,866,881 bytes both total and GPU-resident for the loaded text model.
Windows NVIDIA telemetry showed approximately 20,299 MiB total dedicated memory
in use after loading, including other GPU applications and runtime overhead.
The download includes a vision projector; these measurements are text-only.
They do not establish long-context, image, model-quality or concurrent-load performance.
The matching [offline scan receipt](QWEN35-GPU-SCAN-RECEIPT.json) retains eight MCP
findings (MEDIUM aggregate risk); all 64 local prompt skills passed.

One real short spoken HUD reply completed the full gateway/MCP/GPU/DLP/CPU-TTS path in 6.31 seconds. This excludes microphone capture/STT and does not predict arbitrary reply lengths.
