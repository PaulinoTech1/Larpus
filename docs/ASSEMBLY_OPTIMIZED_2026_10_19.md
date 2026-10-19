# Assembly optimized module check — 2026-10-19

The selectable **Assembly optimized** module passed correctness checks and repeated the warm scoring comparison. The station was not started, and no release was activated by this measurement.

Run `97c981ea762b48ca9bf424f9ad613229` loaded the checkout runtime over the frozen agent image in a network-disabled eight-CPU, 12 GB container. It used the pinned four-worker pool, the unchanged half-precision kernel, and the 2 MiB aligned matrix. Anonymous huge pages backed the whole aligned reservation: 58,720,256 bytes (56 MiB). The float16 payload is 57,376,512 bytes, about 54.7 MiB. That is the additional matrix beside Assembly original and the existing float32 index.

## Correctness

1,024 seeded random queries, the same seed as the stock lab:

- Raw optimized scores matched Assembly original bit for bit.
- Maximum absolute error versus NumPy was 7.450580596923828e-08.
- Guarded optimized top-18 sets matched NumPy on all 1,024 queries.
- Assembly original differed on query 729 only. Optimized matched NumPy there.
- All eight held-out text-to-reference neighbor sets matched NumPy for both Assembly choices.

These finite checks are not a proof for every input.

## Warm guarded scoring

Each backend has 300 measured calls. The timer excludes a 100 ms pace, five warmup rounds, and query embedding. A 60 second pause separates the blocks. Pressure and post-embedding conditions from the stock lab were not repeated.

| Block | NumPy p50 / p95 ms | Assembly original | Assembly optimized | Optimized versus NumPy |
|---|---:|---:|---:|---:|
| early-warm | 2.893 / 3.243 | 2.037 / 2.287 | 1.879 / 2.093 | 35.0% |
| repeat-warm | 2.910 / 3.372 | 2.035 / 2.442 | 1.888 / 2.257 | 35.1% |

Neither block recorded an ambiguity fallback. No optimized scoring call was at or below 1 ms. This is full-index guarded scoring, not chat or text-to-first-token latency.

Receipts: `data/assembly-linux-build/optimized-verify/97c981ea762b48ca9bf424f9ad613229/`.

## Prepared candidate

`341de68e12974563ab8da85c370542cc` is prepared and not activated. It uses the
active release's consistent knowledge index with this scoring module. The
working checkout catalog was not overwritten. The gateway was not started.
