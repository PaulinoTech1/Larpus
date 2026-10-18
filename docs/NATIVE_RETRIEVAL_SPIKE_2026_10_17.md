# Native retrieval experiment — October 17, 2026

The tested C scorer should **not replace NumPy**. AVX2/FMA beat the single-thread-request NumPy baseline slightly, but lost to the eight-thread-request baseline. More importantly, vector scoring occupies only a few milliseconds of a roughly two-second retrieval path. No production optimization was installed or activated.

## Target and scope

Measured on the owner’s AMD Ryzen 9 5900X (12 physical cores / 24 logical threads). WSL remains limited to 20 logical CPUs; the Linux experiment was capped at eight CPUs. The active release was `690d8bcbedcd4ff2a0f710b8fedaaa83`, with Larpus 3.8 on GPU and CPU voice running.

The native experiment is a Windows MSVC DLL, not a Linux production module. Linux profiling used a separate container from the active agent image, with no network, GPU, broker sockets or writable production mounts. Neither experiment changed runtime settings, shared dependencies, images, source snapshots or release selection.

## Linux retrieval profile

Eight fixed cases from `evals/performance.json`, one conditioning pass excluded, then three measured passes: 24 observations. The engine was loaded once. Model/index setup is excluded. These are medians of accumulated scopes per request; scopes overlap and must not be added together.

| Scope | Median ms |
|---|---:|
| augment_total | 2165.062 |
| database | 331.389 |
| embedding_onnx | 6.301 |
| embedding_tokenization | 0.183 |
| inspect_message | 10.811 |
| neighbors_total | 10.251 |
| query_embedding_total | 6.659 |
| rerank_total | 1363.144 |
| reranking_onnx | 1355.534 |
| reranking_tokenization | 6.710 |
| screen_optional_evidence | 6.731 |
| topk | 0.370 |
| vector_dot | 3.161 |

`database` includes the existing integrity verification and connection opening; it does not isolate hashing from SQLite connection overhead. SQLite query execution, bookkeeping and other retrieval work remain inside `augment_total`. Screening hooks shown above are those present in the frozen release.

The instrumented engine ran locally within the experiment process. Production uses a persistent worker and socket transport. This profile therefore identifies costs, but is not an exact production transport breakdown or a new prompt-to-first-text benchmark. Wrapper overhead, CPU quotas, host activity and deadline-dependent reranking affect results. Reranking retained the existing batch/deadline behavior; no answer-quality claim follows from these timings.

At the measured median, vector scoring is approximately 0.15% of retrieval augmentation. Even eliminating that representative scoring cost would save only about 3.2 ms. This is an illustrative ratio of medians, not a guaranteed per-request upper bound.

## Windows C comparison

The exact pinned active-release embedding index contains 74,709 rows × 384 dimensions, converted to float32 as in the runtime. All eight fixture questions were embedded with the pinned query embedder. Three scorers share the existing NumPy top-k algorithm: preallocated NumPy matrix-vector multiplication, optimized ordinary C, and C AVX2/FMA intrinsics. The C implementations are single threaded.

Compiled with existing MSVC 19.41 using `/O2 /arch:AVX2 /LD`; generated assembly contains `vmovups` and `vfmadd231ps`. No handwritten assembly or downloaded compiler was needed.

Fresh processes request native thread limits through `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` before imports. These are requested limits; effective BLAS thread counts were not independently inspected. NumPy is 2.2.6. Kernel trials include ctypes entry and lightweight Python shape checks for C, with preallocated outputs for all scorers. Each query has five excluded conditioning trials and 50 interleaved measured trials; order is deterministically shuffled.

The table reports the median across eight per-query medians, in milliseconds. Full per-query trial distributions and p90 values are retained locally.

| Requested native threads | Measurement | NumPy | Ordinary C | AVX2/FMA C |
|---:|---|---:|---:|---:|
| 1 | Score kernel | 5.162 | 17.747 | 4.301 |
| 1 | Score + existing top-k | 5.343 | 17.995 | 4.524 |
| 8 | Score kernel | 2.794 | 18.220 | 4.419 |
| 8 | Score + existing top-k | 3.001 | 18.472 | 4.648 |

Both thread configurations were run twice in separate fresh processes; the first-run receipts are retained separately. They showed the same ordering: AVX2 ahead of single-thread-request NumPy, behind eight-thread-request NumPy, and ordinary C slowest. This is a Windows kernel experiment; it does not establish the speed of an equivalent Linux C build.

Correctness: 23 synthetic checks per final run covered odd/tail dimensions, unaligned inputs, empty row sets, invalid pointers/dimensions/size overflow, duplicate ties and cancellation. All eight production-index queries passed numeric tolerances (`atol=2e-6`, `rtol=2e-5`) and preserved the exact ordered top-18 row IDs for both C versions. Synthetic random checks use `atol=2e-5`, `rtol=2e-5`. This finite test set does not prove bitwise equivalence or rank equivalence for all possible queries. FMA and reassociation can change rounding.

## Decision and next target

Keep the existing NumPy scorer. Do not add native build/deployment complexity or hand assembly for this result. Profile and test reranking policy and immutable-database verification next, preserving evidence selection, integrity checks and answer quality. A verification cache would require a trusted immutable file identity and explicit invalidation; simply removing hashing is not an acceptable optimization. Any proposed reranking change needs the existing quality rubric and reference comparisons.

The earlier [performance baseline](PERFORMANCE_BASELINE_2026_10_17.md) remains the prompt-to-first-text result. No integrated chat latency improvement was measured in this experiment.

## Receipts, reproduction and availability

Owner-local artifacts are under `data/native-retrieval-spike/` (ignored by Git): `score.c`, `score.asm`, `score.dll`, `build.cmd`, `bench.py`, `linux_profile.py`, `run_linux.py`, Windows JSON receipts, `linux.json`, and before/after health/container snapshots. These scripts are experimental and are not runtime imports or public APIs.

Run `build.cmd` from that directory using the installed VS 2022 toolchain, then from the repository root run `python data/native-retrieval-spike/bench.py 1`, repeat with `8`, and run `python data/native-retrieval-spike/run_linux.py` for the isolated Linux profile. Reproduction uses the then-active release, so record its ID and expect results to differ after a release/corpus change. The Linux runner refuses network pulls and uses the already-cached image.

Before/after active release and all existing container IDs matched; the experiment container was removed after completion. Final station checks passed except the retained security-scan warning, so overall health remains degraded. The health probe reports the selected model GPU-resident and the pinned offline CPU voice worker available. No gateway/model/voice restart, activation, commit or push was performed. A health check is not a browser or audible-speech test.
