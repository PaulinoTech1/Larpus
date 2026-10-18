# C and handwritten assembly experiment — October 18, 2026

The extended Windows experiment found a repeatable scoring gain. Parallel float16-input C and handwritten AVX2/FMA assembly roughly halve vector-scoring time relative to NumPy on the same corpus. This saves approximately 1–1.5 milliseconds in this kernel; no Linux production or prompt-to-first-text gain has been measured. The running station was not updated.

## Implementation

The owner-local source and build artifacts are in `data/native-retrieval-spike-v2/`:

- `native.c`: four independent SIMD accumulators, unrolled loops, bounded static OpenMP row partitions, and float32 or float16 matrix input.
- `dot.asm`: handwritten Win64 leaf routines using AVX2/FMA, with F16C conversion for the half-input variant; scalar tails handle nonmultiples of 32.
- `bench.py`: correctness checks, fixed fixture queries, repeated interleaved timings, BLAS inspection, source/DLL hashes and rank checks.
- `build.cmd`, `sweep.py`, and `run-*.json`: repeatable local build, initial thread sweep and raw observations.

The baseline index already stores binary16 values. The old runtime converts those values to float32 once before scoring; the new half-input kernels read the original values and convert them exactly to float32 in registers, then accumulate in float32. This changes memory traffic, not the stored numerical precision. The harness asserts exact equality between the half-input reconstruction and the existing float32 matrix.

The CPU is the Ryzen 9 5900X. The Windows benchmark process is restricted to 20 allowed logical CPUs before importing numerical libraries, and worker requests cannot exceed 20. WSL remains configured for 20 logical CPUs. No host affinity, service configuration or shared dependency was changed.

Build tools were the already-installed MSVC 19.41 and MASM x64. Flags: `/O2 /arch:AVX2 /openmp /LD`. The exported functions are experimental; they assume valid nonoverlapping arrays supplied by the checked owner harness and AVX2/FMA/F16C support. There is no portable CPU-feature dispatch or Linux ABI implementation.

## Repeated results

Same active-release matrix: 74,709 × 384. Each fresh process measures all eight `evals/performance.json` cases. Each scorer/query receives five excluded conditioning trials and 40 measured trials in deterministically shuffled interleaved order, with preallocated score outputs and identical NumPy top-k selection. Values below are medians across eight per-query medians, in milliseconds. C timings include ctypes and wrapper checks.

| Native threads | Run | NumPy float32 | C float32 parallel | Assembly float32 parallel | C half-input parallel | Assembly half-input parallel |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 1 | 2.812 | 2.431 | 2.465 | 1.268 | 1.259 |
| 4 | 2 | 2.799 | 2.468 | 2.475 | 1.276 | 1.255 |
| 8 | 1 | 2.423 | 2.520 | 2.496 | 1.304 | 1.268 |
| 8 | 2 | 2.465 | 2.501 | 2.508 | 1.293 | 1.275 |

The final eight-thread repeats show about 1.9× faster scoring for half-input assembly relative to NumPy. C is close enough that this experiment does not justify requiring assembly in a production implementation. The largest improvement comes from the half-input memory layout plus parallelism; float32 assembly alone does not beat NumPy consistently.

The initial 1/4/8/12/20-thread sweep is retained in protocol-2 receipts. Half-input parallel scoring was around 1.23–1.30 ms at 4–20 requested threads; spending more than four to eight threads produced little benefit in these observations. Those exploratory runs preceded metadata improvements. The four final protocol-3 runs above include actual BLAS thread reporting and source/DLL hashes.

| Native threads | Run | NumPy score + top-k ms | Assembly half-input score + top-k ms |
|---:|---:|---:|---:|
| 4 | 1 | 3.044 | 1.483 |
| 4 | 2 | 3.047 | 1.446 |
| 8 | 1 | 2.676 | 1.510 |
| 8 | 2 | 2.706 | 1.492 |

NumPy 2.2.6 uses OpenBLAS 0.3.29 with the reported Haswell kernel configuration. Its exported thread-count function confirmed four or eight threads as requested in each final run. MSVC OpenMP receives the corresponding explicit thread count; its effective team size was not separately instrumented. The two libraries retain separate worker pools, and interleaving can affect scheduling/cache behavior. The machine remained available for ordinary host/station work; this was not a dedicated idle-system benchmark.

## Correctness and review

All four final runs passed 110 synthetic checks covering empty row sets, odd dimensions/tails, unaligned float32 inputs, duplicate ties, cancellation and rejected native arguments. All eight real fixture queries preserved ordered top-18 row IDs for all eight native variants. Rank mismatches now fail the run after retaining its receipt.

One final eight-thread run additionally validated 128 deterministic normalized random queries against all eight variants: 1,024 comparisons passed both numeric tolerances and exact ordered top-18 equality. These random queries test numerical/ranking behavior, not semantic quality. Production-index tolerances are `atol=2e-6`, `rtol=2e-5`; synthetic random-tail checks use `atol=2e-5`, `rtol=2e-5`. This is finite validation, not bitwise equivalence or proof for every query.

Independent static review found no blocking Win64 calling-convention or array-bound issue. The assembly uses volatile registers, handles scalar tails and executes `vzeroupper`. There was no guard-page test or exhaustive binary16 edge-case validation. The reviewer identified missing BLAS/provenance metadata and nonfailing rank flags; these were addressed in the final harness.

The corpus is from active release `690d8bcbedcd4ff2a0f710b8fedaaa83`. The final receipts verify that the working retrieval module and retrieval configuration are byte-identical to that active release. Fixture questions remain from the working checkout. Source/DLL SHA-256 values and every measured trial are retained in the final receipts.

## Reproduction and production boundary

From `data/native-retrieval-spike-v2`, run `build.cmd`. From the repository root, run:

```powershell
python data/native-retrieval-spike-v2/bench.py 8 --test-only
python data/native-retrieval-spike-v2/bench.py 8 --extended
python data/native-retrieval-spike-v2/bench.py 4
```

The code, binaries and receipts are owner-local experimental artifacts ignored by Git. No native runtime import, loader fallback or deployment pin was added. The next integration gate is a Linux-compatible implementation/build and a full retrieval/chat evaluation that preserves evidence rankings, integrity checks and answer quality. The earlier [Linux profile](NATIVE_RETRIEVAL_SPIKE_2026_10_17.md) shows reranking and database verification dominating retrieval; saving about one millisecond of scoring is unlikely to be perceptible in a multi-second reply.

At the final availability check, active release and existing container IDs matched the prior experiment. Station checks passed except the retained security-scan warning; overall health remains degraded. Model/GPU and offline CPU voice checks passed. No gateway/model/voice restart, deployment, commit or push occurred. Browser and audible-speech acceptance were not run.

Final protocol-3 receipts:

- `run-4-1792314531145236500.json`
- `run-4-1792314570885604500.json`
- `run-8-1792314513758792900.json`
- `run-8-1792314546629101800.json`
