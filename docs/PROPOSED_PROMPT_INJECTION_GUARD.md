# Proposed layered prompt-injection classification (2026-10-25)

Status: **Architecture proposal only. No new model, inference service, policy, release, or live deployment is asserted by this document.** The active frozen release and its security claims are unchanged. A CPU-bound classifier is the current-hardware experiment; a second GPU-based guard LLM is future work only.

## Motivation and scope

LARPUS already uses Stegdetect for Unicode/steganographic carriers, its trusted input gate, fixed MCP tools and approved skills, a capability-limited private inference broker, and an output-DLP quarantine. Carrier detection, semantic injection classification, authorization, and disclosure prevention are distinct jobs. The October 22 text-filter evaluation documented false positives on benign technical material and missed constructed carrier families; those authored sets do not predict real-world error rates. A probabilistic classifier can provide additional *evidence* about instruction-hijacking attempts, not a proof that inputs are safe.

The working goal is **improve recall and benign-text discrimination without creating new authority or unacceptable latency**. Do not imply that adding a second classifier solves prompt injection. An attacker may still influence model answers even when the sandbox and broker enforce their privileges correctly.

## Current-hardware experiment: CPU classifier

- Candidate: Horizon-Labs/prompt-injection-guard-small, **141M parameters** (not 131M), an mmBERT-small-based binary classifier for direct and indirect prompt injection.
- Source / terms: https://huggingface.co/Horizon-Labs/prompt-injection-guard-small ; model card reports an **ungated Apache-2.0** release, locally runnable PyTorch and ONNX variants, and permissively licensed training inputs. Verify the exact artifact revision, dependency licenses, weight checksums, and acceptable redistribution/usage terms during preparation. The model publisher's accuracy tables are not LARPUS validation.
- Selection rationale: straightforward access without a request for identifying registration details, permissive open-source licensing, local/offline execution, explicit indirect/RAG/tool-result focus, and native ONNX support. This is a **privacy and licensing preference**, not a claim that Meta necessarily uploads inference inputs. Meta's download/access flow can request personal registration information. Avoid misleadingly equating model download identity requirements with cloud inference or exfiltration.
- Comparison reference: **Meta Llama Prompt Guard 2 86M**, not Llama Guard 2; Meta also supplies a 22M Prompt Guard 2. Parameter counts do not prove classifier accuracy, calibration, inference latency, security, or language coverage; the 141M choice must survive quality and performance comparison.
- Runtime target: a separately constrained **CPU-only**, offline classification worker on the Ryzen 9 5900X; retain Qwen 27B on the RTX 3090 Ti. Do not borrow GPU VRAM or assume free GPU headroom. Budget threads, resident RAM, worker concurrency, and CPU contention with the existing embedding/ONNX reranker. Reuse a warm ONNX Runtime session; profile and benchmark before setting admission deadlines or targets.
- The publisher advertises up to 8K tokens of input and reports training with maximum length 1,024. Validate long-context behavior; do not silently truncate untrusted evidence. For inputs beyond the verified window, define deterministic segmentation and aggregation, caps on total windows and tokens, overlap policy, and refusal/hold on incomplete scans.
- Verify the exact ONNX graph and preprocessing path against the upstream reference; its provided quantized ONNX artifact is not necessarily a full INT8 model. Validate score and decision parity before adopting quantization.

## Proposed trust path, not deployed

Untrusted input or retrieved passage
  -> existing Stegdetect and LARPUS structural input gate
  -> proposed isolated CPU neural classifier (with source-trust context and evidence labels)
  -> a **trusted, versioned policy** deciding allow / hold-for-review / reject
  -> existing fixed MCP/retrieval and private capability-constrained inference broker
  -> Qwen model
  -> existing output DLP / quarantine before delivery.

The diagram is conceptual: retrieval evidence, user inputs, local skills, and tool results enter through different trust boundaries. Insert checks at the final trusted forwarding boundary for each untrusted source, not just at the browser entry. No neural classifier is permitted to change MCP tool permissions, model prompts, lane identity, containers, mount points, network policy, or DLP behavior. A low injection score **cannot override a mandatory deterministic hold**, and a model score must never be interpreted as authorization.

Classify legitimate owner instructions separately from lower-trust embedded instructions in document/tool text. Preserve original carrier evidence and source identity. Any upstream text that looks like a configuration command for the detector remains data and cannot set its threshold. Keep the classifier process without model-callable network, filesystem, credential, or privileged host access. No remote inference for private material.

Decide policy and error semantics before enabling enforcement: incomplete windows, tokenizer/ONNX failure, missing pinned model, invalid input, stale hashes, out-of-memory, unavailable worker, and timeouts must not silently become an allow decision. An optional shadow-only classifier may fail without modifying the active gate; once a classifier becomes a required security gate, failure should hold or reject at its trusted boundary. Test denial-of-service impact and prevent an external text payload from causing unbounded inference.

## Future GPU-based secondary guard (not part of this experiment)

Investigate a separate **guard LLM**, with Meta Llama Guard 4 as one *possible* candidate, only when an independent GPU or higher-capacity GPU and a new evaluated serving architecture are available. Meta documents **Llama Guard 4 12B** as a multimodal **content safety** model. It is distinct from Llama Prompt Guard 2 86M and is **not** automatically an equivalent indirect prompt-injection detector. Its license and access requirements differ from Apache-2.0; the project's permissive/open-source preference may favor a different future model.

Such a future worker must use a separate capability and queue, must not receive broader data or authority than required, must undergo independent licensing/privacy review, and must be evaluated for prompt-injection-specific utility, memory residency, interference with Qwen, latency, and safety-policy mismatches. No secondary LLM, dedicated second GPU, or upgraded GPU is present in the current LARPUS experiment.

## Required evidence and activation gates

1. **Source and reproducibility:** pin exact model revision, tokenizer, config, preprocessing, ONNX artifact, hashes, licenses, signatures if supplied, and isolated dependency versions. Inspect artifacts before allowing offline installation; no model auto-download in production.
2. **Baseline comparison:** use the unchanged Stegdetect + current LARPUS gate, optionally Meta Prompt Guard 2 86M where its license/access allow, and the Horizon candidate. Distinguish agentic indirect injection, ordinary user instructions, mathematical notation/Greek, multilingual text, benign quoted attacks, Unicode obfuscation, and structured data.
3. **Labels and splitting:** preserve independently adjudicated, source-separated held-out inputs; hold out whole attack families, source documents, and near-duplicate generators. Report TP/FP/TN/FN and precision/recall by stratum, with confidence intervals and uncertain labels reported separately. Existing authored synthetic examples remain regression tests, not population estimates.
4. **Performance:** record warmup/startup, tokenizer and inference time separately, CPU cores/threads, RAM, prompt/window lengths and batch policy, p50/p95/p99 under isolated and contended loads, plus user-visible first-DLP-approved-text and task-completion latency. Do not assume adding a classifier is free; test contention with retrieval reranking.
5. **Security regression:** verified no-forwarding on fail-closed outcomes; no prompt-level override of decisions, limits, or tool permissions; adversarial saturation/timeout tests; exact model/worker mount and network isolation; refusal on malformed or incomplete results; retention of existing output DLP and broker constraints.
6. **Release hygiene:** shadow-mode comparison without granting approval or affecting production, then an owner-approved prepared frozen release, fresh full scanner and functional readiness, live canary/rollback/reboot tests, and a separately recorded activation receipt. No activation without measured evidence and an explicit decision.

## Primary references and limits

- Horizon model card: https://huggingface.co/Horizon-Labs/prompt-injection-guard-small (141M, Apache-2.0, ungated, ONNX, training/evaluation caveats).
- Meta Prompt Guard 2: https://dev.meta.ai/llama/docs/model-cards-and-prompt-formats/prompt-guard (86M and 22M).
- Meta Llama Guard 4: https://dev.meta.ai/llama/docs/model-cards-and-prompt-formats/llama-guard-4 (12B multimodal safeguard).
- Existing LARPUS facts and boundaries: ARCHITECTURE.md, STATUS.md, BROKER_HARDENING.md, STEGDETECT_EVALUATION.md, FILTER_FP_FN_2026-10-22.md.

The model publishers' comparisons are **third-party self-reported**, not LARPUS-specific verification. No inference latency, memory fit, accuracy, interoperability, or operational security benefit has been measured for the proposed model on the LARPUS station.
