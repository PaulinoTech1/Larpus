# Failure-isolation production update — 2026-10-20

Owner scope: failure isolation only. Execution profiles and the MCP Skills
extension remain unpromoted. No latency or answer-quality acceptance claim.

## Candidate and source

Activated release `042f91c0a1454887a694c945f49237ad` is based on the previous frozen
release `7df2e957751642d6ace4630fa047fe94`, rather than the full experimental
checkout. The owner staging source retains the production corpus, persona
prompts, broker prompt pins, transport, UI controls and configuration. Its
27 changed payload files implement the scoped catalog/retrieval/scorer behavior,
shared root imports, corresponding tests and the catalog-count notice. The
gateway schema and catalog formatting are factored to fit the existing
production complexity ceilings. No allowance or new-function cap was raised.

The owner updater extends the isolated-suite deadline from 180 to 600 seconds
and reads the frozen candidate's UI manifest in a separate process. It does not
omit or relax a test. The text source delta is retained
in [the deployment patch](releases/failure-isolation-2026-10-20.patch); the
frozen release manifest records the actual payload hashes. This patch describes
the production variant; the branch also retains its earlier experimental code.
The patch uses zero-context unified hunks (`git apply --unidiff-zero` against
a separate copy of the recorded baseline). Its normalized text was reproduced
and compared across all 27 changed files; SHA256 is
`c5bc3cb3f6532d67ca9d8875d54c03d19492a7aae0837706a73d8576577bc72d`.
Never apply it directly to a frozen release.

## Preparation record

The station was initially stopped. Owner-authorized `releases.py start` restored
the selected release and existing model/CPU voice before preparation. Required
health checks passed; the existing security-scan warning remained visible.

First candidate `ce4cc024edb94d14a522c1b2c971f827` built and passed pipeline
switching, but its test command exceeded the 180-second deadline. It was never
activated. Its snapshot and failure log were retained, and only its three
unused execution containers were stopped. The model, voice and serving gateway
were left running. A fresh snapshot was staged after extending the deadline.

Second candidate `320a1e34cc654ce3b9863c0c09250f30` passed its isolated Python
suite, companion contracts and ten UI suites. Preparation then refused the
checkout's eleventh, unpromoted execution-profile UI suite, which is absent
from the scoped candidate. A red/green regression proved the updater was reading
the wrong source's manifest. Its fix and regression passed all 31 owner-release
tests. The rejected snapshot/log were retained; only its three unused execution
containers were stopped. The next candidate independently repeats preparation.

Review also reproduced a valid-JSON `null` persona crashing catalog loading.
The dictionary check now rejects that named persona while retaining valid
personas. Six null/list/scalar cases passed, with red/green evidence. Independent
source review approved the fix and the scoped gateway adaptation.

The first broad direct-checkout unittest invocation was not a passing gate:
475 tests, three skips, one failure and five errors. It exposed two stale
test fixtures (scorer retry state and the new partial skill catalog), plus
host/isolation-environment errors. The fixtures were corrected without changing
runtime DLP, retrieval, MCP authorization or isolation. The configured isolated
runner then passed: 476 tests, four skips. After the later updater fix, all 31
release tests and the unchanged complexity gate passed. The final frozen
candidate's preparation remains the deployment gate.

## Deployment and verification

Final preparation passed the isolated local suite (321-test inventory), 29
companion catalog contracts, all ten UI suites, scorer switching/restoration,
and all isolation probes. The frozen complexity gate passed: 532 functions,
78 modules, unchanged production allowances. Static scanning completed all 70
targets: 69 clean skills and the exact same 11 reviewed MCP findings. The
warnings remain in the actual receipt; this is not a clean-scan or independent
security-audit claim.

The prepared payload, deployment and scan pins were validated before activation.
The synthetic live broker check passed: chat completed 4.063 seconds after
background preemption, cancellation recovery was confirmed, notes resumed with
`done_reason=stop`, and the broker returned idle and unfaulted. The owner-local
harness copy changed only the synthetic job's hard-coded model tag to the
already-selected `larpus3.8:27b-q4`; no model switch was performed. No owner
writer was running or restarted.

`python scripts/releases.py activate 042f91c0a1454887a694c945f49237ad` succeeded.
`active.json` read-back reports it running, with
`7df2e957751642d6ace4630fa047fe94` retained as previous and no pending cutover.
No rollback was needed; an actual rollback was not exercised. The updater
stopped the previous execution containers while retaining their images and
snapshots for rollback. Explicit return remains `python scripts/releases.py rollback`.

The model and existing CPU voice retained their exact images and start times
through preparation and activation. Gateway bindings, authentication, shared
dependencies and owner state were not changed. Activation took 30.374 seconds
as a whole command, including readiness and pruning; that is not port downtime.
Across 1,848 catalog HTTP samples, two failed during cutover. The surrounding
successful samples were 3.729 seconds apart. This sampled bracket does not
measure exact port downtime or prove continuous availability of every API.
There was a brief rebind, not zero downtime. LAN sessions need a fresh login.

Post-activation checks passed:

- Catalog: HTTP 200, 12 personas, 69 skills, zero rejected entries.
- Health: selected LARPUS 3.8 fully on GPU; Assembly optimized still selected.
- Chat: HTTP 200 in 8.656 seconds; streaming: HTTP 200 and a terminal `done`
  frame in 9.984 seconds. These are single functional checks, not benchmarks.
- CPU speech: HTTP 200, valid 86,572-byte RIFF/WAV, 2.672-second request.
- Unknown persona remained HTTP 400; filtered instruction text remained 422.
- Existing-CA-validated home-LAN request without authentication remained 401.
- Required station-health checks passed; overall status remains degraded only
  for the retained static-scan warning.

Private logs and numeric receipts remain ignored: `data/failure-isolation-*`,
including preparation logs, service continuity, broker live checks, API checks,
activation timing and the availability summary. The rendered HUD, physical
microphone, second-device login, sustained workload and answer quality were not
verified. Browser inventory exposed no connected browser surface; no HUD was
opened. The latency screen was not rerun. No critic, MCP session reuse, or
fault-closed fallback was introduced. Failure containment remains 3.

## Owner HUD pass (about two minutes)

1. In an already-open HUD tab, confirm its existing conversation is still there.
   Lost transcript or a forced clear is a bug. LAN tabs need a fresh login after
   the gateway process changes; this is the existing session limitation.
2. In a separate tab, open `http://127.0.0.1:8080/`. Check that the persona and
   skill selectors populate, the conversation area renders, and no unexpected
   catalog-rejection notice appears for the intact production catalog.
3. In that separate tab, enter `Give me one short evening planning suggestion.`
   in **Message larpus**, then press **Send message**. Expect a completed reply
   and working controls. Partial text presented as a completed reply is a bug.

This pass does not corrupt production files to manufacture a rejection. Those
faults belong to the isolated tests. Human/device acceptance is pending until
the owner reports a verdict; deployment and automated checks do not establish it.
