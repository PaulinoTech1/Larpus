# Independent Recovery Supervisor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recover a confirmed dead gateway through a bounded owner-side supervisor and demonstrate safe recovery using disposable failure drills.

**Architecture:** A pure decision module consumes typed observations and durable history. Separate journal and Windows adapter modules handle persistence and fixed owner operations; a CLI supplies singleton supervision, owner intent and visibility. Reuse the existing release lock and validation/launch mechanisms without invoking general station startup.

**Tech Stack:** Existing Python standard library, Windows process identity and file locks, fixed WSL/Podman observation commands, unittest, existing Node UI contracts; no added dependencies.

**Spec:** [Approved design](../specs/2026-10-20-recovery-supervisor-design.md). Read both documents before execution.

## Global Constraints

- Implementation is pending owner review of this plan and execution-method selection.
- Version 1 automatically recovers only a confirmed dead gateway; all other component recovery is held for owner action.
- Five-second observation interval; three consecutive confirmed-dead observations of the same selected generation.
- At most two launches per rolling ten minutes; at least 60 seconds between attempts, plus bounded 0–10-second jitter.
- Defaults are proposed operating policy, not measured recovery-time guarantees.
- Disabled until explicitly armed; reboot and supervisor restart do not arm it.
- Preserve broker cancellation fences, integrity/authentication/DLP gates, fresh MCP sessions, model/voice identities and active requests.
- No new model tool, listener, network service, cloud dependency or shared dependency replacement.
- No production fault injection, installation, scheduled task, arming, activation, commit or push without the corresponding owner scope. Task boundaries below are review checkpoints, not automatic commits.
- Keep production running; never edit frozen payloads, deployment pins or scan receipts. Preserve unrelated files and the unpromoted-feature boundary.
- Never raise `config/complexity-baseline.json` allowances or its new-function cap.
- Use synthetic data and dedicated disposable stores/ports for drills. Shared model and voice must not be stopped.

## File Responsibilities

| File | Responsibility |
| --- | --- |
| `scripts/recovery_policy.py` | Typed observation/history/decision records and pure transition policy |
| `scripts/recovery_state.py` | Strict bounded journal, durable owner intent, attempt reservation and singleton lock |
| `scripts/recovery_backend.py` | Fixed Windows observations and lock-protected gateway-only recovery |
| `scripts/supervise.py` | Owner CLI, one-cycle/watch orchestration and redacted status |
| `scripts/releases.py` | Reusable readiness/launch integration and maintenance suppression contract |
| `runtime/health.py`, `runtime/gateway.py` | Additive gateway-generation-specific health identity |
| `scripts/recovery_drills.py` | Disposable-process harness, fault ownership checks and numeric receipts |
| `tests/test_recovery_*.py` | Policy, state, adapters, CLI and drill contracts |
| `docs/RECOVERY_SUPERVISOR.md`, `docs/UPDATES.md` | Owner operation, evidence classes and later rollout record |

Use the existing `scripts` package and unittest patterns. Keep production commands
fixed; test injection belongs in Python adapter constructors and the disposable
harness, not caller-selected executables or arbitrary production stores.

## Shared Interfaces

Define frozen dataclasses in `scripts/recovery_policy.py`:

- `Policy(interval_seconds=5, dead_threshold=3, attempt_limit=2, window_seconds=600, cooldown_seconds=60, jitter_max_seconds=10)`.
- `GatewayIdentity(release_id: str, pid: int, creation: str, command_sha256: str)`.
- `Observation(identity: GatewayIdentity | None, process: str, http: str, readiness: str, dependencies: str, broker: str, suppression: str | None, wall_time: float, monotonic_time: float)`. Process values: `alive/dead/reused/unknown`; HTTP: `responding/refused/unreachable/unknown`; readiness: `ready/failed/stale/unknown`; dependencies: `ready/busy/failed/unknown`; broker: `idle/busy/faulted/unknown`.
- `History(armed: bool, state: str, reason: str, identity: GatewayIdentity | None, dead_count: int, attempts: tuple[float, ...], last_wall_time: float, next_attempt_wall_time: float, reservation: dict | None)`.
- `Decision(state: str, reason: str, action: str, dead_count: int)`, where action is `none/recover` and state is one of the seven states in the spec.
- `decide(observation: Observation, history: History, policy: Policy) -> Decision` performs no I/O. Reasons use a literal closed set. Recovery eligibility is a proposal; the executor must recheck under lock.

The journal serializes these records with schema `version=1`, a maximum 64 KiB,
and at most two in-window attempts. An in-flight reservation also stores its
attempt ID and the new process identity as soon as available. Retain monotonic
cooldown information in-process; after restart conservatively reconcile wall
time and hold on clock ambiguity. Status uses enum values, IDs, numeric times
and counts, never raw exception/subprocess text.

## Review Focus

1. An operator intentionally shuts down the station while a recovery cycle is already queued: no resurrection (Tasks 3–4).
2. The supervisor crashes after launching but before updating the active pointer: no second gateway or cleared budget (Tasks 2–3).
3. Health from the previous gateway looks recent: replacement is not declared ready from another generation (Task 3).
4. State replacement fails or the clock moves backward across restart: previous committed state survives and no launch occurs (Tasks 1–2).
5. The test harness receives a real production PID/store or a reused test PID: injection is refused before signaling anything (Task 5).

## Task 1: Pure decisions and bounded recovery policy

**Files:** Create `scripts/recovery_policy.py`, `tests/test_recovery_policy.py`.

**Interfaces:** Produces the dataclasses and `decide` defined above; consumes no runtime modules or services.

- [ ] Write `test_only_third_confirmed_death_proposes_recovery`: with armed history and ready/idle dependencies, counts 1 and 2 yield `none`, count 3 yields `recover`; healthy/reused/unknown observations do not advance confirmed death.
- [ ] Write `test_refusals_and_warnings_never_become_restart_requests`: busy, faulted, stale, failed and unknown dependency evidence yield no recovery; a reviewed warning with otherwise ready dependencies does not trigger recovery of a live gateway.
- [ ] Write `test_budget_cooldown_selection_and_clock_boundaries`: two attempts in 600 seconds hold; before `next_attempt_wall_time` no launch; identity change resets suspicion; durable held state requires acknowledgement; backward time holds.
- [ ] Run `python -m unittest tests.test_recovery_policy -v`; confirm the new contract fails before implementation.
- [ ] Implement the exact interfaces and literal reason set. Fail closed on invalid enum values, nonfinite times and invalid policy values. Use injected time; no sleeps or randomness inside `decide`.
- [ ] Run the same module and `python scripts/complexity.py check`; require zero failures/regressions. Review checkpoint; commit only if separately requested.

## Task 2: Durable intent, reservations and singleton state

**Files:** Create `scripts/recovery_state.py`, `tests/test_recovery_state.py`.

**Interfaces:** Consumes Task 1 records. Produces `Journal(directory: Path)`, methods `read() -> History`, `write(history: History) -> None`, `reserve(identity: GatewayIdentity, now: float, jitter_seconds: float) -> str`, `record_launch(attempt_id: str, identity: GatewayIdentity) -> None`, `set_armed(armed: bool) -> None`, and `singleton()` context manager. Default owner directory: `data/recovery`; tests use temporary directories.

- [ ] Write `test_absent_journal_is_disabled_and_corrupt_journal_holds`: an absent journal defaults disabled; wrong types, oversized input, unknown schema and redirected paths refuse recovery rather than resetting history.
- [ ] Write `test_failed_replace_preserves_previous_commit_and_prevents_launch`: inject ENOSPC/permission/replace failures, verify the previous journal bytes remain valid, and verify no recovery callback runs.
- [ ] Write `test_restart_retains_reservation_budget_and_owner_disable`: reserve, reconstruct `Journal`, and assert the attempt still counts; disabled and held states persist; a second singleton cannot acquire authority.
- [ ] Run `python -m unittest tests.test_recovery_state -v` and record the failing assertions.
- [ ] Implement bounded reads, same-directory temporary writes, file flush/fsync and atomic replacement. Reuse the reviewed owner-only Windows ACL approach from `scripts/protect-quarantine.ps1` through a fixed adapter; do not broaden the quarantine helper's authority. Verify owner/SYSTEM access and reject unsafe path identities. On ACL, persistence or time ambiguity, hold.
- [ ] Run state and policy modules; require previous-content preservation, durable attempt accounting and no side effects on failure. Review checkpoint without automatic commit.

## Task 3: Fresh observations and gateway-only recovery

**Files:** Create `scripts/recovery_backend.py`, `tests/test_recovery_backend.py`; modify `runtime/health.py`, `runtime/gateway.py`, `scripts/releases.py`, `tests/test_releases.py`, `tests/test_skills_health.py`.

**Interfaces:** Consumes Task 1 and Task 2. Produces `Backend(root: Path)` with `observe() -> Observation` and `recover(expected: GatewayIdentity, journal: Journal, policy: Policy) -> dict`. The result contains fixed `state/reason/attempt_id/identity` fields. Production `root` is derived from the owner script, not accepted from the CLI; test backends are injected.

- [ ] Write `test_recent_health_from_other_generation_is_not_ready`: a fresh old-generation receipt must fail readiness for a newly launched process; existing response keys remain compatible.
- [ ] Write `test_gateway_recovery_never_calls_general_start_or_starts_containers`: absent exact gateway plus ready selected dependencies permits one validated launch; spies assert no general `start`, container start/stop, model warm-up, broker reset, cancellation or pruning.
- [ ] Write `test_lock_recheck_defeats_disable_selection_port_and_cutover_races`: change each condition after the proposal; each prevents launch under the management lock. Live PID reuse, missing process identity and uncertain listener ownership hold.
- [ ] Write `test_orphan_launch_reconciliation_and_cleanup_uncertainty_hold`: fail between launch and pointer publication; a later pass reconciles exact reserved PID identity and readiness, or holds without a second launch. Failed readiness drains only the owned new process; bounded drain failure holds without force-kill.
- [ ] Run the new backend tests and relevant existing release/health modules; require red evidence for new behaviors.
- [ ] Add an optional keyword `generation` to `health.check` and `health.start_monitor`, preserving existing callers. Gateway creates a random per-process token and supplies it to the monitor. Add `producer` with release ID, PID, generation token and monotonic check start/finish to its health receipt. In readiness, require matching release/PID, stable generation across confirmation reads, and a completed report produced after that launch. Reject stale/unknown producer state; never rewrite frozen payloads to introduce these fields.
- [ ] Implement `observe`: bounded exact-process/HTTP checks; required health pass list from the existing readiness gate; read-only selected dependency identities and broker state at action time. Confirm WSL is already running before WSL commands so observation cannot implicitly boot it. Unknown or stopped WSL holds. Do not generate tokens or rerun heavyweight scans per observation.
- [ ] Implement `recover`: acquire the existing management lock nonblockingly; reread all safety conditions; validate pins; durably reserve; invoke only the fixed gateway launch; persist the new identity before further waiting; require fresh readiness; publish the matching active process record atomically. On launch/publication uncertainty hold and preserve the reservation. Do not release the lock while an unrecorded launch could race deployment.
- [ ] Run `python -m unittest tests.test_recovery_policy tests.test_recovery_state tests.test_recovery_backend tests.test_releases tests.test_skills_health tests.test_gateway -v` and complexity checks. Existing bootstrap releases without generation receipts are unsupported for automatic recovery and must be held explicitly; ordinary owner startup compatibility remains tested.

## Task 4: Owner controls, observation mode and deliberate shutdown

**Files:** Create `scripts/supervise.py`, `tests/test_recovery_cli.py`, `docs/RECOVERY_SUPERVISOR.md`; modify `scripts/releases.py`, `docs/UPDATES.md` only to document tested behavior, not to claim deployment.

**Interfaces:** Consumes Tasks 1–3. Produces owner commands `status`, `watch`, `arm`, `disable`, and `acknowledge`; `disable --stop-gateway` is the sole combined persistent-disable/drain action. `watch --observe-only` never executes recovery. An injectable `cycle(backend: Backend, journal: Journal, policy: Policy, observe_only: bool) -> Decision` enables bounded tests. No arbitrary command, URL, release choice or production store arguments.

- [ ] Write `test_queued_cycle_cannot_resurrect_intentional_shutdown`: disable persists under the management lock before drain; a previously queued recovery proposal observes disable at its locked recheck and cannot launch.
- [ ] Write `test_observation_singleton_and_acknowledgement_do_not_waive_gates`: observe-only records intended actions without executing; second watch exits; acknowledgement does not clear broker faults or reset the attempt budget; disabled state survives reboot simulation.
- [ ] Write `test_pending_cutover_and_existing_drain_suppress_action`: internal updater drain remains temporary maintenance, not an automatic permanent disable or rearm. General owner startup does not arm supervision. Fresh active selection is observed after cutover rather than inferred from the old PID.
- [ ] Run `python -m unittest tests.test_recovery_cli -v`; confirm new behavior fails first.
- [ ] Implement the CLI and one-cycle watch loop with fixed five-second spacing and no overlapping cycles. Use the fixed 60-second cooldown plus injected bounded jitter from Task 2; persisted reservations store the chosen delay once. Cap diagnostics/state size and keep status readable when the gateway is down. Diagnostic sink failure cannot permit recovery.
- [ ] Document exact arm/disable/status/observe-only commands, held reasons and limitations. Do not add scheduled tasks or launch a production supervisor. Keep any HUD integration out of this phase: owner CLI visibility satisfies the approved requirement, and additive health fields preserve current tabs.
- [ ] Run CLI, backend and release tests plus complexity. Confirm only documentation/new code changed and production process identities are untouched. Review checkpoint without automatic commit.

## Task 5: Disposable failure drills and receipts

**Files:** Create `scripts/recovery_drills.py`, `tests/test_recovery_drills.py`; extend `tests/test_retrieval_worker.py`, `tests/test_broker_scheduling.py`, `tests/test_streaming.py`, `tests/test_releases.py`, `tests/chat-stream-ui.cjs` where an existing assertion does not already prove the required outcome.

**Interfaces:** Consumes Tasks 1–4. Produces `run_drills(workspace: Path, repeats: int = 5) -> dict` for an explicitly created harness-owned sandbox; CLI `python scripts/recovery_drills.py --output data/recovery-drills/report.json`. Harness creates a unique ownership receipt and synthetic stores/ports itself. A path supplied merely as output never grants control over processes or existing state.

- [ ] Write `test_refuse_production_or_reused_targets_before_signal`: production root/store/PIDs, unknown containers, missing ownership receipt and changed creation identity are rejected before termination or writes. Assert zero calls to model/voice stop adapters.
- [ ] Write six named drill contracts matching the approved table: gateway exit/recovery, worker miss/BM25, unconfirmed cancellation/refusal, truncated stream/no completed history or replay, ENOSPC/journal preservation, and failed candidate readiness/previous disposable release restored. Use fixed generation and committed-record counters, not reply keyword checks.
- [ ] Run `python -m unittest tests.test_recovery_drills -v`; preserve red evidence.
- [ ] Implement an independently spawned disposable supervisor plus owned gateway fixture on dedicated ephemeral loopback ports. Only explicitly owned fixture gateways may be killed. Use injected dependency/clock/storage adapters for dangerous conditions; do not stop or fault the shared production broker/model/voice. The rollback drill exercises the existing updater with a disposable backend/store; it does not give the supervisor rollback authority.
- [ ] For each scenario save `passed/failed/held/not-run`, target identities, expected action, actual transitions, attempt count, readiness/recovery times, committed records before/after, generation count and cleanup result. Label simulated adapters versus real disposable processes explicitly. Save no prompts, responses, credentials or raw subprocess text.
- [ ] Run all six scenarios five times, preserving every failure; report count/median/p95/max recovery time where meaningful, not a universal uptime claim. Require zero lost committed synthetic records, zero duplicate automatic generations, zero unnecessary negative-case restarts and no attempt-limit bypass. These are measured targets, not permissions to relabel a failed run.
- [ ] Run affected Python modules, `node.exe tests/chat-stream-ui.cjs`, `node.exe tests/session-ui.cjs`, and complexity. Review checkpoint before any owner observation run.

## Task 6: Integration review and separate rollout handoff

**Files:** Update `docs/RECOVERY_SUPERVISOR.md`, the design's evidence/status notes and `docs/UPDATES.md` with verified outcomes only.

**Interfaces:** Consumes the passing task evidence and produces an owner review package; no automatic installation or activation.

- [ ] Run `python scripts/test-local.py` and the configured UI suites, `python scripts/broker-prompts.py --check`, `python scripts/complexity.py check`, and `git diff --check`. Keep any unrelated baseline failure distinct and unresolved gates visible; do not increase allowances or disable tests.
- [ ] Review the complete branch against the approved spec, including the five Review Focus cases. Review source reachability/scanner inventories for the new owner modules and runtime health identity changes. No warning inventory change is automatically accepted.
- [ ] Collect the six repeated drill receipts and explicit limitations. Verify that there is no production supervisor process, scheduled task or armed journal. Preserve unrelated dirty files and keep private reports ignored.
- [ ] Present a scoped observation-only rollout proposal specifying the exact supervisor version/source, 30-minute observation window, fixed probes, CPU/request overhead measurements and stop procedure. A failed proposal/run does not permit recovery. Do not start this window without its owner authorization.
- [ ] After the observation evidence is reviewed, present the installation/arming proposal separately. Production-compatible runtime changes require a newly staged and prepared failure-only release; do not promote unrelated checkout features. Validate prepared status before authorized activation. No production crash drill is implied by arming.
- [ ] Before replacing or removing the new shutdown contract, durably disable supervision and stop only the verified supervisor. Preserve the journal; do not stop a healthy gateway, model or voice to uninstall the supervisor.
- [ ] Commit/push only when requested. Deployment, observation, arming, human acceptance and broad data recovery remain separately reported states.

## Self-Review

- Spec coverage: Tasks 1–4 cover policy, authority, fresh evidence, durability, intent and visibility; Task 5 covers all six drills plus unsafe-target rejection; Task 6 covers evidence and rollout.
- Interface consistency: all orchestration consumes the shared Task 1 records; persistence and execution use the same `Journal` and fixed `Backend`; the supervisor never calls general `start` or rollback.
- Review Focus: each of the five conditions has a named regression in its owning task.
- Scope: no supervisor installation, live fault, production activation, backup implementation or automatic dependency recovery belongs to plan approval.
- Execution recommendation: Native implementation with one independent whole-branch review, because the journal, lock and recovery interfaces are tightly coupled. Subagent-driven execution remains an owner-selectable alternative with task-by-task reviews.
