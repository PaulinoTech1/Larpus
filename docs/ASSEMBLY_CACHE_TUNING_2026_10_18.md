# Assembly cache tuning: 5900X, 2026-10-18

The retained change caches the four immutable matrix partition descriptors when
creating the scorer and avoids repeated partition arithmetic and ctypes
pointer lookups on every query. Each query still owns a fresh output buffer. Submitted jobs are
joined even if a later submission fails, keeping input/output buffers alive.
The assembly kernel, NumPy fallback, ranking policy, ONNX settings and four
persistent scoring workers are unchanged. Both pipelines remain selectable.

This is a small dispatch saving, not proof that cold-cache accesses have been
eliminated. No hardware cache-miss counters were available, and no end-to-end
chat latency improvement has been established.

## Hardware and method

Windows reports a Ryzen 9 5900X, 12 cores/24 logical processors, 6 MiB L2 and
64 MiB L3. WSL remains limited to 20 logical processors and 48 GB RAM. Its
virtual topology reports 32 MiB L3; this does not establish physical CCD
placement. The agent and benchmark each retain an eight-CPU quota and 12 GB
memory limit. No affinity or host settings changed.

The production-sized matrix is 74,709 by 384: approximately 54.7 MiB binary16
versus 109.4 MiB float32. Tests use the existing offline models in a separate,
network-disabled, read-only CPU container. Eight fixed Home Assistant/Cyber
Coach cases rotate backend ordering; two conditioning rounds are excluded.
Measured rounds per case/backend: warm 16, pressure 12, post-embedding 20,
post-reranking 6, saturated post-embedding 20. Pressure touches a 128 MiB buffer
at 64-byte strides; it is a proxy, not a guaranteed cache flush.

Paced conditions wait 100 ms before preparation, outside all timers. Saturated
conditions do not. Preparation, scoring and their combined duration are
recorded separately. Warm preparation itself runs the scorer; pressure
preparation touches the buffer. These synthetic totals are not chat timings.
Quota counters cover preparation plus scoring, not individual instructions.

## Scoring results

Diagnostic receipt:
`data/assembly-linux-build/cache-final-49df173742fc48d780d860dc925e97cd/report.json`.
All values below are median / p95 milliseconds; lower is better.

| Condition | NumPy | Deployed Assembly | Cached dispatch |
|---|---:|---:|---:|
| stress-embedding | 3.143 / 26.814 | 2.291 / 31.222 | 2.203 / 26.697 |
| warm | 2.563 / 3.018 | 1.808 / 2.127 | 1.794 / 2.069 |
| pressure | 3.268 / 3.779 | 2.390 / 2.791 | 2.365 / 2.822 |
| after-embedding | 3.044 / 3.586 | 2.118 / 2.535 | 2.066 / 2.433 |
| after-reranking | 3.293 / 3.799 | 2.215 / 2.627 | 2.204 / 2.543 |

Paced median scoring savings versus deployed Assembly are approximately 10-52
microseconds (0.5-2.4%); saturation saves about 88 microseconds (3.8%). Pressure
p95 increases slightly, from 2.791 to 2.822 ms. Differences this small remain
sensitive to scheduling. NumPy comparisons include the existing Assembly gain;
they must not be attributed entirely to this change.

Saturation recorded 39/32/35 throttled periods for NumPy/deployed/candidate.
Paced warm, pressure and embedding recorded none; paced reranking recorded
1/1/0. An earlier unpaced candidate run had a post-embedding p95 of 36.856 ms
versus 2.838 ms deployed. That adverse result is retained at
`cache-final-8de390ec538f4d4589852190dc5d23bf/report.json`. Quota observations
show scheduling pressure is a confounder; they do not prove cache misses caused
the spikes or that this patch fixes throttling. In the diagnostic, saturated
combined preparation/scoring median was 14.041 ms candidate versus 13.595 ms
deployed, despite faster scoring. Overall application throughput is not proven.

## Rejected experiments

- Aligned matrix/query buffers and reusable aligned output followed by a copy
  did not consistently improve total scoring. Fresh caller-owned output stays.
- Software prefetch at several distances showed mixed median/tail results;
  no experimental prefetch kernel is included.
- Reducing ONNX threads or disabling worker spinning reduced some contention
  but made combined inference/scoring slower. The original settings remain.
  ONNX documents this latency/CPU tradeoff in its
  [threading guide](https://onnxruntime.ai/docs/performance/tune-performance/threading.html).

Receipts under `data/assembly-linux-build/`:

- `cache-8772c81c139042f8ad3ca22d639efc20/report.json`: initial variants.
- `cache-2b1f361423924bd2bfe1df7d4b4ce052/report.json`: alignment/prefetch repeat.
- `cache-c52abad7b73e4778b0127422b7c2c0ad/report.json`: isolated no-spin probe.
- `overlap-9dffce81d7f8481295d3780491ea9006/report.json`: interleaved settings;
  combined post-embedding medians 9.800 ms original, 10.742 ms four threads,
  21.906 ms no-spin. Post-rerank: 59.677 / 85.353 / 91.335 ms.

## Correctness and reproduction

Across 1,024 seeded normalized random queries, candidate scores were bitwise
identical to deployed Assembly, retained outputs stayed unchanged, and top-18
sets matched NumPy. Maximum absolute NumPy difference was 8.94e-8. This is a
finite test, not a proof for every possible query. Unit tests cover small/empty
partition ranges, caller buffer ownership and joining already-submitted jobs
when submission fails. The failure-lifetime test failed against the old wrapper
before the fix. The native binary remains pinned to SHA-256
`3cf2fcb2c80a7b0ecdd109e33281d9b55e9b51088c10f1d6321785c1fc3a717f`.

The owner command defaults to a plan and requires explicit execution:

```powershell
python scripts/benchmark-assembly-cache.py
python scripts/benchmark-assembly-cache.py --run --baseline b029d94bfc9b43f8a3ab30c38ddad78a
```

Use the stated baseline after activation to retain the old-versus-new
comparison. The command verifies frozen source/kernel pins and records raw
samples, quota observations, image and source hashes privately. It never
activates a release or restarts the model/voice.

## Maintained-command repeat

The public command completed successfully. Receipt:
`data/assembly-linux-build/cache-final-66b8f9a0782442f8a934dba20fb5ca16/report.json`.
Same wrapper source SHA-256:
`3e59ec32995e826dbbd6120a4e9546e0921d3f463e650a6a598d77bcb2dc7445`;
baseline `db16eb2bea4779567f36774f2f95e3a52f5e4836da1c7e91aab10c677d9cfb07`.

| Condition | NumPy median / p95 ms | Deployed median / p95 ms | Cached median / p95 ms |
|---|---:|---:|---:|
| stress-embedding | 2.975 / 44.711 | 2.115 / 40.045 | 2.058 / 5.495 |
| warm | 2.759 / 3.325 | 1.904 / 2.312 | 1.908 / 2.243 |
| pressure | 3.424 / 3.940 | 2.495 / 2.965 | 2.420 / 2.894 |
| after-embedding | 3.004 / 3.498 | 2.082 / 2.446 | 2.047 / 2.451 |
| after-reranking | 3.207 / 3.988 | 2.194 / 2.553 | 2.228 / 2.685 |

Pressure and post-embedding scoring medians improve in both paced runs
(24-75 and 35-52 microseconds respectively). Warm and post-reranking results
are mixed: this repeat is 4 and 34 microseconds slower respectively. Its
post-rerank p95 is 2.685 versus 2.553 ms. This is not a universal speedup.
Combined embedding/scoring median is slightly slower in both paced runs,
including 9.092 versus 9.038 ms here. The rationale for retaining this bounded
change is cheaper immutable dispatch setup in the pressure/embedding scoring
conditions plus correct buffer lifetime on partial submission failure, not a
claimed overall inference speedup.

Saturation quota events in this repeat are 30/36/30; paced warm, pressure and
embedding have zero; reranking has 0/3/2. The repeated 1,024-query correctness
checks passed with the same 8.94e-8 maximum NumPy difference.

Local isolated suite: 320 tests ran, two skipped, no failures. Complexity gate
passed (542 functions, 83 modules). A helper complexity failure was corrected
before staging by extracting baseline validation into its own function.
Scoped code review found no blockers. Production changes are limited to the
wrapper, buffer-safety tests and opt-in benchmark; unrelated working changes
are excluded. Deployment verification is recorded below after preparation.

The first preparation (55f31e55e08e42f9b578bedb6b5240c3) stopped after 32
scan receipts and remained staged. It was never activated. Its incomplete
receipts are retained; preparation was restarted from the same scoped source
as 08b98ea2f34407cb77dc79aa7d7866a, without altering frozen files or the
active gateway. The retry uses an owner-side hidden process with a persistent
log/exit receipt so chat interruptions do not discard its progress.

## Deployment and availability

Activated `f08b98ea2f34407cb77dc79aa7d7866a` from prepared, validated frozen source. The
only payload differences from `b029d94bfc9b43f8a3ab30c38ddad78a` are
`runtime/native_scoring.py`, `tests/test_native_scoring_buffers.py` and
`scripts/benchmark-assembly-cache.py`. Frozen Python/UI/isolation checks and all
70 scan targets completed, retaining the same 11 reviewed MCP findings. Station
functional checks pass; security-scan warning remains, so overall health is
still degraded for that known reason.

Production remained available during preparation. Model and CPU voice container
IDs, images and start times match before/after snapshots. The selected model
was preserved. Live NumPy-to-Assembly switching, a successful HTTP reply and
CA-validated unauthenticated LAN control rejection (401) were verified after
activation. Assembly is selected. WSL remains capped at 20 logical processors.
No rollback was needed. Activation took 25.837
seconds for the whole command including validation, drain, readiness and
pruning; port-rebinding downtime was not measured and this is not zero downtime.
LAN sessions need fresh login after the gateway process change; backend changes
do not require clearing an already-open conversation.

Private receipts: `cache-source-receipt.json`, `cache-full-tests.log`,
`cache-prepare-retry.log / cache-prepare-retry.json`, `cache-activation.json`, `cache-activation.log`, and
`cache-availability-before.json` / `cache-availability-after.json` under
`data/assembly-linux-build/`. Previous frozen release is retained for rollback.
No commit or push was performed.

Verification limitation: the first post-activation reply probe returned a
non-success observation and tripped the verifier assertion. Its detailed
observation was not persisted by that initial helper, and the gateway log
contains no corresponding diagnostic. A repeat with observation persistence
passed (HTTP 200, first checked text received at 9.699 s, complete at 9.875 s,
Assembly actually used, no unknown citations). This is one successful live
probe after one unexplained failure, not a reliability-rate or latency
improvement claim. Switching, health and authentication assertions passed on
both executions before the reply probe. No service restart was used to obtain
the repeat result.
