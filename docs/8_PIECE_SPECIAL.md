# 8 piece special

Status: separate local Verified-latency experiment; no new runtime profile,
deployment, or production configuration change. The name identifies the
existing eight-CPU-thread, rerank-batch-four setup. Iterate here without
folding unqualified timing changes into the broader Verified release plan.

## Frozen starting point

- Active release at creation: `03959f0891764772a962726bea4309d7`.
- Retrieval: 8 ONNX CPU threads, batch 4, 0.9-second rerank deadline,
  10 BM25 candidates and 6 semantic candidates. Keep the approved corpus,
  embedding index, model weights, security checks and output gate fixed.
- Private evidence and future scratch work belong under the ignored
  `data/8-piece-special/` directory. The frozen release is a reference, not
  an editable workspace. Stage any future implementation as a new release.
- The earlier `data/verified-59/` preflight candidate is separate and must
  not be activated over this newer release.

## Starting measurements

Local HTTP Verified first checked text; each run had 9 excluded warm-ups and
27/27 successful measured requests. These are sequential sessions on the same
active release, not a controlled A/B or a long-run tail guarantee.

| Run | Median | Nearest-rank p95 | Retrieval median | Model first-frame p95 |
| --- | ---: | ---: | ---: | ---: |
| `d182403674014c49864903d66d49bfa6` | 6.548 s | 9.829 s | 1.936 s | 4.248 s |
| `5c971d911b884ffda3bf9594350b0d74` | 5.901 s | 7.106 s | 1.897 s | 1.232 s |
| `aedae3f8a7644709a75b9071b3092068` | 5.925 s | 6.767 s | 1.893 s | 1.239 s |

The active release, model-weight, retrieval-config, database, embedding and
notes receipts matched across the three runs. No setting change caused the
faster observations. The reason for the first run's slow model first frame
is unknown. A later `cyber-soc` probe took 16.911 seconds to first text, so
first-after-idle behavior still needs controlled measurement.

An offline eight-CPU, batch-four sweep found that 12 threads shaved about
35 ms from median retrieval but scored 8 instead of 12 candidates under the
deadline and changed top-five results. Sixteen threads was slower and also
scored 8; 20 threads hit the disposable container's 64-process limit. Keep
8 threads until a new quality-preserving candidate proves otherwise.

Two `cyber-soc` replies across the three runs reported an unknown citation
identifier. Three subsequent retained-answer probes reported none, but did
not resolve the earlier anomaly. Answer quality and source support have not
been certified from these timing receipts.

## Iteration contract

1. Record a concrete hypothesis and the exact code/config delta under this
   experiment before running a candidate. Change one measured bottleneck at
   a time; keep the active release serving.
2. Compare against this frozen starting point with the same fixed prompts,
   excluded warm-ups, full success denominator, stage scopes and local HTTP
   transport. Inspect first-after-idle separately from warm requests.
3. Reject a speedup that loses rerank coverage, changes selected evidence
   without review, weakens screening or auth, produces unsupported citations,
   worsens approved-chunk pacing, or degrades answer quality.
4. Run the repository's frozen preparation and acceptance gates before any
   activation. Do not report component timings as whole-reply improvement.

The broader target remains median <=5.9 s and p95 <=6.8 s for local first
checked text. Pixel/browser timing is deferred. See
[the broader Verified plan](VERIFIED_LATENCY_PLAN_2026_10_21.md) for release
gates and limitations.

## Fresh-preflight candidate, 2026-10-21

Candidate `b2e0c086017d480f9e360f1dbc6b2a7e` was prepared from the active
frozen payload with only a concurrent fixed-pod/infra observation and its
focused tests changed. It keeps fresh observation, model-to-pod identity and
all downstream validators before inference. The active release was not changed.
The isolated release test suite, UI contracts, isolation probes, complexity
check and scan gate passed. The scan retained the source-pinned existing MCP
warning. A direct run of the full test suite from an unsealed source copy had
two Windows ACL test errors because its source hash did not match the installed
image; the release preparation's isolated test suite passed.

Seven paired observation-only measurements showed preflight collection median
832 ms baseline versus 629 ms candidate. This is a component result. The
matched 27-per-arm MCP run `2dbf84fbdf62463b86310b1deca2473c` completed
27/27 in each arm with no unknown citation IDs. First checked text median/p95
was 5.233/6.389 s baseline versus 5.224/6.713 s candidate. That run gave
the candidate 18 first-in-pair positions and baseline 9, so it cannot qualify
the whole-reply effect. The following even-order 36-per-arm diagnostic run
`b2207b2badb445d0a5736e0984ba8a77` was contaminated by concurrent source
work and is not a production timing gate. It reported 36/36 each,
5.218/8.174 s baseline and 5.232/7.314 s candidate. Request order and
model-first-frame variation were larger than the approximately 0.2-second
preflight saving. Candidate activation remains held pending an uncontaminated,
balanced comparison, source-support review, pacing checks and the required
local HTTP qualification. Adding a habit-formation source is separate from this
latency candidate and must not be pooled into these timing receipts.
