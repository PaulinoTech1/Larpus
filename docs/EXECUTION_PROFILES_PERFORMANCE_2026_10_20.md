# Secure execution profiles: measured acceptance

2026-10-20. **Faster, but not accepted for production.** Ultra Fast reduced mean
HTTP first-approved text by 14.7%, from 6.703 to 5.718 seconds. Its p95 was
7.980 seconds, so both registered five-second requirements failed. Output pacing
passed the registered comparison. Answer-quality parity remains unestablished.
The candidate was not activated, and the initially stopped station was restored.

## System and procedure

Candidate `dc74ddc8315d4fdaa6349c72fc40bc46` was prepared from selected release
`7df2e957751642d6ace4630fa047fe94` plus 31 explicitly scoped files. Unrelated
inactive MCP Skills, CI overrides, startup and KaTeX changes were excluded.
The selected production pointer never changed. The gateway listened only on
owner loopback, not LAN. No model/voice image, dependency, binding policy,
authentication policy, broker quota, sampling, retrieval deadline or power
setting was changed. The existing 20-processor WSL ceiling was retained.

The frozen candidate's harness ran 20 fixed short/medium cases, five rounds and
three profiles, with balanced seed 5900 and at least 16-second start spacing.
Session 1 covered rounds 0/2/4; session 2 covered 1/3. Each invocation had three
excluded warm-ups. Three earlier smoke calls were also excluded. These are two
sequential invocations, not reboot or controlled cold-cache sessions.

Both sessions used the same LARPUS 3.8 model (`larpus3.8:27b-q4`), Assembly
optimized scorer, corpus, frozen security inputs, telemetry and explicit
owner-only answer capture. Diagnostic used Verified as its base. Per-response
model/source/profile receipts and between-request model/scorer checks were
required; combination validated every scheduled identity and session partition.
The window lasted 88m24s, including smoke, setup and cleanup, from 07:26:58 to
08:55:22 UTC. Preparation took a separate 650.956 seconds.

Original owner-local receipts are under
`data/execution-profiles/live-20261020-dc74ddc8/`: session manifests/rows,
`combined/report.json`, `state.json`, `cleanup-verified.json`, blinded review
files/scores, `acceptance-analysis.json` and `resource-analysis.json`.
The acceptance thresholds were saved before measurement in
`data/execution-profiles/acceptance-design.json`. These data files remain ignored
by Git; completed answers are separate from ordinary numeric diagnostics.

## First approved text

Seconds, successful responses only. Failures remain in the attempt denominator;
they are neither zero-filled nor retried. P99 at this sample size is descriptive.
This measures HTTP text arrival, not physical browser paint, voice or LAN timing.

| Profile | Attempts / failures | Mean | Median | P95 | P99 | Sample SD | Min / max | Under 5s / attempts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Verified | 100 / 3 | 6.703 | 6.214 | 9.045 | 9.989 | 1.371 | 4.974 / 10.291 | 1 / 100 |
| Ultra Fast | 100 / 0 | 5.718 | 4.994 | 7.980 | 8.607 | 1.396 | 4.008 / 9.208 | 51 / 100 |
| Diagnostic, Verified base | 100 / 2 | 6.602 | 6.054 | 8.788 | 9.671 | 1.319 | 4.893 / 10.655 | 2 / 100 |

Ultra Fast's unpaired mean reduction was 0.985s (14.7%); median reduction 19.6%
and p95 reduction 11.8%. In the 97 pairs where both Verified and Ultra Fast
succeeded, mean delta was -1.007s and median delta -0.928s. Paired delta SD was
2.072s, and some individual cases were slower (maximum delta +2.912s). This is
an improvement on this workload, not consistent sub-five-second production.
Diagnostic's paired mean delta was -0.100s and median +0.006s; stochastic output
variation prevents treating that as negative instrumentation overhead.

All five failures occurred on `home-uncertainty`: Verified rounds 1/2/3 and
Diagnostic rounds 3/4. The frozen collector retained a generic `request_failed`
classification, not an underlying error diagnostic, so their cause is unresolved.
No quality scores or timing samples were invented for these missing answers.

## Completion and output consistency

| Profile | Completion mean / median | P95 / P99 | Sample SD | Min / max |
| --- | ---: | ---: | ---: | ---: |
| Verified | 10.227 / 8.603 | 20.610 / 22.800 | 4.307 | 5.321 / 24.212 |
| Ultra Fast | 9.265 / 8.129 | 18.298 / 24.207 | 4.209 | 4.233 / 26.707 |
| Diagnostic | 10.185 / 8.636 | 21.826 / 26.409 | 4.387 | 5.191 / 27.391 |

| Profile | Per-answer longest gap mean / median | P95 / P99 | SD | Min / max |
| --- | ---: | ---: | ---: | ---: |
| Verified | 0.803 / 0.740 | 1.632 / 1.817 | 0.418 | 0 / 1.911 |
| Ultra Fast | 0.805 / 0.679 | 1.605 / 1.876 | 0.425 | 0 / 1.948 |
| Diagnostic | 0.799 / 0.673 | 1.627 / 1.783 | 0.402 | 0 / 1.878 |

Ultra Fast/Verified longest-gap ratios were **0.918 median and 0.983 p95**, below
the registered 1.10 ceiling. Diagnostic ratios were 0.910 and 0.997. The main
pacing gate passed, so no conditional confirmation run was needed or performed.
This does not establish pacing under concurrency, long history or LAN rendering.

## Answer quality

One profile-blind agent assessed every successful answer, using the existing
five 0-2 dimensions and case-specific review points. Profile labels remained
withheld until scoring finished. There were 295 unique assessments across 20
cases, with no duplicated or missing successful-answer scores. This is an agent
rubric review, not human verification, statistical equivalence or certification.
Available source previews were incomplete; unresolved support was distinguished
from demonstrated falsehood.

| Profile | Scored | Accuracy | Grounding | Uncertainty | Usefulness | Instruction following | Critical flags |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Verified | 97 | 1.495 | 1.711 | 1.464 | 1.784 | 1.670 | 4 |
| Ultra Fast | 100 | 1.530 | 1.740 | 1.500 | 1.680 | 1.740 | 3 |
| Diagnostic | 98 | 1.551 | 1.684 | 1.500 | 1.714 | 1.684 | 5 |

Ultra Fast's all-scored usefulness mean was 0.1035 lower than Verified, beyond
the registered 0.1 ceiling. The matched-success comparison gives -0.0928, within
the ceiling, but omits three failed baseline answers. Both are reported; the
pairing population was not changed to obtain acceptance. There were no additional
Ultra Fast critical flags within those 97 matched pairs, but one critical answer
had no successful baseline counterpart. Its parity is unknown. Diagnostic had
five newly flagged critical answers within matched pairs. Quality acceptance is
therefore **not established**, even though several mean dimensions improved.

The 12 critical flags included dismissing vulnerability findings after failed
reproduction, validating alert closure on false positives alone, incorrect
validation metrics, contradictory time budgets, misleading stability claims and
claiming Task Manager provides historical CPU temperature. Recurring lesser
issues included citation overextension, requests for unsanitized logs, excess
length and incomplete uncertainty. These are model-answer problems, not evidence
that a profile bypassed application security. They also do not establish that
the faster observation method caused the answer differences.

## Attribution and hardware limits

Median stage durations (milliseconds) were:

| Stage | Verified | Ultra Fast | Diagnostic |
| --- | ---: | ---: | ---: |
| Fresh preflight | 1727.545 | 730.253 | 1744.086 |
| MCP connection | 1081.059 | 1082.519 | 1075.013 |
| Retrieval | 1963.395 | 1960.742 | 1963.552 |
| Model first frame | 295.712 | 258.447 | 271.629 |
| Child first checked text | 3161.433 | 3071.409 | 3021.668 |

These overlap and have different clock origins; do not sum them as exclusive
costs. The roughly 997ms median preflight reduction is consistent with much of
the paired improvement. MCP startup and retrieval remain substantial measured
costs. No ordinary-chat second-model evaluator was found to disable.

Available telemetry covered 295 successful requests and 590 GPU boundary
snapshots. Host CPU averaged 37.1% (range 26.0-51.9%). GPU boundary temperature
ranged 47-68C, clocks 1920-2055MHz, power 109.92-449.95W, and observed power limit
remained 450W. VRAM used ranged 22,763-23,892MiB out of 24,564MiB. Boundary samples
can miss peaks and do not establish thermal throttling, CPU temperature/effective
clocks, per-container attribution or silicon quality. No contemporaneous HWiNFO
CPU log was incorporated in this run. Stock settings were retained; no tuning
or overclock was performed.

Telemetry acquisition averaged 169ms/request (median 141ms, p95 256ms, maximum
2.398s), recorded separately and outside the HTTP first-text timer. All profiles
used identical collection. An offline alternating synthetic Trace control ran
10,000 exercises/mode: disabled mean 3.11 microseconds, enabled 34.60 microseconds
for ten constant gates. This isolates wrapper overhead only. A live model
logging-on/off control was not run; its cache/scheduling effects remain unknown.

## Security, readiness and handoff

All profiles retain the same shared mandatory validators and release gates.
Ultra Fast gathers fresh observations in one bounded launch; it caches no allow
verdict. Selected per-profile mutation, storage, scanner/evidence, cancellation,
truncation and optional-component tests support that contract. They are bounded
tests, not an exhaustive hostile-system assessment. The existing lexical DLP and
citation-ID checker do not prove semantic safety or claim entailment.

Preparation completed 70 scan targets, retaining the same 11 reviewed MCP
warnings: two HIGH DockerSocketAccess, seven MEDIUM subprocess, one LOW skill
permissions and one LOW getattr. None was suppressed. The earlier snapshot
`9ed01f211b8a44598a19f4e7058a9059` was rejected at a diagnostics UI harness check;
it stayed frozen and was superseded, never activated. No activation or rollback
was attempted. The live candidate returned to stopped state with no remaining
containers; external checks found no running WSL instance and no listeners on
8080/11434. The notes task remains Disabled and selection remains `7df2...`.

**Decision: retain production; do not promote this experiment.** Latency failed,
quality parity is unresolved and browser/LAN acceptance remains untested. The
prepared candidate and original receipts remain available. Commit/push and
activation were not performed. Any later activation must revalidate prepared
status and use the updater, with LAN re-login and brief port rebinding disclosed.
See [engineering evidence](architecture/engineering-report.md),
[module contracts](architecture/module-contracts.md) and
[update procedure](UPDATES.md).
