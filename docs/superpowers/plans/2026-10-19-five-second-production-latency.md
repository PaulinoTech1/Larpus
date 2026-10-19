# Five-second production response plan

> **For agentic workers:** Use `superpowers:executing-plans` for native execution after review. Steps use checkbox (`- [ ]`) syntax. This is a planning proposal, not authorization to implement, start services, publish or activate a release.

**Goal:** Qualify first approved response text within five seconds for at least 90% of a declared warm production workload, preserving security decisions, evidence, answer quality and delivery consistency.

**Architecture:** First expose the actual critical path, then reduce fresh security-collection transport and repeated fixed MCP process setup. Keep authorization/integrity checks per request. Optimize retrieval or screening implementation only where measurements demonstrate an equivalent, useful saving. Advance one independently measured change at a time.

**Tech stack:** Existing Windows/Python gateway, SDK 2.3 stdio, E:-backed rootless Podman/WSL, selected GPU Larpus 3.8, Assembly optimized four-worker scorer. No dependency/model/driver/firmware changes or overclocking.

**Spec:** The success criteria, constraints, experiments and acceptance gates below are the proposed design brief. Implementation details of a reusable MCP session require the Task 1 lifecycle evidence and Task 3 feasibility gate; this document does not claim those properties already exist.

## What current evidence establishes

Selected release: `7df2e957751642d6ace4630fa047fe94`. Latest HTTP baseline
`f7ebb4535ecc41f387fc2cb84555f4a5`: 24 measured requests after eight excluded warmups.

| Measurement | Latest observation |
| --- | ---: |
| First text median / p90 | 7.210 / 8.796 seconds |
| Complete reply median / p90 | 9.066 / 11.149 seconds |
| Fresh isolation preflight median | 1.954 seconds |
| MCP process/connection setup median | 1.204 seconds |
| Retrieval median | 2.066 seconds |
| Model first-frame median | 1.386 seconds |

Stages overlap: first-checked-text timing includes other inference work, and
model first frame need not contain visible text. Do not add all stage medians.
The p90 goal needs approximately 3.8 seconds of tail reduction from this sample;
reaching a five-second median alone is insufficient.

The earlier fresh single-collector experiment reached 4.796-second median but
6.141-second p95 on a narrower MCP workload. Its pacing confirmation failed:
median longest inter-chunk gap increased 14.3%. It remains rejected. The Skills
candidate also remains inactive. Neither is the starting production payload.
See [latency](../../RESPONSE_LATENCY_2026_10_19.md),
[consistency](../../RESPONSE_CONSISTENCY_2026_10_19.md) and
[latest measurements](../../MCP_SKILLS_PERFORMANCE_2026_10_19.md).

## Target and fixed constraints

- Primary server target: p90 <=5.000 seconds from receipt of a valid request to first approved, nonempty text. Count legitimate requests that fail or exceed five seconds as misses. Never substitute a status message, acknowledgement or unfiltered token for answer text.
- Verify the same five-second target from HUD submit to first rendered approved text on the owner's actual LAN path. Report server and browser distributions separately; server results alone do not prove visible production latency.
- Warm means the selected model has passed full-GPU/context readiness before submission. Model startup, switching, compression, simultaneous submissions, notes preemption and near-capacity contexts have separate results. Retain an all-request view; do not hide those tails in a warm-only headline.
- Keep the model, quantization, context 131072, sampling, output limits, prompts, source corpus, evidence/reranking budgets and reference screening fixed in the primary comparison. Keep Assembly optimized and the 20-processor WSL ceiling. No model downgrade, shortened evidence or reply, cached answer, automatic persona/skill substitution, or cloud fallback.
- Preserve input/DLP/output gates, sentence-release rules, source hashes, exact approved tools, fixed executor, rootless/network-none containment, mounts, capabilities, images, credential isolation, auth/TLS, rate limits, broker budgets and cancellation fencing. No startup-only, periodic or TTL reuse of an approval verdict.
- Keep release files and receipts immutable, all artifacts/temp on E:, owner data private, and running production available during preparation. If a later approved test window starts a stopped station, restore stopped state. Model-pod/OS/dependency maintenance is separate from application activation.

## Approaches and recommendation

1. **Fresh batching plus reduced process setup — recommended.** Targets roughly three seconds of observed median host/setup overhead. Fresh batching already has evidence of useful savings; session reuse has meaningful lifecycle/security work to prove.
2. **Further scoring/kernel tuning alone.** Retain the existing best scorer, but prioritize whole retrieval profiles: its kernel is only a portion of the roughly two-second retrieval stage. Microsecond improvements alone cannot recover the multi-second gap.
3. **Model/prompt/context or token-release changes.** Excluded from this plan because they change the quality or screening contract and would make attribution harder. Consider a separate proposal only if the fixed-contract target proves unattainable.

Five seconds at p90 is a testable goal, not a promised outcome on this hardware.
Stop and report the measured floor if equivalent optimizations are insufficient.

## Task 1: Establish a trustworthy critical path and workload

**Files:** extend `runtime/mcp_client.py`, `runtime/inference.py`,
`runtime/gateway.py`, `scripts/performance_transport.py`,
`scripts/performance_metrics.py`; add `runtime/latency_trace.py`,
`tests/test_latency_trace.py`, `evals/latency-five-seconds.json` and
`scripts/benchmark_latency.py`. Extend `web/app.js` (the `chat.onsubmit` handler
and streaming/render callbacks); do not alter UI layout or conversation persistence.

**Interface:** `LatencyTrace.mark(name: str) -> None` and
`LatencyTrace.snapshot() -> dict` provide bounded, allowlisted monotonic offsets
and a server-generated trace ID. Cross-process spans retain their own durations;
never subtract unrelated clocks. No prompt, credential or source body in public
diagnostics. Existing timing fields and API responses remain compatible.

- [ ] Read the frozen request path and locate actual HUD handlers before edits. Record request admission/queueing, fresh collection versus validation, child/import/handshake, retrieval components, broker admission, first nonempty model content, release-boundary wait, output gate and transport/render durations. Retain numeric model prompt-evaluation/generation metadata only where actually available.
- [ ] Add failing tests for monotonic/overlapping spans, missing events, byte bounds, redaction, unchanged public API and tracing-on/off output equivalence. Prove tracing adds less than 1% overhead in an identical-output fixture; live samples alone cannot establish its cost.
- [ ] Implement tracing and an owner-only plan-by-default harness. Pin runner/workload/source/config/model identities; retain partial failures and interrupted/identity-changing runs as invalid. No arbitrary server/executable input or production bypass switch.
- [ ] Pin 20 qualification cases: the unchanged existing eight plus 12 fixed multi-turn cases (four each Home Assistant, Cyber Coach and mathematics). Across the extra cases include short, medium and long histories, follow-up arithmetic, anti-repetition, stability pushback and uncertainty/provenance. Record actual token sizes after generation; freeze prompts, weights and scoring rubric before comparison. This is a qualification mix, not an assertion of actual usage frequencies.
- [ ] Obtain a fresh baseline after the scoped startup correction, including a complete running-service inventory. Earlier tests did not isolate historical-container startup overhead. Measure cold observations separately. Report per-case and pooled first-text p50/p90/p95, complete response, failures, and per-answer longest-gap median/p95.
- [ ] Run focused trace/metrics/API tests and document the measured critical path. Preserve the existing 398-test baseline and four skips as historical evidence; do not assume future counts.

**Gate:** A bounded timeline explains where first approved text is delayed, without double-counting stages. No optimization proceeds based solely on the older aggregate medians.

## Task 2: Requalify fresh batched security collection

**Files:** `runtime/isolation.py`, `runtime/isolation_probe.py`,
`tests/test_isolation.py`, `tests/test_isolation_snapshot.py`; owner replay fixtures
under the new ignored E: run directory. Use the earlier experiment as reference,
not a wholesale checkout or promotion of `ddf716...`.

- [ ] Write failing tests for equivalent acceptance/rejection, partial/reordered observations, bounded read/timeouts, invalid images/mounts/OCI/network/pod/infra/source and changed state between consecutive requests. Both collectors must reject the same tested tamper classes before a model call.
- [ ] Implement only fresh bounded read-only observation batching. Keep host policy, per-request fingerprint and all validators; never cache a pass or relax a check to reduce cost.
- [ ] Separate collection time from validation time. Run differential known-state and in-memory mutation fixtures plus the real sealed behavioral isolation probes. Preserve reviewed scan findings.
- [ ] Replay identical safe model frame sequences with original boundaries/gates to isolate collector effects from generated-answer variation. Compare the approved byte sequence, release decisions and cadence. Then run a balanced live pilot against the baseline.
- [ ] Stop on a reproducible pacing regression. Diagnose model frames versus screening versus host scheduling; do not alter chunk boundaries or declare the earlier pacing failure harmless simply because generation code is unchanged.

**Gate:** Same tested security decisions, exact replay output, fresh checks, no pacing regression beyond the declared threshold, and a useful real reduction. Otherwise retain the production collector.

## Task 3: Evaluate fixed local MCP session reuse

**Files:** `runtime/mcp_client.py`; if feasible add `runtime/mcp_session.py`
and `tests/test_mcp_session.py`; extend `tests/test_mcp.py`,
`tests/test_model_switch_regressions.py` and `tests/test_streaming.py`.

**Proposed boundary:** one gateway-owned fixed local stdio session, one active
chat request, bounded lifecycle and explicit close. No new network listener,
container privilege or model route. Do not invent an SDK reuse API: first verify
the installed SDK's actual lifetime/async ownership and cancellation behavior.

- [ ] Produce a read-only lifecycle design covering the current event-loop-per-call wrapper, rate-limit state, persona/history/skill separation, progress routing, EOF, cancellation and update/model-switch ownership. If safe reuse cannot be expressed with supported SDK APIs, stop this task with evidence.
- [ ] Add failing tests: full fresh preflight before every call; session bound to release/container/source identity; a changed or failed check closes it before inference; identity/model changes between preflight and dispatch remain held by the broker; no cross-request history/progress; one active request; unchanged limiter policy, explicitly checking its formerly process-local counters; cancellation reaches a confirmed broker idle fence; EOF/timeout closes state without an automatic duplicate inference retry.
- [ ] Implement only after the lifecycle design is reviewed. Keep instruction/resource approval fresh inside the long-lived server, and invalidate on release/model transition or failed verification. Prove release draining closes the session before cutover and old HUD requests remain compatible.
- [ ] Benchmark first-session and reused-session costs separately. Include repeated requests, idle intervals, model switching and stale source/container negatives. Reuse a transport, never an authorization verdict. Preserve no-direct-inference-fallback behavior.

**Gate:** The actual measured setup saving is useful and every lifecycle/security regression passes. A faster handshake with weaker freshness, cancellation or rate limiting is rejected.

## Task 4: Optimize only the remaining measured CPU bottleneck

**Files:** profile-owned portions of `runtime/knowledge.py`, `runtime/retrieval.py`,
`runtime/retrieval_worker.py`, `runtime/dlp.py` and their existing tests; any new
owner profile harness stays under `scripts/` with fixed inputs and no runtime bypass.

- [ ] Profile fresh database/embedding checks, mapping/opening, semantic/rerank calls, continuation reads, IPC copies, output-boundary wait and DLP separately. Identify whether time is CPU, scheduling, I/O or waiting for a complete approved sentence.
- [ ] Select at most one measured, dominant duplicate operation for each candidate: request-local verified handle reuse, bounded batching or reduced copying. Each candidate gets a failing equivalence/tamper/cleanup test before implementation.
- [ ] Require identical selected evidence, original passage bytes, prompts and filter decisions on replay. Live reference differences caused by the existing rerank deadline remain a quality confound, not permission to skip candidates or lengthen/shorten budgets silently.
- [ ] Keep unchanged output-release rules. If the remaining floor is model generation or the security-required release boundary, report it; do not release unapproved partial text to pass the stopwatch.

**Gate:** A material critical-path saving with established equivalence. No new C/assembly work without a profile demonstrating that this is where milliseconds are being lost.

## Task 5: Qualification, frozen preparation and production decision

- [ ] For each component pilot use four balanced alternating measured rounds after one excluded warmup per case/arm. Keep components independently revertible. Only combine components that pass their own gates; do not run the entire qualification matrix for a rejected pilot.
- [ ] Freeze the final protocol before running it: 20 cases, ten measured rounds per arm split as five in each of two sessions, one excluded warmup per case/arm/session. This is 200 measured calls per arm plus 80 warmups. Preserve every attempt; no retry-until-pass or silent pooling. Report order/session effects and small per-case tail-sample limits.
- [ ] Require p90 <=5.000 seconds in both sessions and pooled qualification, with >=90% of legitimate attempts delivering first approved text by five seconds. Report p95, all failures and each case/history bucket; expose slower buckets rather than hiding them in the aggregate.
- [ ] Require every legitimate benign qualification request to complete successfully, with no unexpected refusal, truncation, timeout or empty answer. Expected attack/containment refusals are verified separately and never relabeled as successful latency samples.
- [ ] Require no >10% increase in either median or p95 of per-answer longest approved-chunk gap, and no >5% p90 complete-response regression against the matched baseline. Any triggered investigation gets one predeclared confirmation only, with both receipts retained; unresolved results mean no promotion.
- [ ] Review every measured answer with the five existing 0-2 rubric dimensions, blind A/B labels where practical. Compare source bodies and selected instruction hashes, not just IDs. Require no new material factual/security error and no unresolved per-case quality decline. Known baseline arithmetic/stability defects stay explicit. AI review is labeled as such and cannot establish blanket human-validated correctness; unresolved quality blocks the claim.
- [ ] Run all applicable local tests, ten UI contract suites, broker prompt pins, companion contracts, complexity with unchanged allowances, fresh review, frozen preparation, isolation probes and complete security scans. Retain the 11 reviewed findings and any new finding for disposition, not suppression.
- [ ] Build from the selected frozen payload plus only approved optimization hunks. Exclude inactive Skills/collector payloads and unrelated main changes unless separately scoped. Stage and prepare through `scripts/releases.py`; never edit active payload/pins/receipts. Verify prepared integrity and a rollback path before presenting the production decision.
- [ ] Candidate HTTP/HUD measurements require a separately authorized staged activation: drain/readiness/automatic restoration, owner LAN login, actual submit-to-render check, auth rejection and offline denial checks. No unprotected second gateway or listener to bypass that boundary. Describe port rebinding honestly.
- [ ] After authorized activation, monitor passive local timing for at least 100 legitimate requests across two sessions. Preserve overall and per-history/first-after-idle distributions. Compare available timings/quality with the declared workload; a synthetic result is qualification evidence, not an established production SLO. Roll back on security/lifecycle regression or a confirmed target/quality/pacing failure. Stop any temporary window in its original state if not activated for continued use.

## Decision and handoff

Recommended order: **instrumentation → fresh collector → safe MCP reuse → only
then remaining CPU work → qualification → separately authorized activation**.
Planning estimates for component savings are hypotheses, not additive guarantees.
The greatest uncertainty is tail latency after the unavoidable checks and first
approved sentence, particularly with longer histories and shared GPU workloads.

Native implementation is recommended because tracing, session ownership and
release draining share one lifecycle contract. A fresh review follows integration.
This request only creates the plan: no runtime edit, benchmark, service startup,
new release, commit/push or activation is performed by writing it.

## Self-review and highest-risk checks

Coverage: timings/workload (Task 1); collector equivalence/pacing (2); identity,
cancellation, state and limiter isolation (3); evidence/output equivalence (4);
quality, repeated tails, real HUD/security, availability and rollback (5).
The five main rejection cases are stale transport authority, unconfirmed
cancellation, cross-request state, deadline-sensitive evidence drift and measuring
unapproved/status text as a response. Each has an owning gate above. Persistent
session feasibility is an explicit experiment with a stop condition, not an
assumed supported feature. No five-second claim is made before the evidence.
