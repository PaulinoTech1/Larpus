# Chat latency investigation - 2026-10-16

The owner requested a shorter delay between submitting a prompt and receiving a
reply, including using more CPU work where beneficial. Measurements below are
local synthetic probes, not browser, microphone, LAN or sustained-load results.

## Evidence

The original active release was `9d76eed753ad4ec9901c8b988e961248`.
The initial fresh greeting returned headers in 0.010 seconds, first checked text
in 18.829 seconds and completed in 19.716 seconds. Later warm-model greeting
probes reached first checked text in 5.535, 5.341 and 5.857 seconds (median 5.535).
The cause of the initial slower observation was not established; it must not be
presented as an improvement caused by the patch.

An instrumented owner-side probe inside the existing sealed agent measured
0.233 seconds importing inference, 2.066 seconds retrieving five references,
0.636 seconds from starting the model stream to its first frame, and 2.857
seconds from entering inference to the first checked chunk. A separate full MCP
probe measured 1.793 seconds preparing the child, connection at 3.002 seconds,
first checked text at 5.680 seconds, and completion at 6.681 seconds. These are
different requests; their timings must not be added as an exact decomposition.

## Bounded change

Read each inspected container's OCI configuration concurrently, using at most
four CPU-side threads. Every request still performs current source-fingerprint,
deployment, container, OCI, network, capability, mount and model checks. A failed
read rejects preflight; no integrity decision is cached and no filter is removed.
The GPU model and persistent CPU retrieval/voice services retain their settings.

Three paired live preflights against the same running deployment:

| Implementation | Run 1 | Run 2 | Run 3 | Median |
| --- | ---: | ---: | ---: | ---: |
| Sequential OCI reads | 2.881 s | 1.644 s | 1.646 s | 1.646 s |
| Concurrent OCI reads | 1.507 s | 1.273 s | 1.332 s | 1.332 s |

This demonstrates a 0.314-second median reduction in this preflight component
(19%). It does not establish the same percentage improvement for whole replies.
Model prefill, evidence retrieval, conversation length, queue contention and
waiting for a complete screened sentence remain additional latency sources.

Three alternating baseline/candidate MCP requests, sharing the existing model,
returned HTTP-equivalent tool status 200 throughout. Baseline first checked text
was 5.660, 5.793 and 5.640 seconds; candidate was 6.695, 5.045 and 5.082 seconds.
Medians were 5.660 versus 5.082 seconds: 0.578 seconds (10.2%) lower for this small
greeting sample. The slower first candidate observation remains in the sample.
These measurements start at MCP invocation and exclude HTTP/browser/speech; they
do not establish a tail-latency guarantee. Numeric receipt:
`data/latency-mcp-paired.json` (ignored owner data).

A separate three-pair library-question sample (two-sentence AES-GCM explanation)
did not reproduce a whole-request improvement: baseline median first checked text
was 6.762 seconds and candidate median was 7.182 seconds. All six requests
succeeded with four references each. These small, variable samples do not prove
a general text-latency reduction; only the paired preflight component measurement
isolates the changed operation. Receipt: `data/latency-knowledge-paired.json`.

The owner clarified that first text, rather than speech startup, is the priority.
An exploratory voice-threading change was removed from the checkout and excluded
from the release. The separate voice experiment did not modify serving code or
replace its model, worker, profile, or dependencies.

`python scripts/benchmark-chat-latency.py --repeats 3` measures local HTTP headers,
first checked text and completion for fixed fresh greeting conversations. It
prints only numeric results and scope, never generated text. Runs use real
inference and may compete with an interactive user.

## Validation and rollout

The added regression first failed without concurrent reading, then passed with
the implementation. It checks actual overlap, stable result ordering and failure
propagation. All six isolation tests pass. A separate candidate source directory
based on the frozen active payload passed the complete isolated suite: 221 tests,
two skipped. The unrelated checkout's existing study-notes complexity failures
were left untouched.

The candidate includes only `runtime/isolation.py`, `tests/test_isolation.py` and
the timing script changes relative to the active payload. Its staging source also
includes the matching owner research catalog needed to verify existing provenance;
the frozen metadata was neither rebuilt nor changed. Initial staging rejected
the source without that catalog, leaving production untouched.

Candidate `5e8e07aab85b4484855be3af26c24b20` passed preparation: application and HUD
contracts, isolation probes, exact MCP discovery and all 70 complete static targets.
The 69 skill targets were clean; the MCP inventory retained the exact 11 reviewed
warnings. This is regression screening, not an independent audit or a clean MCP
scan. The original gateway, model and voice remained running during preparation.

The prepared-release live broker harness passed: synthetic background inference
was preempted, chat completed successfully in 6.797 seconds after preemption,
and synthetic notes resumed successfully. This is a scheduling check, not an
ordinary first-text benchmark. Receipt: `data/latency-broker-live.json`.

Activated `5e8e07aab85b4484855be3af26c24b20` through the updater, retaining
`9d76eed753ad4ec9901c8b988e961248` for rollback. Activation succeeded without an
automatic rollback. Gateway listeners briefly rebound; this was not zero downtime.
LAN sessions need another login, while the existing HUD conversation stays in
its tab. Model and selected CPU voice containers retained five-day uptimes and
were not restarted or replaced. The owner notes writer was already stopped and
was not started by this work.

After activation, three local HTTP fresh-greeting requests reached first checked
text in 5.974, 4.940 and 4.747 seconds (median 4.940 seconds), versus the earlier
production sample's median 5.535 seconds. That is 0.595 seconds (10.7%) lower for
this small sample, not a guarantee for arbitrary questions or idle conditions.
The initial slower post-activation observation is included. All streams completed.
Receipt: `data/latency-http-after.jsonl`.

Station-health required checks pass; overall status remains degraded for the
retained static warnings. Local persona access returned 200 and CA-verified LAN
access without authentication returned 401. Numeric health/uptime receipt:
`data/latency-activation-health.json`. No physical browser, microphone,
second-device, sustained-load, or actual rollback acceptance was performed.

Rollback remains `python scripts/releases.py rollback`; no commit or push was
requested or performed. Unrelated working changes remain in the main checkout.
