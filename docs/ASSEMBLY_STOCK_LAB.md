# Assembly/HWiNFO lab within the existing CPU envelope

This owner-side suite compares the frozen current Assembly pipeline, NumPy and
a separately built candidate on the full approved embedding index. It does not
activate changes or start the gateway, GPU model or CPU voice. The station must
be stopped first; the scheduled nightly task is not changed by the suite.

All run artifacts and compiler caches stay on E:, including Linux files inside
the Larpus WSL disk, whose registered location is checked before startup. The
suite reuses existing installed Python, Zig, WSL and pinned images. It does not
move those dependencies or claim Windows performs no unrelated writes on C:.

## Commands

From `E:\speedzone_MS\LARPUS`:

```powershell
# Read-only plan; does not start WSL.
python scripts/assembly_lab.py

# HWiNFO Sensors must already be logging to this E: CSV.
# Smoke validates transport/correctness and cannot qualify a speed claim.
python scripts/assembly_lab.py --run --smoke --hwinfo E:\speedzone_MS\LARPUS\larpus-sensors.csv

# Full session: correctness/selection startup, 5 min settling,
# 10 min comparisons and 5 min warmed repeat. Startup is additional.
python scripts/assembly_lab.py --run --minutes 20 --hwinfo E:\speedzone_MS\LARPUS\larpus-sensors.csv
```

The default CSV clock offset is Eastern daylight time, UTC-240 minutes, matching
the October 19 recording. Set `--utc-offset-minutes` explicitly for another
offset/date. Stale or wrongly offset sensor data prevents a load run.

Outputs are under `data/assembly-linux-build/stock-lab/<unique-id>/`:

- `REPORT.md`, `report.json`: latency distributions, raw samples and qualification.
- `stdout.jsonl`, `stderr.txt`: observable progress and retained failures.
- `status.json`: current phase, latest sensor time, completed/held state.
- `manifest.json`, captured source and `liblab.so`: source/fixture/image pins.
- `sensors.json`, `sensor-phases.json`: captured host readings and phase joins.

Nothing is installed into the runtime. When the suite started WSL itself, it
terminates Larpus after its own container exits, provided no other containers
have appeared. It does not shut down other distributions.

## What is measured

Guarded scoring includes the full-index score array, worker dispatch, output
validation and the existing ambiguity guard. Preparation and 100 ms pacing are
outside that timer. Warm cache, 128 MiB strided cache-pressure preparation and
post-embedding conditions run in rotated NumPy/current/candidate order, both
early and in the warmed repeat. Pressure is a proxy, not a verified cache flush.

`Engine.neighbors` is separately timed on actual held-out text: embedding,
guarded scoring, top-k selection and reference mapping. A 1 ms score does not
mean a 1 ms text-to-reference fetch, model response or browser render.

Qualification requires at least 100 measured samples in **every** reported
early/repeat condition, p95 <=1 ms and at least 95% of calls <=1 ms, at least a
10% median improvement over the current pipeline, and no p95 regression.
Numerical and top-reference-set checks must pass. Smoke runs never qualify.
P50/p95/p99, outliers, fallback/quota observations and all rejected candidates
remain visible. Passing this suite does not automatically authorize deployment.

Candidate selection questions are separate from held-out acceptance questions.
The full run checks 1,024 seeded random queries and actual neighbor-reference
sets. Native validation covers empty/small/odd shapes, output sentinels,
retained-output ownership, repeated jobs and invalid arguments. Current
experiments require the candidate's raw scores to match the frozen Assembly
scores bit-for-bit, in addition to tolerance checks against NumPy. Numerical
testing is finite, not a proof for all possible inputs.

## Candidate implementations

The C pool has sleeping persistent pthread workers. It calls the unchanged
deployed binary16 assembly or a float32 assembly implementation with the same
four-accumulator reduction. Workers 2/4/6/8 are screened; no affinity is changed.
The float32 input is lossless, uses the existing full float32 matrix, and doubles
matrix read bytes compared with binary16. Its bandwidth cost is measured.

An additional 4/8-worker candidate copies the binary16 matrix into a 2 MiB
aligned anonymous mapping and requests `MADV_HUGEPAGE`. Actual `AnonHugePages`
is read from the process's smaps and retained in the report. An advisory request
alone is not counted as huge-page backing. This candidate adds a matrix-sized
resident copy and startup mapping/copy work, excluded from steady-state timing
and retained as a deployment cost. No sysfs/OS huge-page setting is changed.

Candidates use a stronger experiment-only cutoff guard: duplicate vector rows
at an ambiguous boundary also fall back to NumPy. The frozen current guard
deliberately skips that fallback. A 1,024-query gate found one case where current
Assembly selected a different row ID with an identical vector; the first full
attempt was rejected before timing. The diagnostic is retained at
`data/assembly-linux-build/stock-lab/diagnose_guard.json`. The candidate guard
does not waive the mismatch: it reproduces NumPy's reference choice instead.
Raw native scores remain bitwise-equal to current Assembly. Current-vs-NumPy
reference differences remain separate diagnostic failures of the control.

The C library is an owner-only experiment, never exposed through MCP. Its pool
has a serialized caller contract; the Python adapter locks scoring/closing and
retains matrix, query and output ownership until native work has joined.

## CPU and availability boundaries

There are no BIOS, voltage, power-plan, affinity or PPT/TDC/EDC writes. The
observed/inferred PPT envelope is approximately 142 W; this is not certification
that every BIOS setting is factory stock. The existing WSL limit stays 20
logical CPUs/48 GB, with an eight-CPU/12 GB test container and no GPU access.

During the supervised runner the conservative stop rules are Tctl/Tdie >=85 C,
any CPU thermal-throttling flag, stale sensor readings, or observed/inferred PPT
above 145 W. These are experiment guardrails, not CPU specifications, and cannot
control unrelated host programs. Hitting the existing normal power limit alone
does not cause a power-setting increase. HWiNFO polling is approximately two
seconds: joins are phase-level and cannot attribute individual 1 ms calls.

Build and initialization costs are separate from steady-state comparisons.
The supervisor does not establish universal overclock/undervolt stability,
silicon quality, memory error freedom, or physical CCD placement under WSL.
