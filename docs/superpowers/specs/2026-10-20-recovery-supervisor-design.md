# Independent recovery supervisor and failure drills

Date: 2026-10-20. Status: owner approved the written design on 2026-10-20.
Implementation-plan review and execution-method selection are next; production
installation and arming remain separate rollout actions.

## Intent and scope

The owner selected recovery plus failure drills before broader data recovery.
The goal is predictable recovery from a gateway process crash while keeping
healthy services running and preserving every existing security refusal.
Containment, recovery time and data preservation must be demonstrated rather
than inferred from a listening port or a green unit suite.

This is an architectural change. This document authorizes no installation,
background task, fault injection, runtime change, deployment, commit or push.
After written-design approval, a separate implementation plan must define the
execution and verification steps.

The production reference is the failure-isolation release described in
[the deployment record](../../FAILURE_ISOLATION_RELEASE_2026_10_20.md).
Implementation must recheck the selected release; an ID in this document is
not permission to overwrite a later selection. Experimental execution profiles
and MCP Skills remain outside this change.

## Existing mechanisms to reuse

- `scripts/releases.py`: immutable-payload validation, process identity checks,
  Windows management lock, selected bindings, launch and readiness checks.
- `runtime/health.py`: gateway-owned monitor and bounded health report. The
  report is periodic, not a fresh observation of every dependency.
- Broker state: active lane, waiting work and cancellation fault fence.
- Existing refusal and history contracts: incomplete text is not committed as
  a finished turn; ordinary inference has no direct/cloud or CPU-token fallback.
- Existing NumPy/BM25 substitution and prepared-release rollback mechanisms.

The supervisor must not call the current general `start` command as its crash
action. That command can start model/voice/execution services and recover a
pending cutover. Automatic gateway recovery needs a narrower operation.

## Architecture and authority

Use one owner-side Windows process independent of the gateway. It has no model
tool, MCP exposure, new listener, remote-control endpoint or cloud dependency.
Its executable and dependencies remain the existing approved owner environment.
An owner launcher may start it hidden; installing a scheduled startup task is a
separate, explicit rollout action. Version 1 is disabled until the owner arms it.

Separate three small responsibilities:

1. Observation adapter: fixed, bounded reads of process identity, HTTP state,
   selected dependency state and owner-management state.
2. Decision function: observations plus durable history produce one reasoned
   action. It performs no I/O and supports deterministic fake-clock testing.
3. Recovery executor: obtains the existing management lock, repeats the safety
   checks, records the attempt durably, and launches only the validated gateway.

The first version automatically recovers only a confirmed dead gateway.
Alive-but-unresponsive gateways, dead execution containers, stopped WSL,
unloaded models, GPU problems and voice failures are observed and held for owner
action. They are not grounds to restart healthy neighbors. Expansion to another
component requires a separate reviewed recovery rule and a passing drill.

## Observation contract

Observe on a proposed five-second interval, with one cycle at a time, bounded
timeouts and no accumulating probe queue. Record observation age and timeout
separately from a negative result. A probe error is unknown, not proof of death.

Keep these dimensions distinct:

| Dimension | Evidence | Interpretation |
| --- | --- | --- |
| Process identity | Recorded PID, creation identity and fixed command line | Exact match alive; absent process confirmed dead; reused PID held |
| HTTP service | Bounded owner-loopback probe of the selected listener | Responding, refusing admission, unreachable, or unknown |
| Functional readiness | Selected-release health with generation identity and freshness | Required gates pass, failed, or stale/unknown |
| Dependencies | Fixed container/image identities and fresh read-only broker state | Ready, busy, faulted, unavailable, or unknown |
| Owner intent | Armed/disabled state, maintenance state, management lock and cutover journal | Recovery permitted or suppressed |

A fresh health receipt must identify the release and gateway process generation.
Validate its producer identity and age; the presence of a recent file alone
cannot establish that a replacement gateway is ready. Additive receipt fields
must preserve existing HUD/API consumers. Health polling must not generate model
answers, take the inference slot, bypass isolation or rerun heavyweight scans
every five seconds. The prepared integrity and scan gates remain mandatory.

The reviewed scan warning alone never triggers recovery. Missing or failed
mandatory security evidence is held, not treated as an ignorable warning.
Fresh broker state is required at the action boundary; a cached healthy report
does not clear a cancellation fence.

## Decision states and recovery algorithm

States: disabled, observing, suspect, waiting, recovering, cooldown and held.
Every state carries a fixed reason code and timestamp. Unknown evidence prevents
action. A healthy observation clears a transient suspicion, not a durable hold.

Proposed initial policy:

- Require three consecutive confirmed-dead observations of the same selected
  gateway generation. A change of selection or identity restarts observation.
- Under the management lock, reread selection, owner intent, pending cutover,
  process identity, listeners, dependency identities and broker state.
- If any required dependency is busy, wait without cancellation, restart or
  spending an attempt. If it is faulted or its state is unknown, hold.
- If a pending cutover exists, defer to the owner updater. Never infer which
  release should win or invoke rollback automatically from the supervisor.
- If a configured listener is occupied unexpectedly, hold. Never kill its owner
  or launch a second gateway alongside it.
- Validate the selected prepared release and its existing deployment/scan pins.
  On drift, hold. Never reseal, rewrite pins or choose a different release.
- Persist an attempt reservation before launching. If the journal cannot be
  written safely, do not launch. Reuse the validated owner launch primitive;
  preserve bindings and authentication and start no containers.
- Require fresh process-generation-specific functional readiness. If readiness
  fails, use the ordinary bounded drain for this exact newly launched process;
  never force-kill or leave an untracked second launch. Cleanup uncertainty holds.
- Allow at most two launch attempts in a rolling ten-minute window. Wait at
  least 60 seconds between attempts, with bounded 0–10-second jitter. Persist
  history so restarting the supervisor cannot reset the limit.
- On exhaustion, enter durable held state. Owner acknowledgement permits
  reevaluation; it does not waive safety checks or erase the broker fence.

These timing values are proposed policy defaults, not measured recovery
guarantees. Deadline tests use a monotonic clock; restart-safe attempt history
also records wall-clock information. Clock reversal or ambiguous persisted
time must conservatively hold rather than create unlimited attempts.

## Intentional shutdown, maintenance and singleton behavior

Store owner supervision intent outside frozen payloads. An intentional shutdown
must persist disabled intent under the management lock before draining anything.
The supervisor must never interpret a deliberate shutdown as a crash.

Existing drain markers, pending cutovers and maintenance intent suppress action.
The supervisor must not clear them. Installation remains disabled until the
documented shutdown/start workflow participates in this intent contract.
Reboot does not itself grant permission to arm recovery or start WSL/model/voice.

Use a separate supervisor singleton lock. A second supervisor exits without
mutation. Deployment uses the existing management lock; the supervisor never
holds it while sleeping between observations. A crash while an attempt is
reserved leaves a durable reservation. On restart, reconcile exact process and
listener identities before any new attempt; ambiguity holds.

## State durability and visibility

Owner-local supervisor state records schema version, selected release/gateway
identity, armed state, state/reason, observation ages, attempt history and last
recovery result. Use bounded files, owner-only access and atomic replacement.
Reject redirected paths and malformed state. Do not include prompts, replies,
credentials, raw subprocess output or source passages.

Expose state through an owner CLI even when the gateway is down. A compatible
HUD status may read a bounded snapshot while the gateway is up. A stale or
unreadable supervisor report must never appear healthy. If writing state fails,
emit a fixed owner diagnostic when possible and take no recovery action.

Broader backups and transactional note/conversation changes are deferred. This
phase tests the supervisor journal and selected existing commit contracts; it
does not claim all owner data is crash-safe or replace a backup/restore plan.

## Failure drills and acceptance evidence

Use isolated stores, synthetic records, dedicated loopback ports and explicitly
identified disposable candidate processes. No mutation of production selection,
owner data, active payloads or frozen receipts. A harness must refuse production
identities and uncertain process/container ownership before injecting faults.
Do not stop the shared model or CPU voice. Use injected adapters for dangerous
dependency/fence/disk conditions. Live drills must name exactly which disposable
gateway they may terminate; no broad process-name killing.

| Fault | Required result | Evidence |
| --- | --- | --- |
| Disposable gateway exits | Supervisor survives; only that selected test gateway is restored | Independent supervisor identity, one launch, fresh readiness, elapsed recovery time |
| Retrieval worker becomes unavailable | Existing BM25 path still answers with approved evidence | Worker failure plus successful retrieval/chat contract; no model or voice restart |
| Cancellation cannot be confirmed | Admission stays refused; supervisor cannot clear it by restarting broker or gateway | Persistent fence, zero recovery launches while fenced, explicit held reason |
| Stream disconnects halfway | No completed history entry and no automatic second generation | Partial stream, browser/history contract, generation counter |
| Disk fills during journal replacement | Previous committed journal remains readable; failed reservation prevents launch | Before/after content and hashes, explicit failure, zero side effects |
| Candidate fails readiness | Existing updater restores the previous disposable release | Selected IDs, process identities, readiness failure and restore receipt |

Additional mandatory cases: repeated probe timeouts; PID reuse; unexpected port
owner; stale health from a dead generation; missing dependency; intentional stop;
management-lock contention; selection change between probe and action; pending
cutover; supervisor restart mid-attempt; corrupted state; clock reversal; restart
budget exhaustion; diagnostic sink failure; and retained scan warning alone.

Report each drill independently as passed, failed, held or not run. Record the
injected fault, exact owned target, expected action, actual transitions, attempt
count, recovery/readiness timing and cleanup result. Preserve failed receipts.
Mocked tests, disposable-process drills and real-device acceptance are separate
evidence classes. Updater rollback tests do not imply that the supervisor itself
may roll back releases.

Acceptance requires zero lost committed synthetic records for the stores under
test, zero duplicate automatic generations, zero unnecessary restarts in the
negative cases, and enforcement of the durable attempt bound. Report measured
recovery distributions, not only a successful single run. Unproven stores and
platforms remain explicit limits.

## Rollout and remaining limits

Order: deterministic policy and adapter tests; disposable-process drills;
observation-only operation; review of false suspicions and probe overhead;
explicit owner arming of gateway-only recovery. Installation/arming and any
production fault drill need their own scoped rollout authorization. A normal
application update still follows stage, prepare, validate and activate.

Rollback begins by disabling supervision durably and stopping only the
supervisor, leaving the station alone. Preserve journal and drill evidence.
Never remove the owner shutdown contract while an armed supervisor can run.

This design does not provide host high availability, Windows/WSL restart,
automatic GPU/model/voice recovery, failover to a second model or host, automatic
deployment rollback, persistent LAN sessions across gateway changes, or general
backup recovery. It cannot restore service while its Windows host is down.
The subsequent data-recovery design must specify protected stores, backup
destination, encryption, retention and an independently demonstrated restore.
