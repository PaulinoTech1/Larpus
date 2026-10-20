# Verified concurrent observations

Status: screening complete. Prepared `306986ac3d954e7791b2b7a3028838e2` was
not activated. No five-second claim.

## Approved bounded change

Verified overlaps three independent fresh reads: distro policy, Podman host
information and container inspection. Once container identities are known, OCI
configuration reading overlaps the dependent pod/infra inspection chain. A
request-local pool has at most three workers. It joins outstanding reads on exit;
failure at any stage rejects, without a cached or alternative allow verdict.
All existing isolation validators still run before the MCP child is launched.
Ultra Fast's separate snapshot path is unchanged.

Diagnostic exposes numeric initial/namespace-read phases, child import duration
and retrieval base/notes/provenance/engine/neighbors/rerank spans. Import duration
is computed once per child; extra request spans are enabled only for Diagnostic.
Timings do not contain prompts/evidence or determine approval. Broken timing
storage/clock tests preserve the underlying operation's result or failure.
Child import time is nested within connection startup; retrieval spans overlap.

Model, prompts, sampling, evidence budgets, deadlines, DLP, authentication, broker
quotas and stock power settings are unchanged. No persistent MCP session, early
inference or reduced screening was added. The 20-processor ceiling is retained.

## Offline evidence

- Checkout: 465 tests, four skips,196.170s; process exit0. Eight new overlap,
  rejection, fresh-read and timing tests passed after observed red failures.
- Narrow source: 360 tests, two skips,138.372s; process exit0. It excludes
  unrelated inactive checkout features. Its own complexity and original broker
  prompt checks passed;429 chat hashes and18 notes hashes remain unchanged.
- Root complexity passed without increasing existing allowances. Required
  cross-profile faults and exact approved-byte replay remain in the suite.
- Original owner files and selected release7df2 are preserved. No commit/push.

Receipts and candidate scope: `data/verified-latency/`. The first corrected
snapshot `90ab2aa349b74747930d591f9521ab5e` reached scan and stopped: the
scanner counts five direct `isolation.py` subprocess calls instead of six,
because the unchanged distro probe is now `pool.submit(subprocess.run, ...)`.
The prepared candidate `306986ac3d954e7791b2b7a3028838e2` records that exact
count. The other reviewed warnings stay. No finding was deleted from the code.

## Screening protocol and limits

Before measurements, eight existing Home/Cyber cases were fixed, one balanced
round across Verified, Ultra Fast and Diagnostic (Verified base), seed5900,
three excluded warm-ups and at least16s spacing. Telemetry and owner-only answer
capture are identical. All24 attempts, including failures, are retained. The
owner collector extends only the older numeric-stage allowlist to capture new
diagnostics, recording its own hash. It does not alter frozen runtime behavior.

This screening is not the100-attempt/profile acceptance run. Historical timings
from the earlier report have a different sample population and time window;
they cannot establish a causal speedup. No quality parity or browser/LAN timing
is inferred. A failed screen does not justify resampling until passing. The
temporary owner-loopback station is restored to its initial stopped state.

The first window failed before preparation while the local model was starting;
a bounded read-only readiness probe now precedes warm-up. Preparation later
rejected a copied newer prompt and an unused inactive import. The mutable source
was corrected against the frozen baseline; rejected snapshots stayed frozen and
were not activated. No benchmark answers existed in those failed attempts.

## Screening result

One balanced round, seed 5900, completed at 10:50 UTC. Each profile had eight
measured attempts. Verified failed once on `home-uncertainty` (`ValueError`);
that attempt stays in the denominator. Ultra Fast and Diagnostic had no failures.

HTTP first-approved seconds, successes only:

| Profile | Attempts / failures | Mean | Median | P95 |
| --- | ---: | ---: | ---: | ---: |
| Verified | 8 / 1 | 5.394 | 4.961 | 7.917 |
| Ultra Fast | 8 / 0 | 4.845 | 4.596 | 6.391 |
| Diagnostic, Verified base | 8 / 0 | 6.704 | 7.186 | 7.838 |

Every p95 is above five seconds. Quality is unreviewed. This is not the
100-attempt acceptance run and does not promote a profile. Selected release
remains `7df2e957751642d6ace4630fa047fe94`. The temporary station was stopped,
including model, voice and Larpus WSL.

Receipts: `data/execution-profiles/verified-screen-20261020-306986ac/`.
See the [earlier 100-attempt/profile baseline](EXECUTION_PROFILES_PERFORMANCE_2026_10_20.md).
