# Verified chat latency plan — 2026-10-21

Status: candidate `03959f0891764772a962726bea4309d7` is the active release.
The new numeric spans are in that release. Local HTTP run
`d182403674014c49864903d66d49bfa6` completed 27/27 measured requests:
first checked text median 6.548 s and nearest-rank p95 9.829 s. The target
is not met. Two identical follow-up runs, `5c971d911b884ffda3bf9594350b0d74`
and `aedae3f8a7644709a75b9071b3092068`, also completed 27/27 measured
requests and reported median/p95 of 5.901/7.106 s and 5.925/6.767 s.
No code, model, retrieval setting, or release change occurred between them.
The slow first run had model-first-frame p95 4.248 s, versus 1.232 and 1.239 s
in the follow-ups. Retrieval medians were 1.936, 1.897 and 1.893 s. The
reason for the transient model delay is unknown. These small runs have pending
answer review and are not a tail guarantee or a matched release A/B test.
All three runs used identical active release, model-weight, retrieval-config,
database, embedding-manifest and notes-manifest receipts; no setting was relaxed
to obtain the two faster results. Two `cyber-soc` measured replies, one in the
first run and one in the third, reported an unknown citation identifier. Three
subsequent retained-answer probes of that case reported no unknown identifiers,
but their answers do not explain or clear the earlier anomaly. Their first-text
times were 16.911, 7.460 and 5.628 s, so first-after-idle/model variability
also remains open. Do not claim whole-system quality or durable tail improvement
from the faster runs alone.
Preserve production while developing and measuring candidates; activation
remains a separate release decision.

## Goal and boundary

For the active release's default Verified-equivalent chat path, reach a warm local
HTTP median time to first **approved, nonempty** text of at most **5.9 seconds**
and p95 of at most **6.8 seconds**, as clarified by the owner. Report completion
time and first-after-idle separately.
Measure actual HUD submit-to-render time on the owner's LAN as a separate result.

Keep the current model and weights, 131072-token context, sampling, prompt and
evidence budgets, source selection rules, approved-output boundary, auth/TLS,
DLP, fresh isolation checks, broker limits, CPU/WSL settings and voice behavior.
Do not count an acknowledgement, raw token or partial unapproved sentence as
first text. Do not trade reply quality or chunk pacing for a faster timestamp.

## Baseline and assumptions

The earlier frozen release was `b6dffca22d244953acb3a8574c232e69`; the
current active release is `03959f0891764772a962726bea4309d7`. The earlier local
suite run `ca24874be39540b2a4770626cb1a3887` was stable: 24/24 measured
requests completed after eight excluded warm-ups. First checked text was 6.389 s
median, 7.409 s p90, 7.795 s nearest-rank p95 and 9.135 s maximum. Completion
was 8.152 s median and 9.983 s p95. No measured request reached first text by
five seconds. The first warm-up took 18.129 s to first text. A 24-request p95 is
descriptive and unstable; this run alone cannot qualify a production tail target.

| Assumption | Status | Impact if wrong | Validation |
| --- | --- | --- | --- |
| Median ceiling is 5.9 s and p95 ceiling is 6.8 s | Confirmed by owner | None | Use in qualification |
| Warm fixed prompts represent useful common chat | Unverified | Good synthetic result may not help daily use | Add fixed multi-turn/longer-history cases and LAN HUD measurement |
| Host setup is reducible without weaker checks | Unverified | Optimization may stall or weaken isolation | Trace critical path and differential security tests |

The measured medians for fresh preflight, MCP connection and retrieval were
1.528 s, 1.001 s and 1.926 s. They are timing scopes, not an additive latency
budget. The selected active path already batches OCI reads, while distro, host,
container, pod and infra observations still have dependent or sequential work.
The earlier single-collector experiment improved a narrower latency sample but
failed its independent chunk-pacing check; the later concurrent Verified screen
also failed one of eight requests and did not establish a five-second tail.
Neither candidate should be copied into production wholesale.

## Steps and gates

1. **Freeze a better baseline and critical-path trace.** Working-checkout
   instrumentation now records fresh collection, namespace reads, validation,
   retrieval substeps, and child-import time on Verified and Diagnostic.
   Ultra Fast does not take that path. Detail stages are optional in summaries:
   a missing sample stays null, and the original stage set still defines a
   complete sample. `home-longer-history` is a fixed five-message case. The
   suite records the gap before each probe and summarizes first text only when
   that gap is at least 16 seconds. The live trace that explains the slow p95
   cases is still open. The running release `03959f08` contains these
   spans. The remaining gate is a trace on that active release that contains
   these spans. That trace still has to separate request admission, broker or
   model first content, approved-sentence release, and HTTP delivery for the
   slow cases. It must use request-local clocks and must not log prompts,
   passages, or credentials. Stage timings have to explain the slow p95 cases,
   not only the median.
2. **Evaluate the activated fresh-preflight overlap.** Release `03959f08` already
   overlaps independent distro policy, Podman host and container reads while
   preserving dependent reads and validators. Compare its full HTTP latency,
   output quality and pacing to the earlier release before claiming a benefit.
   A separate overlap candidate `4a982cd7ad7448ecba3f14d777314364` was
   prepared before this activation and must not be activated over the newer
   release. Its component timing is not whole-reply evidence.
3. **If the target still misses, evaluate MCP startup cost.** The active client
   creates a fresh stdio MCP connection per call. First verify the installed
   SDK's lifecycle and async ownership. A reusable local session is admissible
   only if preflight and source approval remain fresh per request, request state
   cannot leak, cancellation and broker idle fencing work, and a changed release,
   container or model closes it. A fresh connection may be used only before a
   request is dispatched, after fresh preflight; do not retry an uncertain or
   partially streamed inference. Never fall back to direct inference. If those
   contracts cannot be proved, retain the current session lifecycle.
4. **Profile residual retrieval/model delay.** Only optimize a measured duplicate
   read, copy or wait. Require identical selected source bodies, prompt bytes,
   output gates and approved chunks on replay. Keep rerank deadlines and model
   settings fixed. If model generation or the approved-sentence boundary is the
   remaining floor, report it rather than weakening that boundary.
   In the active HTTP run, retrieval median was 1.936 s, including 1.452 s
   `retrieval_base` and 0.494 s `retrieval_notes`; preflight and MCP connection
   medians were 1.005 s and 1.022 s. The 4.7 ms `retrieval_engine` median
   measures engine lookup only, not ONNX reranking. `retrieval_rerank` is not
   exposed in this HTTP summary, so its live contribution remains unknown.
   A disposable eight-CPU, batch-four sweep found that raising ONNX threads
   from 8 to 12 reduced median retrieval time by only about 35 ms while scoring
   8 rather than 12 candidates under the 0.9 s deadline and changing top-five
   results. Sixteen threads was slower and scored 8; the 20-thread arm reached
   the disposable container's 64-process limit. Keep the active eight-thread
   setting; these results do not support a thread increase.
5. **Qualify the candidate before activation.** Run matched baseline/candidate
   requests through the same fixed local MCP transport in balanced order across
   two sessions, with at least 100 measured attempts per arm and excluded warm-ups.
   Preserve failures in the denominator; report p50, p90, p95, completion and
   longest approved-chunk gap overall and by case/history bucket. Require a
   useful first-text improvement, no unexpected failed/empty/truncated answers,
   no material answer-quality or source-support regression, and no >10% increase
   in median or p95 longest chunk gap. Review retained answers against original
   passages; citation IDs alone do not establish claim support. MCP timing is a
   candidate gate, not proof that candidate HTTP or browser timing meets target.
6. **Prepare a frozen release, then decide on activation.** Build from the
   selected frozen payload plus only passing optimization hunks. Run focused and
   broader tests, UI/API compatibility, isolation probes, prompt pins, complexity
   checks and complete release scans; retain warnings. Stage and prepare via
   `scripts/releases.py` without editing active files or interrupting the live
   gateway/model/voice. Present the prepared ID, diff, receipts and rollback path
   for the production decision. After any separately authorized activation, run
   the same fixed HTTP suite on the active candidate in two sessions with at
   least 100 measured attempts total and excluded warm-ups. Require median
   <=5.9 s and p95 <=6.8 s in each session and pooled; repeat the answer/pacing
   checks on this path. Verify LAN auth, live HUD timing, health, model placement
   and rollback readiness. Roll back for a confirmed security, quality,
   reliability or timing gate failure. A brief gateway rebind and LAN re-login
   are expected limitations.

Primary evidence: `data/evals/performance/ca24874be39540b2a4770626cb1a3887/`;
earlier failed/pending experiments are described in
`docs/RESPONSE_CONSISTENCY_2026_10_19.md`,
`docs/VERIFIED_LATENCY_2026_10_20.md`, and
`docs/EXECUTION_PROFILES_PERFORMANCE_2026_10_20.md`.
