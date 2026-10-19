# Broker cold-start recovery - 2026-10-19

## Root cause

**Probable original incident diagnosis; controlled service-restart evidence added below.** The recorded incident is
consistent with the broker's first scheduler probe running its cancellation
idle-fence request before the selected model has finished loading. `needs_probe`
starts true, so the first admitted slot probes with a one-token Ollama request.
If the model is not ready, the probe fails; slot cleanup tries the idle fence
again. If that fence also fails, the scheduler marks itself faulted and remains
fail-closed. The startup path previously launched the pod and then the agent and
gateway without first verifying the selected model's identity, context, or
complete GPU placement. Functional readiness happened later and could not undo a
genuine scheduler fault.

This sequence was reproduced with a controlled scheduler/fence simulation, not
with the live GPU. With the original code:

| Case | Simulated observations | Result |
|---|---|---|
| A - healthy startup | Initial fence succeeds | First slot succeeds |
| B - cold model | Initial fence and cleanup fence both fail | Request refused; scheduler faults closed |
| C - delayed readiness | Initial fence fails, next fence succeeds | First request refused; scheduler does not fault |
| D - permanent model failure | Both bounded fence attempts fail | Scheduler faults closed |
| E - interrupted generation | Cancellation fence fails after interruption | Scheduler faults closed; new inference remains blocked |

These outcomes support the startup-order diagnosis but do not establish the
behavior or timing of a real model cold load.

## Code changes

- `scripts/releases.py` now checks the broker's two private Unix sockets and
  scheduler state, then validates the approved local model selection before
  starting voice, notes, agent, or gateway processes. It reuses the existing
  owner-side model backend for a bounded local warm-up when the selected model
  is not loaded, and verifies model identity, context, and full GPU residency.
  An active notes-maintenance phase defers cold warm-up. A faulted or busy
  broker is not reset or interrupted. Startup writes the active pointer only
  after functional readiness succeeds; a failed readiness check drains the
  newly launched gateway and leaves the old pointer intact.
- `runtime/model_backend.py` supports bounded readiness requests and validates
  the exact selected model and placement fields. Partial GPU placement is
  distinguished as pending so startup can poll until its deadline.
- `runtime/gateway.py` and `runtime/model_routes.py` keep protected API routes
  unavailable until the owner readiness marker is written. Authentication
  remains checked first; station-health remains available to the owner
  readiness poll.
- `tests/test_releases.py`, `tests/test_broker_scheduling.py`,
  `tests/test_model_switch_regressions.py`, and `tests/test_gateway.py` cover
  cold/delayed/failed readiness, model identity and placement, cancellation
  fail-closed behavior, startup ordering, active-pointer preservation,
  authentication, and the gateway readiness gate.

The scheduler's `needs_probe`, `probe`, `slot`, cancellation fence, admission
policy, model-switch policy, and model/inference settings were not changed.
No model, broker, MCP, security-scan, network, authentication, or container
authorization boundary was bypassed.

## Tests

Validation used the configured project interpreter, Python 3.10.10:

| Command | Result |
|---|---|
| `python -m unittest tests.test_releases tests.test_broker_scheduling tests.test_model_switch_regressions tests.test_gateway` | Pass: 68 tests; 1 skip |
| `python scripts/test-local.py` | Pass: 378 tests; 2 skips |
| `python scripts/verify-broker.py --output data/broker-cold-start-synthetic.json` | Pass: Windows synthetic fixtures |
| `python scripts/complexity.py check` | Pass: 624 functions, 92 modules |
| `python -m py_compile ...` on modified runtime and test modules | Pass |
| `git diff --check` | Pass |

The focused scheduler skip and one full-suite skip are the real Unix capability
socket test (`requires Linux`); the other full-suite skip is the published-notes
test (`no published notes`). The broker receipt records
`unix_socket_verification: not_checked`. Linux socket behavior is therefore
**not verified** here. Small readiness-route and failed-start cleanup checks
were rerun after the full suite and passed.

No security scanner or release preparation was run. Existing documentation
records 11 reviewed MCP findings; this repair does not clear or reclassify
them, and the scanner was not used to claim a clean result. The local regression
suite retains existing release rollback, pending-cutover, source-integrity,
container authorization, and gateway PID identity coverage.

## Security

Verified in local tests: API authentication remains required while the startup
gate is closed; authenticated inference and protected GET routes return 503
until readiness is marked; station-health remains available for the readiness
poll; no model call occurs while the chat gate is closed; broker cancellation
faults remain fail-closed; broker sockets must be private sockets owned by the
expected UID; only a catalog-approved selected model can be warmed.

Not verified: live Linux Unix-socket behavior, a real GPU/model cold load,
physical GPU placement, a Windows/WSL restart, live first chat, or a fresh
security scan. No security finding is represented as resolved by these tests.

## Runtime

At the original code-only checkpoint, no real cold-start, model-readiness,
broker-readiness or first-chat timing was collected. The synthetic broker receipt
took 0.485 seconds on Windows; this is harness time, not runtime measurement.

## Release status and rollback

The initial readiness code was committed as `363f085`. Later controlled restart
evidence and a scoped owner-startup correction are recorded below.
The checkout baseline was `f81635976458990e0782addfec4c75b734db1301`; the active
frozen release remains `7df2e957751642d6ace4630fa047fe94`, with
`f08b98ea2f34407cb77dc79aa7d7866a` recorded as previous and no pending cutover.
The running gateway was confirmed against the active release after testing.
At the original synthetic-test checkpoint, no frozen payload was edited, prepared,
activated or rolled back, and no service was stopped. The code was subsequently
committed and published; that does not establish production activation.

No rollback is needed because production selection did not change. Retain the
existing frozen release directory and payload untouched. If an owner-authorized
future activation must be reversed, use the existing
`python scripts/releases.py rollback` operation; it restores the previously
selected release through the release manager rather than modifying either
release payload.

## Unresolved problems and acceptance

At the code-only checkpoint, the cold-start diagnosis remained probable pending an authorized
maintenance session verifies model identity, complete GPU residency, context
131072, both broker sockets, first chat, and normal operation after a real
shutdown/start cycle. Do not restart the active broker or perform that test as
part of this code-only repair. A cold warm-up is explicitly deferred while the
nightly notes maintenance marker is active. No other cold-start issue was
confirmed by these synthetic tests.

## Authorized follow-up: controlled model-pod restart

The owner subsequently requested completion of the outstanding tasks. Private
receipt `cold-start-live.json` records a drained gateway and stopped/restarted
model pod, preserving the selected baseline, model/voice images, binding and auth.
The selected `larpus3.8:27b-q4` reported size and VRAM both 20,862,835,097 bytes
and context 131072. Both private broker sockets passed readiness; the scheduler
was idle and unfaulted before and after the first chat. The greeting completed
with HTTP 200, first text 11.202 seconds and total 11.504 seconds.

Elapsed checkpoints from the test's beginning were drain 5.918 seconds, pod
stopped 69.336, functional readiness 217.085 and final verification 230.497.
These include owner checks and service transitions; they are not model-load time.
The selected frozen gateway lacks the new HTTP admission gate, so this validates
owner prewarming/broker readiness and first chat, not live activation of that gate.
Full Windows/WSL power-cycle behavior and original-incident causality remain unproven.

The first follow-up exposed another lifecycle defect: `pod start larpus-offline`
revived historical retained containers. The shutdown verifier refused its original
image-only scope rather than silently stopping unknown names; that failed receipt
is retained. The revised cleanup separately verifies the fixed offline pod's ID,
network-none scope and member names, plus exact image pins for outside services.
Owner `releases.start()` now starts only `larpus-model` (which brings up its pod
infrastructure), the selected broker/notes services, voice and agent. Idle broker
and model checks still precede gateway admission. Regression assertions failed
against whole-pod startup before the correction. No frozen payload or pin changed.

## Corrected start-from-stopped acceptance

Private `scoped-start-live.json` begins with an empty running-container inventory.
The corrected owner startup produced exactly five selected LARPUS services plus
their pod infrastructure: model, baseline broker, baseline notes client, pinned
CPU voice and baseline agent. No historical container started. Functional
readiness completed 136.302 seconds from the helper's beginning, including
validation/WSL startup; the whole check took 148.973 seconds. These are single
observations, not boot-speed guarantees or directly matched restart comparisons.

Model size/VRAM both remained 20,862,835,097 bytes, context 131072. Broker state
was idle/unfaulted before and after a successful first greeting: HTTP 200,
first text 10.031 seconds, total 10.231 seconds. Selection remained
`7df2e957751642d6ace4630fa047fe94`; no candidate activation or model replacement
occurred. The final local regression ran 398 tests successfully with four
documented skips. Complexity checks retained the existing thresholds.

The service-restart acceptance is complete within this scope. Original-incident
causality, a full Windows power-cycle, live candidate HTTP admission-gate behavior,
browser rendering and second-device sessions remain unverified. The earlier
whole-pod receipt and refused cleanup attempt remain available alongside the
corrected check; neither was relabeled or overwritten.
