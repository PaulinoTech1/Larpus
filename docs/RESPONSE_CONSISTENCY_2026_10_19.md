# Response consistency follow-up - 2026-10-19

**Decision: do not promote this candidate.** First text is faster, but the independent pacing confirmation did not meet the registered consistency criterion. Current release `7df2e957751642d6ace4630fa047fe94` remains selected. Candidate `ddf716bcc1f04df891de7545f2052b64` is prepared and retained for diagnosis, not activated. The working checkout also retains the original preflight as its default; the experimental collector helpers/tests remain available.

## Results

The main experiment used four fixed cases (greeting, norms, scalar ODE pushback, SOC advice), six measured rounds each, alternating backend order after one excluded warm-up round. Both versions used Assembly optimized, the same Larpus 3.8 GPU model, context, sampling, prompts, corpus, budgets and screening.

| Main experiment, 24 requests per version | Existing | Candidate |
|---|---:|---:|
| First approved text median | 5537.4 ms | 4795.9 ms |
| First approved text sample p95 | 7087.3 ms | 6140.6 ms |
| Complete response median | 7167.8 ms | 6344.5 ms |
| Per-answer longest chunk gap median | 806.0 ms | 852.4 ms |
| Per-answer longest chunk gap sample p95 | 1551.9 ms | 1737.8 ms |

First text improved **13.4 percent at both median and sample p95**; all four case medians improved. All 48 calls succeeded; all 24 paired source records matched exactly. These timings include the actual Windows MCP preflight, connection, retrieval, generation and approved output callbacks, but exclude browser painting, HTTP admission and initial module import. p95 is nearest-rank from a small sample, not a production SLO. Requests are warm, short conversations; long histories and loaded-system/cold-start tails are not established.

Main-run stage medians: preflight **1502.3 to 670.8 ms**, retrieval **1845.8 to 1826.8 ms**, MCP connection **984.7 to 1031.9 ms**, model first frame **519.0 to 533.1 ms**. This localizes the main saving to security-collection transport.

The pacing p95 exceeded the pre-registered 10 percent investigation threshold. Only one paired generated answer was byte-identical; mathematical prose/citations dominated the largest gaps. Normalizing individual gaps by character count did not remove the difference, so chunk size alone is not an adequate explanation. The separate median post-first character-delivery rate rose from 122.9 to 152.0 chars/second; it is not GPU token throughput and does not prove shorter pauses.

## Independent pacing confirmation

Before running a second experiment, registered one narrower confirmation in `pacing-confirmation/confirmation-design.json`: norms and scalar ODE cases, six measured rounds each, opposite backend ordering, same warm-up exclusion. No retries until passing; do not silently pool it with the four-case headline. Require no more than a 10 percent rise in both median and p95 of the per-answer longest approved-chunk gap.

| Confirmation, 12 requests per version | Existing | Candidate |
|---|---:|---:|
| First approved text median | 5880.3 ms | 5017.1 ms |
| First approved text sample p95 | 7429.0 ms | 6102.9 ms |
| Longest chunk gap median | 1046.5 ms | 1195.8 ms |
| Longest chunk gap sample p95 | 1980.3 ms | 2107.7 ms |

All 24 confirmation calls succeeded, and all 12 evidence pairs matched. First text improved again, but median maximum gap increased **14.3 percent**, failing the criterion; p95 rose 6.4 percent. Across both experiments: **72 measured successful calls, 36/36 identical evidence pairs**. There is no established causal link from the collector to the pacing differences, because generated text differs and generation/screening code is unchanged. There is also insufficient evidence to call pacing maintained or improved. The safe decision is to retain the current default and investigate generation-versus-screening timings with comparable output before promotion.

## Implementation and security evidence

The experimental collector replaces six WSL launches with one fresh read-only program. It still probes distro isolation, rootless Podman information, container identities, exact OCI files, pod and infra state. Host policy checks and per-request source fingerprint verification remain. No cached verdicts, persistent transport, listener, output-buffering changes, reduced screening, model/prompt/budget changes, overclock or power adjustment.

Candidate source was copied from the frozen active release. Exactly three payload files differ: `runtime/isolation.py`, new `runtime/isolation_probe.py`, and new `tests/test_isolation_snapshot.py`. Unrelated checkout/GitHub changes were excluded. After the failed pacing confirmation, the checkout's default `preflight` was restored byte-for-byte at function level to the existing implementation; snapshot helpers are experimental and unused by that default. The frozen candidate was not modified.

Preparation passed local/companion/UI/isolation checks and all 70 scan targets, retaining the same 11 reviewed MCP findings. Fresh focused tests passed **18 tests**, including malformed/partial/reordered observations, bounds, subprocess/timeout failure, no caching, distro exposure and OCI limits. Complexity checks passed without changing allowances. A scoped independent code review found no important findings; it used mocked data and did not operate services.

A diagnostic replay of actual fresh state then individual in-memory mutations gave matching decisions: valid acceptance and 20 rejections covering privilege, filesystem, ports, resources, image/user, namespaces/network, OCI privilege/capabilities and model parallelism. No real security settings were mutated. These tests are bounded evidence, not an exhaustive audit. LAN TLS certificate verification and unauthenticated API rejection (401) also passed.

An exploratory 20-pair component comparison gave preflight median **1578.2 to 712.0 ms**, p95 **1822.6 to 774.0 ms**, standard deviation **127.0 to 44.3 ms**. That run overlapped startup recovery/pruning; alternating order limits but does not eliminate load confounding. The main response experiment waited until preparation and recovery finished.

## Availability and artifacts

Production remained on the frozen current release throughout candidate preparation and tests. The initial temporary startup hit the previously observed cold-model readiness fault; an idle model load/verification, faulted-broker restart and pruning recovered it. Full GPU placement at context 131072 was verified. That cold-start fault is not claimed fixed. No activation, binding/authentication change, model/voice image replacement, dependency update or power adjustment was made.

The gateway and all LARPUS containers are stopped, and the Larpus WSL distribution is terminated, verified by `shutdown/completed.json` and a fresh running-distribution inventory. The notes task remains disabled. All build, test, temporary and receipt paths are on E:, including the E:-backed WSL disk. Repository publication does not activate this candidate.

Private reproducibility artifacts: `E:/speedzone_MS/LARPUS/data/latency-consistency-20261019/`. Key files: `experiment.json`, `decision.json`, `source-manifest.json`, `profile_preflight.json`, `preflight-comparison.json`, `security-equivalence.json`, `paired-consistency-manifest.json`, `paired-consistency-report.json`, `consistency-summary.json`, `delivery-diagnostic.json`, `pacing-confirmation/`, `lan-auth-check.json`, `shutdown/`. Raw answers/source records are owner data. Copy the harness into a new run directory before rerunning so original receipts are not overwritten.
