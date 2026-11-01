# Prompt Guard 2 86M staging decision

Status: the checkout gateway classifies chat messages with the local Horizon
snapshot when it starts. An injection label is stored in the private
quarantine and removed from the transcript; the gateway keeps serving.
The frozen release, agent image, and live gateway process are unchanged
until a release is activated. Evidence is not classified.
An isolated CPU benchmark harness is
at `data/evals/prompt-guard-2-86m/bench_cpu.py`. It requires an approved local
model snapshot and has not produced an inference result: the exact upstream
weight-file access check returned `GatedRepoError` (HTTP 401) on 2026-10-25.
The live output-quality baseline
`baseline-large-20261025-2135` was running when this was written. Do not change
its serving path or load a competing classifier during that run.

## Intended contract

The requested model is Meta's `meta-llama/Llama-Prompt-Guard-2-86M`, a binary
prompt-attack classifier, not Llama Guard 2. For each untrusted message, the
proposed order is the existing size and role checks, Stegdetect's complete
allow decision, the local Unicode and rule checks in `runtime/text_filter.py`,
then Prompt Guard. A new classifier must never turn an existing hold into an
allow. Retrieval evidence must continue to use its existing gate; extending
model classification to evidence requires separate measurement and an explicit
scope decision. No raw prompt may leave the PC for classification.

The model card gives a 512-token context. Every token of an accepted message
must be covered by tokenizer-aware segments; silent truncation is unacceptable.
An unavailable model, incomplete classification, or segment error must hold
closed if the classifier is ever enabled as an enforcement gate. A shadow
evaluation may record bounded decisions without changing responses, provided
it does not record raw prompts or compromise the baseline.

## Assumptions and decision gates

| Assumption | Status | Impact if wrong | Validation |
| --- | --- | --- | --- |
| “After Stegdetect” means per-message ordering | Unconfirmed | Wrong integration scope | Confirm with owner |
| Owner can obtain and use the gated Meta weights under the Llama 4 license | Owner stated acceptance in chat; Hugging Face account access unverified and weight request returned HTTP 401 | Download and use blocked | Owner completes the model's account-side access flow; then record artifact license and hashes |
| CPU inference meets latency and memory limits | Unknown | Longer answers or resource contention | Measure on this PC after the baseline, including long inputs and concurrency |
| A useful operating threshold exists for LARPUS traffic | Unknown | False holds or missed attacks | Compare labeled benign/attack cases; report both error types by family |

Before a release snapshot: pin the exact model revision and every artifact hash,
keep the license with the artifact, use a local/offline CPU runtime, define a
maximum number of segments and timeout, and add negative tests for unavailable
weights, failed inference, long input, history, and existing Stegdetect holds.
Measure cold and warm p50/p95 classification latency, end-to-end latency, CPU
and RAM, GPU residency, and false holds/misses on representative reviewed cases.
Do not infer local latency from Meta's A100 benchmark. Preserve the active
release and rollback path. Only then use `scripts/releases.py stage` and
`prepare` for a reviewable candidate; activation is a separate decision.

## Current Stegdetect timing evidence

The LARPUS 21-case synthetic evaluator has no duration field, so it does not
answer the current per-request latency question. A historical standalone
Windows Stegdetect resource run with 16,384-character samples reported case
medians from 6.2 to 27.1 ms; its ordinary-text case was 9.347 ms median and
12.076 ms p95. That run included scanner inspection and JSON conversion,
used larger inputs than LARPUS's 8,000-character message limit, and did not
measure the live combined input gate. Current live latency remains unknown.

Sources: [model card](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M),
[Meta README](https://github.com/meta-llama/PurpleLlama/blob/main/Llama-Prompt-Guard-2/README.md),
`docs/TEXT_FILTER.md`, `E:/speedzone_MS/Stego/docs/p2-resource-results.json`.

## 2026-10-25 isolated Horizon comparison probe

The requested measured head-to-head remains blocked: Meta's 86M weight-file
request still returns HTTP 401. Do not substitute Horizon timing for Meta timing
or compare Meta's published A100 GPU result to this local CPU run.

The public, ungated `Horizon-Labs/prompt-injection-guard-small` model was
downloaded at revision `0e3774536debbcd71dbb8534ef71451b583853b8` to the
WSL test area. The local safetensors SHA-256 is
`a23196c117baf414b4b8abd138c5f5656e728877c0bdb2775c361ee89df16deb`;
tokenizer JSON SHA-256 is
`47834a7dbbb0c4324fe9569fe47955241594a9ee539c9e478755d6fbc51e5f46`.
No runtime or release snapshot was changed.

The ignored receipt `data/evals/prompt-guard-2-86m/horizon-cpu-2048.json`
records a warm-up followed by three repeats of four synthetic 2,048-content-
token cases (one repeated benign phrase, one obvious injection phrase at each
of the start, middle and end). Each case used one 2,050-token model input
including special tokens. The CPU process had nice 19, one PyTorch thread and
affinity to WSL CPUs 18–19. Median end-to-end classification time was 3,388 ms
(range 3,258–3,682 ms); model/tokenizer load took 2.72 s; peak process RSS was
1,411,484 KiB. All three benign repeats were labeled `SAFE`, and all nine
attack repeats `INJECTION`. The runner used raw model argmax without Horizon's
optional obfuscation normalizer or threshold tuning. These hand-constructed
examples test plumbing and timing, not a detection rate or representative
false-positive rate. No GPU
inference was requested. LARPUS's separate baseline remained running and its
recorded final failures stayed at zero during the probe; that is not proof of
zero timing interference.

The first harness attempt failed before inference because the installed
`TokenizersBackend` lacked `build_inputs_with_special_tokens`. The corrected
runner checks the CLS/SEP layout against the tokenizer's own encoded output,
then runs the model. The failed attempt produced no performance result.

[Horizon model card](https://huggingface.co/Horizon-Labs/prompt-injection-guard-small)
states Apache-2.0, 141M parameters, 8k supported positions, and training at
up to 1,024 tokens. Its published comparison with Prompt Guard 2 is produced
by Horizon; it is useful for screening candidates but is not an independent
LARPUS acceptance result.

## 2026-10-27 WSL denial

Later Codex attempts to repeat or extend this probe failed before Python,
thread setup, or model load. The cause is the Codex restricted token, not
WSL capacity. An owner PowerShell at Medium integrity can list `Larpus` and
run `/bin/true` in it. MXC can run `cmd.exe` on this PC and still cannot
enumerate WSL distributions. Use `scripts/invoke-larpus.ps1` from outside
the sandbox. Full comparison and the launch command:
[WSL sandbox access](WSL_SANDBOX_ACCESS.md).
