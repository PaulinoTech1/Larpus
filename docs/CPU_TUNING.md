# Ryzen 9 5900X latency work

The owner approved a maximum of 20 logical processors for WSL, keeping headroom
on the 12-core/24-thread host. This is a VM capacity limit, not four dedicated
Windows cores. Windows-side owner tools are outside that WSL limit. The host
has approximately 64 GiB RAM; the existing WSL memory limit remains 48 GB.

## Instrumentation

Successful replies carry an additive numeric `timing_ms` field. Existing HUD tabs
can ignore it. Streaming still releases only checked text and finishes with a
`done` event. No prompt, evidence passage or generated text is added to timing
receipts. Failed or held replies do not acquire success timings.

- `input`: persona, conversation and input checks.
- `retrieval`: evidence lookup, augmentation and screening together.
- `model_selection`: resolving the currently selected model.
- `model_first_frame`: starting generation to the first broker/model frame;
  includes admission, queueing, prefill and transport, not isolated GPU compute.
- `first_checked_text`: inference entry to first approved chunk, before its
  callback; not physical browser display time.
- `inference_total`: inference entry through final output/source screening.
- `preflight`: preparing the fixed child command and current isolation checks.
- `mcp_connect`: child startup and MCP connection/initialization.
- `mcp_total`: the entire MCP operation, overlapping the inference timers.

These scopes overlap. Do not add all values to estimate a total. HTTP admission
and browser rendering are outside inference timers. The owner HTTP probe measures
time from sending a request to receiving its first checked chunk separately:

```powershell
python scripts/benchmark-chat-latency.py --profile greeting --repeats 3
python scripts/benchmark-chat-latency.py --profile learning --repeats 3
python scripts/benchmark-chat-latency.py --profile cyber --repeats 3
```

An older active release returns an empty `stage_ms`; that means instrumentation
is not active, not zero time. These commands use real generation and can compete
with interactive chat.

## CPU sweep

```powershell
# Prints the plan only; no inference.
python -m scripts.cpu_benchmark
# Runs cases sequentially in fresh CPU-only processes.
python -m scripts.cpu_benchmark --run --threads 4 8 12 16 20 --batches 2 4 8 --repeats 3
```

By default the script selects the active frozen release's approved library,
verifies its database/model/embedding pins, and reads SQLite immutably. It never
rebuilds or edits the index. `--directory` and `--models` allow a separate owner
fixture. No package installation, GPU calls, network access or activation occurs.

Each case creates a fresh engine with the requested ONNX threads and reranking
batch size. Native BLAS/OpenMP thread settings are bounded to that case's count;
tokenizer parallelism is disabled. Counts above 20 are rejected. These are worker
settings, not a hard total CPU quota across every host process or native pool.
The actual WSL ceiling needs the maintenance step below.

Setup, warmup and measured requests are separate. Cases exercise fixed learning,
SOC and authorized pentesting questions against 16 semantic candidates. They
do not reproduce the complete live BM25/semantic candidate merge or final
evidence screening. Production's eight-CPU agent quota is unchanged, so a host
result at 12-20 threads cannot be assumed to transfer to production.
Receipts distinguish requested threads from the effective ONNX session thread
count. Visible-CPU limits can clamp the latter; CPU quotas can constrain runtime
without changing the visible CPU count.

The reference scores every candidate without a deadline. Trial cases use the
existing 0.9-second shared semantic/reranking budget. An in-progress batch is not
preempted, so observed latency may exceed the budget. Reports preserve scored
counts, top-five row IDs, ranking overlap, runtime version and database identity.
Top-five overlap is a regression proxy, not evidence relevance or factual-answer
accuracy. A faster result that skips more candidates is not automatically better.
Confirm a candidate inside the actual container and review answers before changing
production retrieval settings. Do not pick a universal winner from a small sample.

### Exploratory owner-host sample, 2026-10-17

Completed all 12 combinations of 8/12/16/20 threads and batches 2/4/8, with two
measured repetitions of each of the three questions after warmup. Windows ONNX
Runtime used the active release's pinned library. Other station preparation was
running during parts of the sweep; case order was fixed. These results are not a
controlled production benchmark and do not justify a production setting change.

| Threads | Batch | Median ms, six requests | Minimum scored / 16 | Mean top-five overlap |
| --- | --- | --- | --- | --- |
| 8 | 2 | 972 | 12 | 0.867 |
| 8 | 4 | 1153 | 12 | 1.000 |
| 8 | 8 | 1284 | 16 | 1.000 |
| 12 | 2 | 1054 | 14 | 0.867 |
| 12 | 4 | 1185 | 12 | 0.933 |
| 12 | 8 | 1165 | 16 | 1.000 |
| 16 | 2 | 995 | 14 | 0.867 |
| 16 | 4 | 1017 | 12 | 0.867 |
| 16 | 8 | 1065 | 16 | 1.000 |
| 20 | 2 | 963 | 6 | 0.700 |
| 20 | 4 | 992 | 12 | 1.000 |
| 20 | 8 | 1160 | 16 | 1.000 |

Receipts: `data/cpu-tuning-sweep.jsonl` and the earlier small
`data/cpu-tuning-initial.jsonl`. The full reference, per-question observations,
warmups and setup costs remain in those ignored owner files. In particular,
20-thread/batch-two's lower latency accompanies less completed work and lower
ranking overlap. No thread-count winner or answer-quality improvement is claimed.

A separate pre-update learning HTTP probe observed 31.017 seconds to the first
checked text and 36.074 seconds to completion. It was one request during other
work, not a stable baseline. Receipt: `data/cpu-tuning-http-before.jsonl`.

An isolated candidate inference compatibility probe returned HTTP-equivalent
status 200, three checked chunks, and numeric stages: input 0.163 ms, retrieval
2180.011 ms, model selection 53.211 ms, generation-to-first-frame 6641.478 ms,
inference-entry-to-first-checked-text 10342.228 ms, total inference 12574.825 ms.
Receipt: `data/cpu-tuning-inference-probe.json`. It excludes HTTP/MCP startup and
is not comparable to the preceding request as a before/after speedup measurement.

A read-only active-release MCP status probe measured preflight 1415.902 ms and
child connection 1039.269 ms. It did not generate an answer. Receipt:
`data/cpu-tuning-mcp-status-probe.json`. Both startup overhead and generation wait
deserve investigation; this evidence does not justify simply increasing threads.

The updated sweep worker also completed a full reference plus batch-four and
batch-eight compatibility probes inside the isolated Linux candidate, reporting
eight requested/configured/actual ONNX threads under its existing eight-CPU quota.
Receipt: `data/cpu-tuning-container.jsonl`. Other preparation could contend with
these probes, so they establish compatibility rather than a winning setting.

## Separate WSL maintenance plan

Prepared owner files are under `data/cpu-maintenance`: an exact original backup,
its SHA256 receipt, and a proposed `.wslconfig`. The proposal preserves the
48 GB memory limit and adds `processors=20`. The approved maintenance below was
completed on 2026-10-17; WSL now exposes 20 logical processors. The original
configuration remains available for rollback. No automatic shutdown is scheduled.

1. Arrange a quiet maintenance window; save/export open conversations and pause
   resumable owner jobs. Record active release, selected model, service identities,
   functional health and other running WSL distributions.
2. Compare the current `.wslconfig` checksum with the saved original. If it changed,
   merge the processor setting into that newer file rather than overwriting it.
3. Drain the active gateway using the updater's normal `stop(active_state)` path;
   do not force-kill in-flight requests. Replace `.wslconfig` with the reviewed
   proposal only after the drain succeeds.
4. Run `wsl --shutdown`. This interrupts all WSL distributions, model and voice;
   it is not an ordinary application update or zero downtime.
5. From this working checkout run `python scripts/releases.py start`. Verify WSL
   exposes 20 logical CPUs, the same model/voice image pins, selected model full
   GPU residency and functional station health. A cold model may need warming
   before readiness succeeds; follow `docs/UPDATES.md`. LAN requires a new login.
6. If the new processor limit causes problems, restore the backed-up config,
   repeat the maintenance shutdown/start, and verify the previous CPU count and
   service readiness. Keep the configuration/availability receipts.

Microsoft documents `.wslconfig` as global WSL2 configuration applied when the VM
starts, and warns that shutdown affects all distributions:
https://learn.microsoft.com/en-us/windows/wsl/wsl-config

## Completed validation and activation

Active release: `690d8bcbedcd4ff2a0f710b8fedaaa83`; previous:
`a4b76072c191467b86de8dac5eced963`. Its isolated source is based on the prior
active payload with only the six reviewed runtime/benchmark/test files changed.
Unrelated checkout changes were excluded. The initial superseded candidate
`e599f8d24f2945de9958dd115295544f` was never activated; its redundant scan was
cancelled after the thread-reporting correction. Its partial scan is not a pass.
No frozen payload or scan receipt was edited to incorporate that correction.

The final candidate passed Python tests, all nine shared Node suites, isolation
probes and all 70 scan targets. Its scan gate retained the same 11 reviewed MCP
issues; overall station health remains degraded only for `security_scan: warning`.
This is regression evidence, not a clean security audit. Independent code review
approved the corrected requested/effective thread reporting. Focused public tests
and the complexity gate passed; three mocked maintenance success/refusal/rollback
tests also passed. No live recovery failure was injected.

Normal application activation drained requests and briefly rebound gateway ports;
model and CPU voice image IDs and start times were unchanged at that phase.
The subsequent, separately scoped WSL maintenance intentionally restarted those
services. Its interval from drained gateway through verified recovery was 139.891
seconds, not a continuous external availability measurement. It preserved the
48 GB memory limit, model/voice image pins, bindings, authentication and owner
data. Only Larpus was running in WSL before shutdown. Restored 3.8 has full GPU
placement and the existing 131072-token context. WSL `nproc --all` reports 20.

Post-maintenance live HTTP probes confirmed timing fields across MCP and the
streaming `done` event. Two learning requests returned first checked text at
11.562 and 6.383 seconds (median 8.973). Different cache/load conditions and the
small sample prevent attributing a speedup to this work. CPU retrieval stays at
eight threads and batch four; no quantized model or dependency was installed.
Synthetic CPU voice synthesis returned audio with HTTP 200. CA-validated LAN
unauthenticated API access returned 401. LAN sessions need another login after
the gateway restart. Physical browser rendering and microphone acceptance were
not performed. No commit or push was made.

Owner receipts: `data/cpu-tuning-workspace.json`,
`data/cpu-tuning-prepare-final.log`, `data/cpu-tuning-activation.log`,
`data/cpu-tuning-after-activation.json`, `data/cpu-maintenance/maintenance.json`,
`data/cpu-tuning-post-maintenance.json`, and `data/cpu-tuning-http-after.jsonl`.

## Native-code experiment

The [October 17 C/AVX2 experiment](NATIVE_RETRIEVAL_SPIKE_2026_10_17.md)
keeps NumPy: the Windows AVX2 scorer lost to NumPy with eight requested threads,
and Linux vector scoring represented only about 0.15% of measured retrieval
augmentation. The report separates operating systems, correctness checks and
timing limits. No native scorer was installed in production.

The [October 18 C and handwritten assembly follow-up](NATIVE_ASSEMBLY_EXPERIMENT_2026_10_18.md)
found a repeatable Windows scoring gain using parallel float16-input kernels:
about 1.27 ms versus 2.42–2.46 ms for NumPy at eight threads. The stored index
values are preserved. The subsequent [Assembly pipeline integration](ASSEMBLY_PIPELINE.md)
records Linux measurements, the owner-approved near-tie policy, the HUD NumPy
switch and deployment evidence. Revised Linux scoring saved approximately 1 ms
in two runs; a complete-chat latency improvement has not been established.

The [further 5900X tuning pass](CPU_TUNING_FOLLOWUP_2026_10_18.md) compared worker
counts, dispatch/affinity, loop unrolling, packed rows and a native cutoff heap.
Its final candidate saved only 1.5–4.2% over deployed Assembly in direct runs;
the added native complexity was rejected and the existing implementation retained.

The [cache and dispatch follow-up](ASSEMBLY_CACHE_TUNING_2026_10_18.md) records
small additional scoring gains, rejected prefetch/alignment experiments and
CPU-quota limits; it does not establish a chat latency improvement.

The separate [1 ms experiment](ASSEMBLY_1MS_EXPERIMENT_2026_10_18.md) tested
ten handwritten variants and held-out workloads. It missed the target and
retained the deployed implementation; tied-duplicate reference limits are recorded.

The [hardware counter profile](HARDWARE_COUNTER_PROFILE_2026_10_18.md) now
measures grouped PMU events and replicated working-set sensitivity. It leaves
production unchanged and separates memory-hierarchy evidence from silicon-quality claims.
