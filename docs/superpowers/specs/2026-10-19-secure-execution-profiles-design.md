# Secure execution profiles: proposed design

Status: owner-approved 2026-10-19; checkout implementation underway. Deployment
and live acceptance have not started. Owner explicitly required modularity.

## Intent and scope

Implement the attached comprehensive modularity request incrementally, preserving
local-only operation, existing mandatory checks, answer quality and output pacing.
The production objective is mean and p95 first-visible response below five seconds,
not a promise that current hardware can meet it. Preserve the existing owner-only
raw benchmark as a separate CLI experiment, inaccessible through chat profiles.

The source audit is in [architecture](../../architecture/engineering-report.md).
Its baseline is checkout `64e49c7`, not an assertion that all checkout changes are
active in the selected frozen release.

## Alternatives and recommendation

1. Recommended: a small request context, a shared inference path, and extraction
   of dependency-light integrity hashing. This preserves current authority and
   allows controlled comparisons without another framework.
2. Persistent MCP sessions could remove startup work, but alter rate-limit
   lifetime, cancellation state and source-freshness behavior. Defer to a separate
   lifecycle design supported by measured evidence.
3. A general plugin/router rewrite increases scope without a demonstrated
   bottleneck. Do not introduce it for this task.

## Profile contract

Add an optional strict `execution` request object. Omission means `verified`
profile and `conversation` interaction, preserving old HUD requests. Accepted
profiles are `verified`, `ultra-fast` and `diagnostic`; interaction labels are
`conversation`, `analysis` and `coding`. They grant no capabilities. Reject
unknown fields, unsupported values and all security-bypass, transport, endpoint,
model, budget or permission overrides.

Diagnostic accepts an optional base of `verified` or `ultra-fast`, defaulting to
verified. Other profiles reject a base field. Resolve into an immutable context,
validate at gateway and child boundaries, and propagate through bounded MCP
metadata `larpus_execution`; retain the existing three tool argument contracts.
Client-supplied metadata cannot override the resolved context or trusted policy.

Verified retains current behavior. Ultra Fast uses the same mandatory validators
and protected broker sampling policy, with only fresh batched observations and
measured orchestration reductions. It does not skip evidence screening, DLP,
authentication, isolation, provenance, citation checks or stream release gates.
There is no existing ordinary-chat model critic to disable. If no safe saving is
demonstrated, report that outcome rather than promoting an ineffective mode.

Diagnostic overlays bounded, redacted numeric stage traces on either base.
Never log prompts, answers, credentials, raw evidence or private filesystem paths.
Keep process-local monotonic durations separate; do not subtract unrelated clocks.
Distinguish first model text, first approved text, first browser render and complete
reply. Include queue, preparation, retrieval, generation, gate and release gaps;
identify overlapping measurements rather than adding nested durations together.

## Integrity and authority

Extract pure fresh source hashing into `runtime/source_integrity.py`, preserving
the existing exact path scope, ordering, symlink and size semantics. Keep
`security_scan.fingerprint()` as a compatibility wrapper using its current root.
Isolation imports the pure function instead of scanner/MCP orchestration. No
cached approval or ignored mismatch is introduced. New source requires new
snapshot preparation; frozen pins and receipts remain untouched.

All production profiles use the sealed broker route. Existing explicit owner/CI
host fixtures remain outside the secure production-profile guarantee; no profile
selects that transport. No new listener, broker, executable skill runner or tool
grant is added. Keep full-catalog tamper rejection. Test optional skill removal
through a consistent reviewed registry/persona change, not silent missing-file
acceptance. Preserve quarantine failure behavior and required scheduler fencing.

Do not broadly refactor the worker/owner import cycles. Document broker
anti-repetition marker coupling and preserve its generation options in every
comparison; direct raw benchmark results do not isolate security cost.

## UI and compatibility

Add a small profile selector; label Ultra Fast as security enforced. Interaction
selection remains independent. Default to Verified and preserve unsaved history,
stream framing, replay and existing tabs. No raw-model option appears in LAN chat.
New response diagnostics must be additive and ignored safely by older clients.

## Validation and promotion

First stabilize interfaces with unit tests independent of live services, then
test malformed profiles, security equivalence, optional-component failures,
cross-request leakage, cancellation and incomplete streams. Repeat the full
regression baseline. Test identical-output frame replay before attributing live
pacing changes to orchestration; retain current documented pacing thresholds.
Do not remove complete-catalog checks or shorten retrieval deadlines to win tests.

Measure at least 100 requests per configuration with fixed workload, persona,
model, broker options, corpus and security pins, balanced interleaving and at least
two sessions. Separate warm-up, cold/warm cache, short/long history and queued
requests. Respect existing request/token budgets; do not raise them for throughput.
Report mean, median, p95, p99, standard deviation, min/max, first-visible and
completion latency, failures, task success and response-quality rubric results.
With 100 samples, p99 is descriptive rather than a stable tail guarantee.

Record available CPU/GPU/memory telemetry at stock power with the existing
20-processor ceiling. Keep logs/builds on E:. Correlate clocks and temperature
only where contemporaneous data exists; old HWiNFO logs do not prove new behavior.
Document logging overhead or mark it unmeasured. Reject speedups that degrade
quality, security, or the established output-pacing gate; no repeated tuning of
acceptance thresholds after seeing results.

Stage only reviewed implementation changes through the release updater. Do not
accidentally bundle unrelated inactive checkout features into a candidate.
Preparation is distinct from activation, which requires its own authorized window.
Keep services available if running; the station was stopped at audit start and
must not be started merely for source inspection. An authorized benchmark window
must restore its initial state. Retain scan warnings, failure/rollback evidence
and before/after scores with confidence. No after-score without executed evidence.

## Delivery sequence

Phases 1-2: source reconstruction, contracts, classification and before scorecard
(documented). Phase 3: pure integrity seam and strict context contract. Phase 4:
shared secure profiles and compatible HUD. Phase 5: fault/security regressions.
Phase 6: controlled benchmark. Phase 7: only measured optimizations. Phase 8:
final report with retained limitations and reproducibility instructions.

The written implementation plan follows approval of this design. Performance
failure is a valid measured outcome; it does not authorize security reductions.
