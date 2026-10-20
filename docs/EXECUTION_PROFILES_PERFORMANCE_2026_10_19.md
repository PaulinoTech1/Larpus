# Secure execution profiles: measurement status

Historical pre-run checkpoint. The completed 300-attempt run, quality review,
stopped-state verification and rejection decision are in the
[2026-10-20 acceptance report](EXECUTION_PROFILES_PERFORMANCE_2026_10_20.md).
The outstanding list below records the earlier checkpoint, not current status.

The modular implementation is in the checkout. **No new live latency, speedup,
quality-equivalence or production-readiness claim is made.** Production remains
the separately selected frozen release. The owner raw benchmark is not a secure
comparison and is never reachable through the profile selector.

## Implemented instrumentation

Diagnostic records child-local input/retrieval/model-selection/first-model-text/
first-approved/completion points, cumulative gate time/count and maximum approved
release gap. Gateway admission wait is a separate host-local duration. Existing
MCP preflight/connect/total fields remain separately labeled. Durations overlap;
do not sum nested values. Nonstream generation cannot establish first-token time.

Browser Diagnostic uses a monotonic clock for first DOM update and a frame
opportunity stored as numeric reply-element dataset fields. Neither HTTP arrival
nor a frame callback proves physical screen paint. Rendered acceptance is pending.
No prompts, answers, credentials or evidence text enter the numeric trace.

## Reproducible harness

`scripts/benchmark_execution_profiles.py` creates a manifest by default, without
operating services. Example from the project root (use new directories):

```powershell
python scripts/benchmark_execution_profiles.py --session 1 --output data/execution-profiles/run-a
```

`--run` requires an already prepared compatible secure gateway in an authorized
service window. The command does not start, deploy or activate it. The owner
loopback route is fixed to `http://127.0.0.1:8080`, redirects/proxies are disabled,
and explicit profiles reject host inference fixtures. Current frozen releases
without the served execution receipt cannot qualify.

For a prepared candidate, pass `--release-id ID` and operate its isolated owner
gateway during the scoped window. This pins that candidate's frozen sources and
checks its served receipt while also recording the unchanged production selection;
it never changes `active.json`. Candidate preparation/readiness and gateway
startup are separate owner maintenance actions, not effects of the collector.

Run sessions 1 and 2 with the same seed/model/scorer/corpus/security inputs and
separate warm-ups, then combine only their completed receipt directories:

```powershell
python scripts/benchmark_execution_profiles.py --session 1 --output data/execution-profiles/combined --combine data/execution-profiles/run-a data/execution-profiles/run-b
```

The full schedule is 300 measured requests plus six warm-ups. With the default
16-second minimum start spacing it takes at least about **82 minutes** excluding
preparation and unusually long responses. Existing broker limits are unchanged;
budget or request failures are counted rather than retried until success.

Report mean, median, p95, p99, sample standard deviation, minimum/maximum, HTTP
first-approved text, completion, longest chunk gap and failures. P99 at 100 samples
is descriptive. Per-profile summaries in individual sessions do not meet the
100-attempt requirement; only a validated combined schedule can do so.

## Outstanding acceptance

- Prepared candidate scope must exclude unrelated inactive changes, with reviewed
  scanner receipts and service-state restoration before a live run.
- Actual generated-answer review against `evals/execution-profiles.json` rubric;
  HTTP success is not task success or factual accuracy.
- Contemporaneous stock-power CPU/GPU/memory telemetry and logging-overhead
  characterization. `--telemetry` can read Windows host CPU/memory counters and
  `nvidia-smi` GPU boundary snapshots (temperature, clock, power, memory and
  utilization), without changing settings. Missing data stays unavailable. It
  records collection time separately; run matched logging-on/off controls before
  attributing overhead. It does not measure CPU temperature/effective clocks or
  container-specific utilization; those still need contemporaneous HWiNFO data.
- Additional cold/cache/history/queue scenarios must be reported separately from
  the fixed sequential workload; no uncontrolled cold-cache claim.
- Mean and p95 first-visible target below five seconds, unchanged quality/security,
  and the existing maximum-gap median/p95 pacing gate (10% regression ceiling).
- Real rendered HUD/LAN acceptance and separately authorized activation/rollback.

Until these checks run, retain the current production setup. See the
[engineering report](architecture/engineering-report.md) and
[module contracts](architecture/module-contracts.md) for source/test evidence.
