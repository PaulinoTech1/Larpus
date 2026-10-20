# One-millisecond Assembly experiment, 2026-10-18

The owner approved a separate experiment targeting approximately 1 ms median
full-index guarded scoring, with p95 also reported and checks beyond the
existing fixed benchmark. The deployed implementation is retained as baseline;
this experiment does not authorize weakening ranking checks or reducing the
index. All experimental code and artifacts are throwaway private probes under
`data/assembly-linux-build/`, not product runtime changes.

## Setup and profiling

Frozen baseline: `f08b98ea2f34407cb77dc79aa7d7866a`. Every probe loads that
release's runtime and image into a separate network-disabled, read-only CPU
container, with eight-CPU quota and 12 GB memory. WSL's 20 logical processor
limit and model/voice settings remain unchanged. Kernel build uses the existing
owner preparation toolchain, not an executable from downloaded reference data.

The full index is 74,709 by 384. There are 73,880 distinct vector rows: only
1.11% duplicates. Deduplicating avoids little computation while adding a scatter
back to the original row order. Preliminary profile values below are separate
measurements, not additive timings or a controlled end-to-end comparison.

| Profile component | Median ms | p95 ms |
|---|---:|---:|
| numpy | 2.421 | 3.194 |
| guarded | 1.583 | 1.855 |
| wrapper | 1.430 | 1.693 |
| cutoff | 0.134 | 0.187 |
| dedup_wrapper | 1.425 | 1.736 |
| dedup_guarded | 1.552 | 1.853 |
| scatter | 0.056 | 0.074 |

The cutoff alone is approximately 0.13 ms in this probe; most time remains in
scoring/dispatch. Deduplication did not offer a meaningful path to the target.
`dedup_guarded` includes compact scoring, scatter and cutoff; `scatter` is an
isolated indexing proxy. This does not prove a hardware memory-bandwidth limit.

## Handwritten kernel sweeps

Six transposed row-tile variants (8/16/32/64 rows, varied accumulator counts)
were tested with the existing empirical cutoff guard. The best fixed-fixture
median was tile32p3, 1.754 ms versus baseline 1.806 ms, a small 2.9% saving.
A second sweep kept row-major storage and processed 2/3/4/8 rows together;
all four variants were slower than baseline. No candidate reached 1 ms.
These sweeps select candidates; they are not acceptance evidence.

| Sweep | Mode | Guarded median / p95 ms |
|---|---|---:|
| transposed | numpy | 2.839 / 16.592 |
| transposed | baseline | 1.806 / 2.481 |
| transposed | tile8p4 | 1.806 / 2.332 |
| transposed | tile16p4 | 1.784 / 2.408 |
| transposed | tile32p1 | 1.782 / 4.002 |
| transposed | tile32p2 | 1.785 / 2.180 |
| transposed | tile32p3 | 1.754 / 2.389 |
| transposed | tile64p1 | 1.797 / 2.383 |
| row-major | numpy | 2.848 / 3.699 |
| row-major | baseline | 1.847 / 2.342 |
| row-major | row2p4 | 1.932 / 8.220 |
| row-major | row3p4 | 2.030 / 9.024 |
| row-major | row4p2 | 2.032 / 5.264 |
| row-major | row8p1 | 1.954 / 2.817 |

The transposed layouts pack exact binary16 values once before timing, and
return scores in original row order. Dimensions and short row groups are
zero-padded, not discarded. Startup packing cost and extra resident memory
are not hidden as free production benefits; no runtime path is installed.
Row-major variants amortize query loads without repacking. Every candidate
still uses four persistent Python executor workers and the existing cutoff.

## Independent checks

The candidate selection fixtures are separate from eight held-out learning,
SOC, governance, pentesting and performance questions. Acceptance diagnostics
also exercise 1,024 normalized random queries with a new seed, ten synthetic
matrix shapes (including odd dimensions, small/empty matrices and twice the
current row count), retained-output ownership, cache-pressure preparation,
embedding and reranking preparation, and actual `Engine.neighbors` calls.
Median/p95 and raw samples are retained. Non-saturated comparisons pause 100 ms
before preparation, outside timers. A 128 MiB strided pressure buffer is a
cache-pressure proxy; no hardware cache-miss counters are collected.

The first held-out run stopped on a top-18 set mismatch, after numeric scores
passed tolerance. Its stderr and exact runner remain at
`one-ms-5259c41c5ebf43b2bd7e1afe71e42c10/`. The diagnostic continuation records
mismatches and duplicate-group information as failures instead of silently
waiving them. The continuation does not convert a failed candidate to a pass.

## Private receipts and reproduction

- `one-ms-2731cbbda1d4472cadffe482d7dd332e/report.json`: component/duplicate profile.
- `one-ms-1e4b0a6abc654fc29ce93e71dd701bfc/report.json`: six transposed kernels.
- `one-ms-582c36f2d7144794a4e6a3a6fb456cf5/report.json`: four row-major kernels.
- `one-ms-kernels/`: generated assembly, build manifest and experimental binary.
- `one_ms_build.py`, `one_ms_run.py`, `one_ms_make_accept.py` and generated
  runners: owner-only throwaway reproduction code, not deployed commands.

Each completed run directory includes the frozen runtime archive, exact runner,
experimental binary where used, stdout/stderr and JSON report. Candidate
numeric checks use atol 2e-6 / rtol 2e-5; reference-set checks are recorded
separately. Finite random/shape tests do not prove universal equivalence.

## Held-out outcome: target not achieved; retain deployed version

Completed diagnostic receipt:
`one-ms-12516b477ab24189a90a9d15b54645e8/report.json`.

All values below are median / p95 guarded scoring milliseconds. Two
conditioning rounds per case/condition/backend are excluded; measured rounds
per held-out case are warm 10, pressure 8, embedding 8 and reranking 4.

| Condition | NumPy | Current Assembly | tile32p3 | tile16p4 |
|---|---:|---:|---:|---:|
| warm | 2.766 / 3.439 | 1.850 / 2.399 | 1.852 / 2.274 | 1.836 / 2.331 |
| pressure | 3.316 / 3.871 | 2.300 / 2.842 | 2.285 / 2.843 | 2.291 / 2.840 |
| after-embedding | 3.004 / 3.532 | 2.004 / 2.349 | 2.070 / 2.301 | 2.028 / 2.362 |
| after-reranking | 2.964 / 3.300 | 2.128 / 2.482 | 2.064 / 2.802 | 2.052 / 2.359 |

The leading fixed-fixture tile32p3 improvement did not generalize to a distinct
held-out win: warm scoring is effectively unchanged, embedding is slower,
pressure is marginally faster and reranking median is faster with worse p95.
Tile16p4 is also mixed. No 1 ms full-index median was obtained. The current
implementation remains the preferred deployment. No repeat was needed to reject
promotion: the first held-out run already misses the stated target and does
not demonstrate a distinct improvement.

CPU quota counters recorded zero throttled periods in all these paced condition
samples. This does not remove scheduling noise or establish a cache-miss cause.
Synthetic shape timing loops were unpaced and did not collect per-sample quota
counters; they are diagnostics, not an equivalent latency/scaling comparison
with the paced table. Sub-millisecond timings on smaller matrices do not count
as meeting the full-index target.

Actual `Engine.neighbors` calls (embedding, guarded scoring, top-k and row-ID
mapping) returned identical reference sets across all four modes for the eight
held-out texts. Median durations across those eight single calls were:

- numpy: 8.589 ms.
- baseline: 7.527 ms.
- tile32p3: 7.670 ms.
- tile16p4: 7.625 ms.

These single calls per text/mode are a smoke comparison, not a reliability or
p95 estimate. Their backend order was fixed, so they do not establish a causal
latency change. The candidate medians are slower than current Assembly here.
This is retrieval-only timing, not complete chat first-text latency.

### Correctness findings and limits

Numeric comparisons completed for 1,024 random queries and ten matrix shapes;
maximum observed absolute score error versus NumPy was 1.1921e-7. All 3,092
retained-output comparisons passed. Both experimental candidates used the
NumPy ambiguity fallback once during random-query checking.

Exact reference-set agreement was not universal: tile32p3 differed on one
random query (251), and the current Assembly baseline differed on one other
query (671). In both examples every changed row has an identical score and
belongs to the same exact-vector duplicate group as the exchanged row. The
NumPy partition can choose different tied row identifiers when other scores
change slightly. There was no observed distinct-vector-group difference in
these recorded examples. Tile16p4 had no set mismatch in this finite run.

This finding is retained as a strict reference-set check failure, including for
the baseline; it is not relabeled as a pass. It shows the previous finite tests
were not proof of universal row-identifier equivalence. A future explicit
deterministic tie policy would require a separate behavior change and review;
no ranking/fallback policy is modified in this performance experiment.

### Artifact and availability evidence

Experimental binary SHA-256:
`dec92f5fabe0510d3dcfc5d2e67a4176c1c02433370a80331c2acd96d2b438e5`.
Exact held-out runner SHA-256:
`bc6a288474afb10b4ee07bf18a3cb650230adea6000de9c847c285e9d04fa2d3`.

The active release remains `f08b98ea2f34407cb77dc79aa7d7866a`. Mid-experiment
and final read-only snapshots (`one-ms-availability-before.json` / `after.json`)
match active release, model/voice container IDs/images/start times and working
scorer/kernel/manifest hashes. The gateway still answers status and Assembly
remains selected. Model and voice start times also match the earlier deployment
receipt. The WSL configuration still says `processors=20`. No gateway activation,
service stop, dependency change, index rewrite, production selector change,
commit or push was performed for this experiment.

No new full application test-suite claim is made: this task changes documentation
and private throwaway probes only. The completed experiment includes failed
checks and rejected candidates, not a new production implementation. The owner
can retain these receipts to evaluate a different algorithm later without
confusing them with the current selectable Assembly pipeline.
