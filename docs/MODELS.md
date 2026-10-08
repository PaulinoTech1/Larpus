# Local model candidates

Start with **qwen3:14b**, Q4_K_M, listed at 9.3 GB in the
[official Ollama entry](https://ollama.com/library/qwen3:14b).
For a larger text-only comparison, use
[qwen3:30b-a3b-instruct-2507-q4_K_M](https://ollama.com/library/qwen3:30b-a3b-instruct-2507-q4_K_M),
listed at 19 GB. These are weight sizes, not total GPU requirements. KV cache,
context, desktop usage and voice models need additional space.

The owner's GPU was detected as RTX 3090 Ti with 24,564 MiB total and about
4,216 MiB already used during the check. That makes the 19 GB candidate tight;
14B is the starting recommendation for voice headroom, not a measured quality win.
Keep the existing qwen2.5:14b persona configuration until a candidate is installed
and reviewed. Windows Home provisioning has now cached this baseline inside WSL2;
a real response used 100% GPU at context 4096. Qwen3 candidates are not installed
or benchmarked, and this single response does not establish quality or speed.

Prepare weights during an explicitly online setup window, before enforcing outbound
denial. Afterwards inference stays on literal 127.0.0.1:11434 with no cloud fallback.
In the isolated deployment, that loopback belongs to the network-disabled pod,
not Windows. The benchmark/select commands below are owner-only host-development
utilities using Windows loopback; they are not wired to the isolated model service.
For the sealed deployment, prepare new model weights during maintenance, edit and
review persona model targets, then reseal/redeploy. Its runtime files are read-only.

```powershell
ollama pull qwen3:14b
python -m runtime.models benchmark qwen3:14b
python -m runtime.models select qwen3:14b
```

Selection requires an installed, configured candidate and updates both personas;
restart the gateway. Candidate policy lives in config/models.json. Benchmark uses
three fixed household, interview and fiction prompts, 4096 context and 256 output
tokens, unloading after each probe. It records digest, cold-load latency and token
rate in data/models/latest-benchmark.json without saving answers. Review real chat
quality and peak VRAM separately, including simultaneous voice work. This utility
is an owner CLI and is not exposed as an MCP tool. No automatic model downloads.
