# Assembly scoring and NumPy

The HUD **Retrieval pipeline** selector switches among **Assembly optimized**,
**Assembly original**, and **NumPy** without changing the model or clearing the
conversation. Choose a pipeline, then press **Switch pipeline**. The choice is
station-wide and applies between serialized retrieval operations. Assembly
optimized is the startup default when its pinned pool loads. If that load or a
later score fails, the worker uses NumPy and leaves Assembly original selectable
when that backend loaded. The choice lasts until the retrieval service restarts.
It does not reload the GPU model.

Assembly optimized is a separate sleeping four-worker C pool. It calls the same
half-precision assembly kernel as Assembly original and scores a 2 MiB aligned
copy of the matrix. Loading succeeds only when anonymous huge pages back that
copy. The extra resident matrix is about 55 MiB plus alignment to the next 2 MiB
boundary. Its cutoff guard also sends duplicate-row ties to NumPy. Assembly
original keeps the earlier guard and falls back only for close distinct rows.
NumPy still performs top-k selection. The API and context format are unchanged.

The status shows the selected available pipeline and whether the last query used
NumPy. An unsupported CPU, a missing or mismatched native artifact, missing
huge-page backing, or failed startup validation makes that Assembly choice
unavailable. A scoring failure disables the selected Assembly backend and uses
NumPy. Near-tied references may change order. Close selection cutoffs use NumPy;
this safety path is counted in status rather than presented as an Assembly speedup.

The measurements below, through the 2026-10-18 activation, describe Assembly
original. The optimized module is checked separately before a release is prepared.

## Measurements and limits

The [Windows experiment](NATIVE_ASSEMBLY_EXPERIMENT_2026_10_18.md) showed a roughly
1.9× kernel speedup. That result did not establish a Linux application speedup.
The first strict Linux implementation demonstrated the cost of preserving
rankings:

| Isolated Linux measurement | NumPy | Assembly pipeline with safety checks |
|---|---:|---:|
| Score median across eight query medians | 2.817 ms | 5.143 ms |
| Neighbors median, including query embedding | 13.317 ms | 16.042 ms |

These measurements used the active frozen corpus, an eight-CPU isolated
network-disabled container, eight requested native-library threads, and four
Assembly workers. Scoring used 60 measured interleaved repetitions per fixture
query after five excluded conditioning rounds. Neighbors used 24 measured
observations per pipeline after a conditioning pass. All eight fixture rankings
and 128 additional random query rankings matched after safety checks. A previous
raw Linux comparison found one ordered top-18 mismatch in 128 random queries,
zero top-18 membership mismatches, and maximum absolute score error
`5.960464477539063e-08`. The owner subsequently approved near-tie reordering.

The guard uses a conservative float32 reduction-error margin around top-ranked
scores and falls back to the original NumPy scorer for ambiguous distinct rows.
Exact duplicate rows are grouped separately. The guarded run recorded 678
ambiguity fallbacks across conditioning, scoring, random-validation and neighbors
calls. This is a correctness-oriented implementation, **not a demonstrated speed
optimization**. That strict release used NumPy by default. Finite comparisons are not
a universal proof of bitwise or rank equivalence.

### Approved near-tie policy, 2026-10-18

The revised pipeline permits interior near-tie reordering and checks only the
selected-set cutoff. Its margin is `2e-6 * max_row_norm * query_norm`, an empirical
tolerance rather than a universal floating-point error bound. Startup checks and
the benchmark verify numeric tolerance and top-18 set equality. Unseen queries
can still change membership; the finite validation does not prove otherwise.

| Linux run | NumPy scoring | Assembly scoring | Reduction |
|---|---:|---:|---:|
| First | 3.212 ms | 2.205 ms | 31.4% |
| Repeat | 3.120 ms | 2.145 ms | 31.2% |

Both runs used the same eight fixtures, 60 measured interleaved repetitions per
fixture, five excluded conditioning rounds, and 128 seeded random queries. All
checked top-18 sets matched and neither run triggered the cutoff fallback.
The raw scores are allowed to differ within validated tolerance. Four persistent
Assembly workers and eight requested BLAS threads share the same eight-CPU test
limit; the host's 20-logical-CPU WSL cap is unchanged.

Neighbors medians were 13.376/12.476 ms (NumPy/Assembly) and 26.068/13.654 ms.
The large run-to-run spread makes those embedding-inclusive results noisy.
Use the repeatable scoring result for the approximately 1 ms CPU saving claim.
Do not extrapolate it into a chat time-to-first-text gain.

A previous strict-policy HTTP preview completed 24/24 replies, with nine measured
samples per mode after conditioning: first-text medians were 6.296 s for NumPy
and 6.661 s for strict Assembly. That small sample showed no end-to-end speedup
and does not measure the revised policy. Spot checks also found both pipelines
violated a requested two-sentence limit in the norms fixture; no answer-quality
percentage or citation-entailment guarantee is claimed.

Near-tie receipts:

- `data/assembly-linux-build/43d32bc42d2f4758a4401c6fe062b866/report.json`
- `data/assembly-linux-build/b8abfbb1d9af4a29a85306afdd463611/report.json`
- Raw comparison: `data/assembly-linux-build/ce72d813dbde495d915a7d79408a0ac6/report.json`
- Strict HTTP comparison: `data/assembly-linux-build/preview-report.json`

Owner-local receipts:

- `data/assembly-linux-build/e25ea371e0e54b92bab91ff528ae2827/report.json`
- `data/assembly-linux-build/af845cfcbbc341eea4af4236cb0a7eea/report.json`

## Build and integrity

The maintained kernel is `runtime/native/score_half.S`; the checked Python adapter
is `runtime/native_scoring.py`. The library has no runtime compiler, download,
OpenMP dependency or model access. `scripts/build-assembly.py` builds it with an
owner-side Linux Zig 0.17.0 toolchain:

```powershell
python scripts/build-assembly.py
python scripts/benchmark-assembly.py --run
python scripts/test-local.py
node tests/pipeline-ui.cjs
```

The toolchain download was SHA-256 checked against the
[official Zig distribution index](https://ziglang.org/download/index.json).
It lives outside the station image and shared runtime dependencies.
`runtime/native/manifest.json` records the artifact/source hashes and compiler.
The adapter verifies artifact size and SHA-256 before loading it and checks CPU
features and startup numerical/ranking probes. Native source, manifest and binary
are included in the scan integrity fingerprint and frozen release payload pins.
Native Python adapters enter the static scan input; assembly received a scoped
manual ABI/bounds review. Neither fact establishes an exhaustive native-code audit.

An ordinary application release packages the pinned library through the existing
`COPY runtime/` image step. Model, voice, authentication and bindings are unchanged.
Owner controls remain behind the gateway's authentication and origin checks and
are not added to the model's MCP tool inventory.

## Availability and release scope

The release candidate is based on the active frozen payload plus only the pipeline
implementation, tests and owner helpers. `releases.py stage --source PATH` permits
this scoped staging while retaining the existing owner data/vendor junctions and
release store; unrelated working changes are preserved. A research catalog copy
was needed only in the staging source to reproduce the existing provenance check;
the frozen corpus and its metadata were not rebuilt.

The first candidate was superseded to include native artifacts in the security
fingerprint. Its preparation descendants were identity-checked before cancellation;
partial scan evidence was retained, and production was not stopped. Strict release
`af473bce74b842a9aa3e42f6c23f3afd` was prepared and activated successfully.
Its availability receipt verifies unchanged model/voice IDs, images and start
times, functional health, authenticated LAN controls, and live switching. The
existing 11 reviewed MCP scan warnings remain; activation needed no rollback.

The near-tie revision was prepared and activated separately as
`d604dfcd7ebd4c0199cdec395b6c61cf`. All 70 scan targets completed, retaining the
same 11 reviewed MCP warnings and no skill warnings. The isolated checkout suite
passed 312 tests with two skips; candidate preparation also passed its required
tests, UI suites and isolation probes. Scoped review found no blocker.

Activation completed successfully without rollback. The entire activate command
took 26.167 seconds, including validation, drain, readiness and pruning; this is
not measured port downtime. Post-activation checks verified Assembly startup,
NumPy/Assembly switching, CA-validated unauthenticated LAN controls returning 401,
and unchanged model/voice container IDs, images and start times. All functional
health checks passed; the retained scan warning keeps overall health degraded.

A live greeting succeeded and reported `last_used=assembly`, with zero cutoff
fallbacks and 7.434 seconds to first text. This single smoke sample proves a
working reply path, not a latency improvement. Evidence is in
`data/assembly-linux-build/fast-availability-before.json`,
`fast-availability-after.json`, `fast-activation.json` and `fast-prepare.log`.

Activation is a brief gateway cutover rather than zero downtime; LAN sessions
need a fresh login while the existing HUD retains its transcript and draft.
Save/export before refreshing to load the selector. The active choice is Assembly.

The [cache and dispatch follow-up](ASSEMBLY_CACHE_TUNING_2026_10_18.md) records
small additional scoring gains, rejected prefetch/alignment experiments and
CPU-quota limits; it does not establish a chat latency improvement.

The separate [1 ms experiment](ASSEMBLY_1MS_EXPERIMENT_2026_10_18.md) tested
ten handwritten variants and held-out workloads. It missed the target and
retained the deployed implementation; tied-duplicate reference limits are recorded.

The [hardware counter profile](HARDWARE_COUNTER_PROFILE_2026_10_18.md) now
measures grouped PMU events and replicated working-set sensitivity. It leaves
production unchanged and separates memory-hierarchy evidence from silicon-quality claims.

## Assembly optimized, 2026-10-19

Assembly optimized is the startup default in this checkout when its pool loads
and anonymous huge pages back the aligned matrix. Assembly original and NumPy
remain selectable. The repeat warm-scoring median was 1.888 ms versus 2.910 ms
for NumPy, about 35% less scoring time, with a 56 MiB huge-page reservation
(about 54.7 MiB of matrix payload). Correctness, limits, and the stopped-station
receipt are in the [module check](ASSEMBLY_OPTIMIZED_2026_10_19.md).

Prepared candidate `341de68e12974563ab8da85c370542cc` is not active. Its
knowledge index is the consistent index from the active release. Activation
remains a separate cutover.
