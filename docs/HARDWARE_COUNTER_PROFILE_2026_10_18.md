# Hardware counter profiling: 5900X, 2026-10-18

The first hardware-counter pass strengthens the case for a memory-hierarchy /
working-set bottleneck in the Assembly scorer. It does not establish DRAM
bandwidth saturation, a particular L3 miss rate, thermal throttling, or poor
silicon quality. No new implementation or hardware tuning was deployed.

## Access and collection boundary

WSL kernel `6.18.33.2-microsoft-standard-WSL2` exposes a CPU PMU, even though
`perf` is not installed. Direct Linux `perf_event_open` calls successfully
counted user-space cycles, instructions, generic cache references/misses and
branches/mispredictions. This corrects the earlier practical limitation: no
hardware counters were collected in the previous experiments, but the missing
`perf` executable did not mean the PMU itself was unavailable.

The default benchmark container denied every perf call (EPERM). A copied,
private seccomp policy retains the default action and all other syscall rules,
removes perf_event_open from the old capability-dependent entries, then allows
that syscall only when pid argument is zero (own calling thread). Production
seccomp, capabilities, images, sysctls and active containers are unchanged.
No new capability, system package, driver or admin session was used. The profiler
container retains eight CPUs, 12 GB, no network, read-only filesystem, dropped
capabilities and no-new-privileges. A separate check confirmed pid=0 succeeds
and an explicit positive pid is denied by the copied policy's default ENOSYS.
An initial check incorrectly expected EPERM rather than ENOSYS; the failed
check receipt is retained and the observed return was subsequently verified.

Six events are grouped and enabled together on each of the four kernel worker
threads; the main-thread cutoff is measured separately. All groups reported
running/enabled fraction 1.0. This avoids comparing counters sampled in different
time windows. Counters exclude kernel and hypervisor execution. They remain
VM-exposed measurements rather than a bare-metal CPU characterization.

The underlying syscall scope and grouped-counter semantics follow the
[Linux perf_event_open reference](https://man7.org/linux/man-pages/man2/perf_event_open.2.html).
Windows also lists PMU sources through `wpr -pmcsources`; WPR was not recording,
and no Windows trace was started. See
[Microsoft PMU recording](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/recording-pmu-events).

## Full-index kernel profile

Index: 74,709 by 384, 54.72 MiB binary16. Four held-out questions, two excluded
conditioning rounds and twelve measured rounds per question/condition: 48 calls
per condition, 192 calls and 768 measured worker regions total. Each region
uses the checksum-pinned deployed kernel; the worker threads are not affinity
pinned. Each sample waits 100 ms before preparation. Pressure touches a 128 MiB
buffer at 64-byte strides and is a proxy rather than a guaranteed cache flush.
Embedding/reranking preparation is excluded from the kernel counters.

| Condition | Instructions/query, millions | Sum worker cycles/query, millions | Kernel IPC | Branch misprediction | CPU quota periods |
|---|---:|---:|---:|---:|---:|
| warm | 11.687 | 21.955 | 0.532 | 0.158% | 0 |
| pressure | 11.687 | 28.284 | 0.413 | 0.190% | 0 |
| after-embedding | 11.687 | 21.355 | 0.547 | 0.181% | 0 |
| after-reranking | 11.687 | 21.049 | 0.555 | 0.176% | 0 |

Instruction work is nearly unchanged while cache pressure costs approximately
29% more summed worker cycles than warm scoring. Branch misprediction is low;
no quota throttling was recorded in these measured scoring regions. This
supports a data-access/working-set explanation over simply removing branch
instructions. It does not by itself distinguish memory latency, bandwidth,
prefetch behavior, translation or execution-resource dependencies.

The empty instrumented region measured a median 7,739 cycles. Instrumented
pipeline wall times include counter-management and dispatch overhead and must
not be presented as production latency. The independent uninstrumented warm
comparison in this process had medians:

- assembly: 2.001 ms.
- numpy: 2.813 ms.

The cutoff region has separate counts in the receipt; it is not part of the
worker IPC numerator/denominator. Summed cycles across four concurrent workers
are not elapsed cycles of a single core and must not be divided by wall time
to report CPU GHz. The recorded cycles/thread-CPU-time ratio also includes
counter-control CPU overhead, so it is not a trustworthy physical effective
clock, especially for short cutoff regions.

## Working-set test and reverse-order repeat

The exact same row-major native kernel processes smaller prefixes and a doubled
matrix. Small cases repeat the kernel inside a tiny C helper to amortize Python
and counter-management overhead. Packing, matrix allocation and counter opening
are outside the kernel regions. The C helper only calls the existing pinned
kernel repeatedly; it does not change its arithmetic. Each size has two excluded
conditioning rounds and eight measured four-worker batches, with 50 ms pacing.
This is a cache-sensitivity diagnostic, not a single-query performance target.

| Working set | Instructions/row, first / repeat | Cycles/row, first / repeat | IPC, first / repeat |
|---|---:|---:|---:|
| 0.375 MiB (512 rows) | 157.1 / 157.1 | 75.5 / 70.1 | 2.080 / 2.242 |
| 3.000 MiB (4,096 rows) | 156.9 / 156.9 | 108.0 / 105.1 | 1.453 / 1.493 |
| 12.000 MiB (16,384 rows) | 156.9 / 156.9 | 170.7 / 182.5 | 0.920 / 0.860 |
| 54.719 MiB (74,709 rows) | 156.7 / 156.7 | 306.2 / 344.2 | 0.512 / 0.455 |
| 109.437 MiB (149,418 rows) | 155.8 / 155.9 | 322.5 / 371.3 | 0.483 / 0.420 |

The first run orders sizes from smallest to largest; the repeat reverses them.
Instructions per row stay approximately 156-157 while full-index cycles per row
are roughly four to five times the smallest working set. The reverse repeat
recorded no quota throttling in measured batches. This replicated result is the
strongest evidence from this pass for memory-hierarchy sensitivity. It does
not prove that all remaining cycles are memory stalls, or identify the exact
cache level or maximum attainable DRAM bandwidth.

The original Python-loop working-set run is retained but superseded:
`one-ms-b86b592a2ef7430d8d50db0fff7908e0/report.json`. Its smallest case incurred
approximately 421 instructions/row, showing material harness overhead; it is
not used for the normalized comparison above. The C-loop repeat reduces that
to approximately 157 instructions/row. Generic misses per thousand instructions
are recorded but are not monotonic across all sizes and are not labeled L3
or DRAM accesses.

WSL exposes `cpu`, `software`, `msr`, tracepoint and related event sources, but
no amd_l3, amd_df or IBS source was observed. Generic cache events therefore
cannot establish LLC miss bandwidth or memory-channel saturation here. AMD
separately documents L3 and Data Fabric PMU sources in its
[hardware profiling reference](https://docs.amd.com/r/en-US/57368-uProf-user-guide/Hardware-Sources).

## vCPU placement and silicon-lottery assessment

Two shuffled sweeps temporarily pin only the private profiler's calling thread
across its 20 allowed virtual CPUs, restoring affinity afterward. Each measures
the full matrix with the raw single-thread kernel, without pool dispatch or
cutoff. Twelve measured calls per vCPU follow two conditioning calls. These
are not four-worker pipeline timings and do not identify physical host cores.

- Initial Python-batch run: per-vCPU median range 2.052-2.843 ms.
- C-batch run: per-vCPU median range 2.091-2.629 ms.
- Reverse working-set repeat: per-vCPU median range 2.042-2.427 ms.

There is placement/run variability, but it mixes boost, cache residency,
hypervisor scheduling and other system load. It does not support ranking the
5900X's physical cores or assigning a good/bad silicon bin. The sweeps were
short profiling tests, not sustained thermal or voltage stability tests.

Read-only host inventory found:

- Ryzen 9 5900X, 12 cores / 24 threads; WSL remains limited to 20 logical CPUs.
- Two 32 GiB G.Skill F4-3600C18D-64GVK DIMMs, reporting configured speed 3600.
  This is not proof of actual timings, FCLK/UCLK, channel interleaving or memory
  controller stability. No RAM or BIOS configuration was changed.
- ASUS ROG STRIX B550-F GAMING (WI-FI), BIOS version 3607.
- High performance Windows power scheme.
- WMI reports 3701 MHz for current/max frequency; this is not a measured boost
  clock. AMD specifies a 3.7 GHz base and up-to-4.8 GHz boost for this model in its
  [5900X specifications](https://www.amd.com/en/products/processors/desktops/ryzen/5000-series/amd-ryzen-9-5900x.html).
- Twelve Windows counter snapshots show per-logical-CPU Processor Performance
  readings of approximately 99-126% of nominal. They cover the whole host and
  are not attributed to the profiler's specific physical cores.
- WSL has no hwmon data; Windows ACPI thermal-zone query is unsupported. No
  reliable CPU temperature, voltage, effective per-core clock or PPT/TDC/EDC
  limit telemetry was collected yet.

HWiNFO 7.16 and Ryzen Master 2.14 are installed but were not running. HWiNFO's
embedded manifest requires administrator elevation, and this session is not
elevated. Its author documents automatic CLI logging as Pro-only; a license
was not assumed and no license settings were inspected or changed. See the
[HWiNFO author reference](https://www.hwinfo.com/forum/threads/supported-command-line-parameters-in-hwinfo64-pro.8549/).
An owner request is pending to start Sensors-only CSV logging at
`data/assembly-linux-build/silicon-sensors.csv`. Physical clock/thermal/power
correlation must wait for actual readings, not be inferred from the WMI base
clock or the vCPU sweep. No thermal-limit or silicon-quality claim is made.

## Practical next measurements

The observed working-set penalty makes locality, representation and required
scan traffic stronger leads than additional arithmetic unrolling. Before
changing clocks/voltage, correlate a fixed scoring workload with HWiNFO effective
clocks, CPU temperature, package power and available limit flags. Inspect
FCLK/UCLK and actual RAM timings if exposed. A native-host L3/Data Fabric/IBS
profile could then separate cache latency from DRAM traffic; it requires a
scoped tool/driver plan and cannot be substituted with the generic WSL counts.
A silicon-quality ranking would additionally need comparable samples or a
controlled frequency/voltage stability experiment, which this task has not run.

## Evidence and station availability

All raw receipts below are private under `data/assembly-linux-build/`:

- `hardware-counter-discovery.json`, `hardware-pmu-enumeration.json`,
  `hardware-pmu-capability.json`: WSL capability discovery and own-thread counts.
- `one-ms-b9ea7f33119749ada6adcdbb4ea80dbd/report.json`: default-container denial.
- `one-ms-324356caadd9450e9beaaec1e7c4f131/report.json`: own-thread policy success.
- `hardware-pmu-seccomp-receipt.json` and copied policy: exact constrained change.
- `one-ms-0960e0b1cb6e447d9e5af8f69f16b7a4/stderr.txt`: wrong expected errno.
- `one-ms-d8f803deb8064368be1d82ca076e285e/report.json`: positive pid denied, errno38.
- `one-ms-5bfdbe89efc74ad383903bcfdf246eef/report.json`: Kernel/cutoff grouped counters.
- `one-ms-260e6fac88a24def9f2e657fb560f19f/report.json`: C-loop working-set test.
- `one-ms-a0b113be0fa84a7598422d910f02fba9/report.json`: Reverse-order repeat.
- `pmu-repeat/`: C source, pinned helper artifact and manifest.
- `hardware-host-inventory.json`, `hardware-windows-clock-profile.json`,
  `hardware-sensor-tool-inventory.json`: host observations.
- `hardware-counter-availability-after.json`: active release/services/source hashes.

The active release stays `f08b98ea2f34407cb77dc79aa7d7866a`, with Assembly selected.
Model/voice container identities, images and start times and scorer/kernel pins
match the previous experiment's ending snapshot. No application deployment,
production affinity change, BIOS/clock/voltage change, dependency installation,
commit or push was performed. The temporary profiling containers exited with
`--rm`. The profiler-only policy file is retained for reproduction and is not
selected by production. This pass does not claim a new application test-suite
result; it changes documentation and private diagnostics, with capability and
measurement checks recorded above.

The timed follow-up workload is ready as private hardware_sensor_load.py: ten
seconds idle, thirty seconds guarded Assembly load, ten seconds recovery, with
UTC phase markers. It has not been run because the requested sensor CSV is
not present yet. HWiNFO was observed running after the owner logging request;
process presence alone is not treated as proof of active logging.

## Owner follow-up: locating the sensor log

After the owner reported logging started but did not know the save location,
a read-only filename inventory covered accessible areas of C:, D: and E:.
The second pass used case-insensitive CSV/HWiNFO filename matching; it listed
571 matching paths on C: and 124 on E:, with no likely sensor CSV found.
D: had no matching accessible paths. Search warnings were retained (579/7/4
messages by drive); this is not an exhaustive inventory of protected folders.
Recent CSV headers and sensor-named files were screened without dumping
unrelated CSV contents. No files were moved or deleted.

Read-only probes for the local/global HWiNFO and Afterburner shared-memory
feeds also returned not found (Windows error 2). Thus neither a located sensor
CSV nor an accessible live sensor feed is available. HWiNFO process presence
was inconsistent across checks and does not establish Sensors/logging status.
The timed load remains held to avoid losing its sensor correlation. Hardware
inventory again confirmed the 5900X and two 32 GiB DIMMs with configured speed
reported as 3600. CPU temperature and physical silicon quality remain unmeasured.

Receipts: `hardware-sensor-log-search.json`,
`hardware-sensor-log-search-casefold.json`, per-drive scan error files and the
private `hardware_shared_memory_probe.py`. The next owner action can use a
simple known destination: Desktop\larpus-sensors.csv via HWiNFO Sensors > Start
Logging, leaving HWiNFO open. No existing log path needs to be remembered.
