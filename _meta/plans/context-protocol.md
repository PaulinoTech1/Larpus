# Context, compression and handoff
Goal: longer useful offline conversations without silently losing decisions.
Constraints: preserve existing uncommitted companion work, auth, MCP tools, CPU voice and GPU-only replies; no commit/push.
Inputs: existing transcript, approved evidence, current model and owner-entered notes.
Outputs: 262,144-token target policy, automatic/manual rolling summary, bounded portable handoff and accurate HUD.
Done when: bounds/error/legacy tests pass; complete release gates; live long-chat and GPU/context verification; rollback retained.
Choice: existing chat MCP transport with reserved bounded summarization envelope, fixed server summary instructions and output DLP. No new tool, database or dependency.
Rejected: simply raising token/turn limits retains silent trimming; independent summarizer adds model/VRAM/dependency cost; extractive clipping loses decisions without acknowledgement.
Budget: conservative UTF-8 byte upper bound plus message overhead reserves output space; measured Ollama counts remain authoritative in HUD. Larger context does not imply 262k words.
Compression: machine-generated JSON capsule with goal, facts, decisions, constraints, open tasks, next steps, references and uncertainty. Keep recent turns verbatim; retain full bounded browser transcript. Commit capsule only after successful screened generation; failures retain original state.
Handoff: versioned local JSON export/import, validated fields and size, no system instructions or automatic actions. Import stages context, never executes content.
Maintenance: candidate preparation does not resize the shared model. During authorised activation/drain, benchmark 262,144 tokens with explicitly evaluated KV cache settings and require full GPU placement and reported context. If validation fails, restore previous release and warm its prior context. No model weights/image/dependency changes. KV-cache changes are now explicitly authorised.
Validation: Unicode/boundary, malformed summaries/imports, failed compression, continuation and compatibility checks; manual summary fidelity and physical/browser limits stated.
AgentDB unavailable; repo and local receipts used instead.

User steering: "wait I want to target 260K tokens context window" supersedes the proposed 16k target.
Verified locally: Ollama 0.40.0, installed qwen35 Q4_K_M model advertises 262144 tokens; loaded at 4096, 100% GPU. No explicit cache quantization environment setting.
260k native target is confirmed; full-GPU fit, long-input latency and summary fidelity remain UNVERIFIED. No live resize or deployment performed. Source code remains an unfinished draft.
A 4-bit KV cache is a separate setting from Q4 model weights and may affect quality; do not claim target achieved from model metadata or an empty-context allocation alone.
Compression/handoff remain part of the requested work. Revise HTTP/MCP bounds, budget/estimation and HUD to support the target before release. Do not deploy this draft.

User authorised quantized KV cache. Owner model-cache maintenance builds a stopped q4_0 candidate from the same cached image, preserves network-none pod/read-only models/GPU mounts, disables Linux cgroup swap, and uses single parallel request + Flash Attention. Drain gateway only for actual switch/measurement; retain old model container until GPU/context and readiness pass, with journal recovery and automatic restoration on failure. CPU offload remains informational, not enabled.
CPU/RAM note: CPU inference uses RAM; avoiding disk swap is distinct. Current WSL memory 31 GiB, 8 GiB available swap/0 used; container memory.swap.max=0 does not guarantee Windows never pages WSL VM memory. Do not change global WSL or Windows paging settings.
