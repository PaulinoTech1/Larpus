# Stock-envelope Assembly results - 2026-10-19

**The candidate improved scoring by approximately 5-7%, but the repeated 1 ms target was not achieved.** The frozen production configuration is retained and remains stopped.

The completed run `f44b0b5cd94249a99fb277e892d8a099` selected `c-pool-aligned-half-4` on separate screening questions, then measured early and warmed held-out questions. The candidate combines a sleeping four-worker C pool, the unchanged half-precision assembly arithmetic, a 2 MiB aligned matrix with actual huge-page backing, and a stricter duplicate-cutoff guard. This experiment measures the combination; it does not isolate which change caused the gain.

## Full-index guarded scoring

Each cell below is p50 / p95 milliseconds. Warm-up, pacing and preparation are excluded from scoring. The entire 74,709 x 384 index is retained.

| Block / condition | Calls per backend | NumPy | Current Assembly | Candidate | Median saving vs current |
|---|---:|---:|---:|---:|---:|
| early/warm | 634 | 2.473 / 2.878 | 1.725 / 1.980 | 1.605 / 1.865 | 7.0% |
| early/pressure | 601 | 3.150 / 3.722 | 2.182 / 2.657 | 2.075 / 2.483 | 4.9% |
| early/after-embedding | 615 | 2.938 / 3.305 | 1.949 / 2.257 | 1.806 / 2.084 | 7.3% |
| warmed-repeat/warm | 316 | 2.473 / 3.057 | 1.715 / 1.955 | 1.618 / 1.891 | 5.7% |
| warmed-repeat/pressure | 300 | 3.143 / 3.661 | 2.187 / 2.594 | 2.065 / 2.455 | 5.6% |
| warmed-repeat/after-embedding | 306 | 2.939 / 3.310 | 1.941 / 2.183 | 1.800 / 2.040 | 7.3% |

There are 8,316 measured scoring calls. Every condition has at least 100 samples per backend. Candidate p95 improved in all six conditions, but no measured candidate scoring call was <=1 ms. The candidate also misses the separate 10% median-improvement gate. It is retained as an experiment rather than promoted.

## Correctness and the duplicate boundary

All 252 native shape/boundary/ownership checks passed. Each candidate completed 1,024 seeded random-query checks with zero NumPy reference-set mismatches after the stronger guard was applied. Raw native score bits match current Assembly; maximum score error against NumPy is 7.450580596923828e-08. Actual held-out Engine.neighbors reference sets also match NumPy.

The original frozen guard selects a different tied reference at random query 729: matrix indices 68560 and 68636 map to distinct row IDs 70578 and 70654 but have identical vectors. This is a reference-choice difference at an exact duplicate boundary, not evidence of unrelated vectors being retrieved. The experimental guard falls back to NumPy for this case; the frozen control remains unchanged. The initial full attempt was rejected before timing, with its failure retained at `data/assembly-linux-build/stock-lab/31604a82fd394b7ea1b367016d654f61/`.

## Text-to-reference fetch is a separate measurement

The final fetch probe is an **unpaced burst**, with 112 measured calls per backend. It includes query embedding, guarded scoring, top-k and reference mapping. It is not directly comparable with the paced scoring conditions. Per-fetch quota counters were not captured, so the long tails cannot be attributed to native scoring or a specific scheduling cause.

- numpy: p50 8.957 ms, p95 60.562 ms.
- current: p50 8.364 ms, p95 59.588 ms.
- c-pool-aligned-half-4: p50 7.975 ms, p95 58.177 ms.

Neither guarded scoring nor complete text-to-reference fetch meets the repeated 1 ms target. No overall chatbot latency gain is established.

## HWiNFO and CPU settings

The supervisor captured 629 distinct HWiNFO samples. CPU Tctl/Tdie peaked at 66.9 C and PPT at 129.024 W (maximum reported PPT-limit utilization 90.9%). All recorded HTC/PROCHOT CPU/PROCHOT EXT flags were No. No sensor guardrail stopped the run. CPU quota counters recorded zero throttled periods in the paced scoring/preparation windows; this does not describe the unpaced fetch probe.

There were no BIOS, voltage, power-plan, affinity or PPT/TDC/EDC writes. The power-plan read-back matches the beginning of the run. WSL remains configured for 20 logical CPUs and 48 GB; the isolated network-disabled CPU-only test container used an eight-CPU quota and 12 GB memory. The log does not certify that every BIOS setting is factory stock or establish silicon quality.

The reported aligned candidates had 57,344 KiB of anonymous huge-page backing. They require an extra matrix-sized resident copy and initialization work. This startup/memory cost is separate from steady-state score latency. No global huge-page setting was changed.

## Availability, artifacts and verification

Active release remained `f08b98ea2f34407cb77dc79aa7d7866a`. No application release was staged/activated, no model/voice image was replaced, and no production service was started. After the run there were no running WSL distributions; the active gateway remained stopped and the LARPUS Study Notes task remained disabled.

All owned artifacts/compiler caches are on E: or in the WSL virtual disk verified at `E:\WSL\Larpus\ext4.vhdx`. Existing installed tools were reused; no dependencies were installed. The original HWiNFO CSV was read without modification. Windows can still perform unrelated OS writes on C:.

Raw run: [REPORT.md](../data/assembly-linux-build/stock-lab/f44b0b5cd94249a99fb277e892d8a099/REPORT.md). Full per-call data, correctness, quota counters and timestamps are in `report.json`; source/image/compiler pins in `manifest.json`; host sensors and phase joins in `sensors.json` / `sensor-phases.json`. All p99/outlier data remain available. Failure and smoke receipts remain alongside the completed run.

Usage and limits: [Assembly stock lab](ASSEMBLY_STOCK_LAB.md). Focused verification: 16 unit checks passed, native integration passed 252 checks, 1,024 random queries per candidate, and held-out reference comparisons. These finite tests are not a universal proof. No commit or push was performed.
