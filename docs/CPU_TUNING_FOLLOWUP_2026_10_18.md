# 5900X tuning follow-up, 2026-10-18

The owner requested a more distinct advantage over NumPy using current hardware.
The active Assembly/NumPy selector and near-tie policy were preserved. The host
WSL limit remains 20 logical CPUs; each experiment used the existing eight-CPU,
network-disabled, read-only test container. GPU model and CPU voice were not
restarted or replaced. No experimental native change was retained.

## Experiments

The corpus contains 74,709 vectors with 384 dimensions. Each input value is the
original binary16 index value. Tests use eight fixed query embeddings, rotating
interleaved execution order, conditioning excluded from reported samples, and
the existing NumPy baseline. Raw-kernel probes are separate from guarded pipeline
measurements; their absolute timings should not be compared across runs as if
host load were identical.

| Raw worker sweep | Median scoring |
|---|---:|
| One worker | 2.919 ms |
| Two workers | 1.928 ms |
| Four workers | 1.688 ms |
| Six workers | 1.681 ms |
| Eight workers | 1.732 ms |
| NumPy, eight requested threads | 3.228 ms |

Six workers did not provide a meaningful improvement over four, and eight were
slower. The NumPy cutoff check alone measured approximately 0.214 ms.

Separate dispatch probes measured shared/dedicated/pinned four-worker pools at
1.846/1.866/1.857 ms. Pinning and dedicated queues were rejected. A fixed-dimension
fully unrolled kernel showed a modest raw gain (1.574–1.620 ms versus 1.688 ms),
but it did not produce a distinct guarded-pipeline improvement. Replacing the
cutoff check with a float-array partition also failed to improve the total.

An eight-row interleaved matrix layout measured 1.694 ms versus 1.832 ms for the
row-major candidate in its raw probe. A bounded C heap with AVX2 threshold
screening was also tested to avoid allocating a full row-index partition.

## Direct final comparison

The final candidate combined the packed eight-row layout and native cutoff helper.
It was compared with the actual frozen active Assembly source and binary in the
same isolated process, sharing the same query inputs and four-worker limit.
Each case used five conditioning rounds and 60 measured interleaved repetitions.

| Run | NumPy | Deployed Assembly | Candidate | Incremental saving |
|---|---:|---:|---:|---:|
| First | 3.202 ms | 2.090 ms | 2.058 ms | 1.5% |
| Repeat | 2.966 ms | 1.976 ms | 1.894 ms | 4.2% |

The approximately 0.03–0.08 ms incremental saving is too small to justify the
added native helper, packed copy, and validation surface for this objective.
The candidate was rejected and the existing native/build files restored
byte-for-byte from active release `d604dfcd7ebd4c0199cdec395b6c61cf`.
The previously measured Assembly advantage over NumPy remains; this pass did
not establish a distinctly larger advantage or an overall chat latency gain.

Candidate validation covered 30 matrix shapes with output sentinels, 30 cutoff
cases including ties and sentinels, and 1,024 seeded random queries. All checked
top-18 reference sets matched NumPy. Two random queries reordered near ties;
maximum absolute score error was `7.450580596923828e-08`. These finite checks
do not prove universal rank equivalence. The maintained benchmark now retains
matrix shape/sentinel checks and 1,024 random comparisons with error/order counts.

## Owner-local evidence

- Worker sweep: `data/assembly-linux-build/6c992dc962b64f688e9f1ce263022b00/report.json`.
- Kernel unrolling: `data/assembly-linux-build/c06f44c073384596936c8f2db989cd75/report.json`.
- Dispatch: `data/assembly-linux-build/5f1dc3693b0d4e3ba60f4d8b9dfcd15e/report.json`.
- Packed layout: `data/assembly-linux-build/10f0ff1044bd4c4392fc1a7c2afec71e/report.json`.
- Final comparison: `data/assembly-linux-build/10e8a8662ef149029e8e1df5d80f7bbc/report.json`.
- Repeat: `data/assembly-linux-build/ce9e0befcb0c4c678abc04082520c4cd/report.json`.

The initial packed comparison `08e337bb7ce54cb49a4e6547f6eb4e1a` is excluded:
its old-pipeline copy incorrectly inherited the candidate's packed score method.
The final two comparisons explicitly load the frozen old scorer class and binary.
One early worker-probe reporting wrapper failed after writing a complete receipt;
its measurements were retained. Failed private probes and stderr remain on disk.
