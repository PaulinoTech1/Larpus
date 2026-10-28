# Recovery execution ledger — 2026-10-20

2026-10-21 update: the scoped production candidate is now prepared, not activated.
Source commit was authorized separately. See [preparation and retained failures](RECOVERY_PREPARATION_2026_10_21.md).
Earlier entries below remain dated implementation evidence; their staging/commit
status is historical. Recovery remains disabled and backups synthetic-only.

This ledger corrects `docs/PROJECT_IMPROVEMENT_PLAN_2026_10_20.md` only where
fresh evidence differs. It is not approval to deploy, arm, commit, or fault
the serving station. Independent review is open: no reviewer has issued a
final verdict, and this session does not substitute one.

## Baseline read on this pass

| Item | Evidence |
| --- | --- |
| Main checkout | `E:\speedzone_MS\LARPUS`, branch `feat/secure-execution-profiles`, commit `a2f12c0` |
| Main dirty files, preserved | `docs/architecture/failure-isolation-outline.md`; untracked `New Text Document.txt`, `larpus-sensors.csv`, `docs/PROJECT_IMPROVEMENT_PLAN_2026_10_20.md`, `docs/NEXT_AGENT_EXECUTION_PROMPT_2026_10_20.md`, and the untracked recovery spec/plan |
| Recovery worktree | `E:\speedzone_MS\LARPUS-worktrees\recovery-supervisor`, branch `feat/recovery-supervisor`, same commit `a2f12c0`, uncommitted supervisor sources |
| Other worktrees, not used as the base | `latency-quality` at `61998c4`; `mcp-skills` at `d14c2b7` |
| Selected release | `042f91c0a1454887a694c945f49237ad`, previous `7df2e957751642d6ace4630fa047fe94` |
| Live gateway | pid 27572 listening on 8080, command line is that selected release. Not stopped |
| Execution profiles and MCP Skills | Prepared earlier, not promoted (`docs/UPDATES.md`) |
| `docs/STATUS.md` | Still the 2026-10-11 snapshot. It is not the live selection |

The recovery worktree also has small edits in `docs/UPDATES.md`, `runtime/gateway.py`,
`runtime/health.py`, `tests/chat-stream-ui.cjs`, and `tests/test_skills_health.py`.
Those stay. This pass does not revert them and does not treat them as reviewed.

## Feature state

| Feature | Production `042f91c0` | Main checkout | Recovery worktree |
| --- | --- | --- | --- |
| Failure-isolation scoping | Activated per `docs/UPDATES.md` | Outline edit only | Not this package |
| Execution profiles | Not promoted | Present at `a2f12c0` | Same commit, not the work |
| MCP Skills | Not promoted | Present, not activated | Same |
| Recovery supervisor | Not installed or armed by this work | Spec/plan untracked only | Uncommitted implementation |

## Findings

1. RuntimeError from launch/drain is mapped to a held reason in `scripts/recovery_backend.py` `_launch` and `_stop_held`. Regression: `test_release_runtime_errors_are_fixed_holds`.
2. A launch that cannot be recorded is stopped, and a failed stop becomes `cleanup-uncertain`. Regression: `test_unrecorded_launch_is_drained_and_uncertain_cleanup_holds`.
3. A broker fault observed under the management lock is held and is not cleared when the fault later disappears. Regression: `test_locked_broker_fault_remains_held_after_fault_disappears`.
4. Reserved reconciliation calls `validate_running` before publish and drains a failed readiness check. Regression: `test_reconciliation_revalidates_pins_and_drains_failed_readiness`.
5. **Fixed in this worktree.** `disable --stop-gateway` used to disable, then `WindowsAdapter.stop_selected` stopped only `active.json`. `Backend._launch` keeps the reservation when `publish` raises. `Backend.drain_owned` now stops the owned selected identity and the reserved launched replacement. The regression is `test_failed_publication_disable_drains_the_reserved_replacement` in `tests/test_recovery_cli.py`. Reused, unknown, and uncertain drains stay held.

## Shutdown contract

Under the management lock, after durable disable:

- Stop the selected identity only when the adapter reports it owned and it is the reserved expected identity, or there is no reservation.
- Stop the reserved launched identity when `owned_alive` confirms it.
- Do not signal a reused PID, an unknown identity, or a selected identity that matches neither the reservation nor the launched replacement.
- A reservation with `launched: null` is `launch-uncertain`.
- A stop that raises, or a process that stays alive, is `cleanup-uncertain`.
- Uncertainty stays in the journal as `held` and keeps the reservation. A confirmed drain clears the reservation and does not relaunch.

## Non-goals

No production observation, arming, scheduled task, fault injection, deployment,
commit, or push. No general station startup, automatic rollback, or model,
broker, or voice restart. No five-second latency change. No live answer
benchmark. No owner-data backup until destination, key custody, and RPO/RTO
are chosen. Drills and synthetic restore stay after this shutdown fix is
revalidated. Independent review remains an open gate.

## Results of this pass

The unpublished-replacement test failed on the old `stop_selected` path
(`stopped == []`). After `Backend.drain_owned`, these commands passed:

```text
python scripts/complexity.py check
python -m unittest tests.test_recovery_cli tests.test_recovery_backend tests.test_recovery_policy tests.test_recovery_state
```

Complexity reported 870 functions and 110 modules, with no allowance change.
The four recovery modules reported 41 tests, exit 0. Gateway pid 27572 was
still present afterward.

`disable --stop-gateway` now disables under the management lock first, then
stops the owned selected identity and a reserved launched identity. A reused,
unknown, or still-living process stays `held` with `reused`, `unknown`, or
`cleanup-uncertain`, and the reservation is kept. A confirmed drain of a
`launch-uncertain` hold clears that reservation and records `disabled`.

The disposable gateway drill now stores the journal state/reason pairs it
actually reads. `generation_count` is null because model generations are not
instrumented. A focused rerun of `tests.test_recovery_drills` plus the three
disable regressions reported 7 tests and 1 failure. The real disposable
gateway drill and the shutdown regressions passed. `truncated-stream` failed
before any drill claim: `tests.test_streaming.StreamingTests.test_ndjson_transport_requires_done_and_caps_frames`
raises `FileNotFoundError` for `/run/larpus-broker/inference.sock` on this
Windows host, while the test expects `ValueError`. That failure is retained.
The other four drill rows remain injected unit contracts. Five-repeat receipts
were not produced. Cancellation is still not tied to a supervisor launch
counter. BM25 is still not asserted through a complete approved-evidence request.

## Open items addressed after the shutdown fix

Missing broker socket now raises `ValueError('Invalid private inference socket')`
instead of `FileNotFoundError`, and it still does not open TCP. The NDJSON
framing test sets `LARPUS_ISOLATION=host` so it checks frames rather than the
absent socket.

`cancellation_drill` runs one supervisor cycle against a faulted broker and
records `generation_count` from the adapter launch counter. It was 0.
`evidence_drill` calls `knowledge.retrieve` on a two-row approved SQLite
fixture with the CPU engine disabled and records the returned source ids
`game-a`, `game-b`. A healthy observation in the same drill also launched 0
times. Five repetitions of all six harness rows passed and were written to
`data/recovery-drills/2026-10-20-five.json`. Gateway recovery seconds for the
five real disposable processes: count 5, median 41.5, nearest-rank p95 42.343,
max 42.343. With five samples the nearest-rank p95 is the maximum. Truncated
stream, disk-full, and failed-candidate rows are still injected contracts, not
full-station faults. `generation_count` on the gateway drill stays null.

`scripts/synthetic_backup.py` exports committed SQLite rows with the backup API,
an HMAC manifest, and restore to a different file. Tests cover an uncommitted
insert left out, a truncated payload, a bad manifest, and `ENOSPC` during
manifest publication. The source bytes stay unchanged. This is not encrypted
owner-data custody. Destination, key custody, RPO, and RTO are still owner
decisions. No owner database was read or written.

`python scripts/broker-prompts.py --check` passed. All 11 UI suites in
`scripts/ui_checks.py` passed. `git diff --check` reported no whitespace
errors. The serving gateway was not stopped.

## Isolated suite

The first `python scripts/test-local.py` in this worktree reported 525 tests,
4 skipped, and 1 error. The error was
`test_isolated_client_never_uses_tcp_when_socket_missing`, which still expected
`FileNotFoundError` after the missing private socket became
`ValueError('Invalid private inference socket')`. `HTTP.open` was still not
called. The assertion was updated to `ValueError`.

The second `python scripts/test-local.py` then reported:

```text
Ran 525 tests in 344.854s
OK (skipped=4)
```

Exit code 0. Complexity inside that run was 881 functions and 111 modules,
status PASS, with no allowance increase. Gateway pid 27572 was still listening
on port 8080 afterward. The suite copies the worktree and does not activate a
release.

## Review collection

An earlier `collect_local_diff.py` run used the main checkout as its working
directory. It died on `larpus-sensors.csv`: `git diff --no-index` emitted byte
`0xb0` at offset 4099, the UTF-8 reader returned no stdout, and joining chunks
raised `TypeError` on sequence item 6. That file is preserved main-checkout
data, about 146 MB, and is not part of this recovery diff. No reviewer was
spawned, and that attempt is not a verdict. The recovery worktree's tracked
diff and 17 untracked text files do not contain byte `0xb0`.

## Independent review 729460c6

A reviewer who did not write the diff reviewed the recovery worktree local
changes. Subagent `01a15b14-e815-7183-a98f-e1ce88e3effd`. Notes:
`C:\Users\PS5KIL~1\AppData\Local\Temp\grok-PS5Killer\grok-review-729460c6.md`.
Summary:
`C:\Users\PS5KIL~1\AppData\Local\Temp\grok-PS5Killer\grok-review-summary-729460c6.md`.
Verdict on that diff: 2 bugs, 2 suggestions, 0 nits. That verdict does not
cover the fixes below.

The bugs were real. `drain_owned` treated every `owned_alive() == False` as a
confirmed stop, including a reused or unreadable replacement PID, and could
clear a `launch-uncertain` reservation. `releases.launch` could leave a live
child when `process()` failed after `Popen`, with `launched` staying null.
Regressions: `test_reused_or_unreadable_replacement_is_not_a_confirmed_drain`
and `test_unrecorded_child_is_closed_on_its_process_handle`. Both failed before
the change. After it, a reused replacement keeps the reservation with reason
`reused`, and an unreadable one keeps it with reason `unknown`. The launch
failure path calls `terminate` on the process handle. If that handle cannot be
closed, the error is `Unrecorded gateway still running`; there is still no
creation date or command hash to store, so `launched` stays null in that
residual case.

The two suggestions are also changed. Reconciliation holds `broker-fault`
before the generic dependency reason. Podman inspect names drop one leading
slash before the inventory comparison. The four recovery modules then reported
45 tests, exit 0. Complexity reported 884 functions and 111 modules, PASS, with
no allowance increase.

`python scripts/test-local.py` after those drain and launch fixes reported 529 tests, 4 skipped, exit 0, in 352.987s. `git diff --check` reported no whitespace errors. That suite does not include the observe-only fix below.

## Independent review 8b4ca37c

A second reviewer who did not write the diff checked the drain and launch fixes.
Subagent `01a15b2e-8e9a-7ae2-8ba5-11b7c3cf30a1`. Notes:
`C:\Users\PS5KIL~1\AppData\Local\Temp\grok-PS5Killer\grok-review-8b4ca37c.md`.
Verdict: 1 bug, 0 suggestions, 0 nits. The earlier drain and launch holes were
accepted as closed, including the residual where an unrecorded child cannot be
closed and `launched` stays null.

The remaining bug was real. `watch --observe-only` rewrote a would-be `recover`
to action `none` and stored `dead_count`, so three dead observation cycles could
make the next armed cycle launch. Observe-only now prints `action=recover` on
that third simulated death and leaves the journal `dead_count` unchanged.
Regression: `test_observe_only_does_not_prime_an_armed_launch`. The four
recovery modules then reported 46 tests, exit 0. Complexity reported 885
functions and 111 modules, PASS. This observe-only edit is not covered by
review 8b4ca37c.

Review `f380a116` then found that pinning `dead_count` also dropped a reset.
A healthy gateway or a new process identity during observe-only kept the old
streak, so the next armed death could launch before three deaths of the current
generation. Observe-only still ignores a simulated increase. It now stores a
lower policy count, and it stores 0 when the identity changes.
Regression: `test_observe_only_drops_a_stale_streak_for_health_or_a_new_process`.
The four recovery modules then reported 47 tests, exit 0. Complexity reported
886 functions and 111 modules, PASS. Review f380a116 does not cover this reset.

Review `b5e77427` accepted the drain, launch, and same-identity observe-only
behavior. It rejected storing 0 for a new dead pid. `decide` restarts that
streak at 1. `_stored_deaths` now keeps a lower policy count and does not treat
an identity change as a special zero. A stored streak of 2 becomes 1 for the
new pid; two later armed deaths of that pid are what reach `recover`. The
regression asserts that count. Review b5e77427 does not cover this alignment.
Subagent `01a15b5a-345e-78e2-97c6-8e06d3196bd3`. Notes:
`C:\Users\PS5KIL~1\AppData\Local\Temp\grok-PS5Killer\grok-review-b5e77427.md`.

`python scripts/test-local.py` after that alignment reported 531 tests, 4 skipped,
exit 0, in 361.201s. Complexity inside that run was 886 functions and 111
modules, PASS. Gateway pid 27572 was still listening on port 8080.

The hash-bound 30-minute observation proposal and the separate arming proposal
are written in `docs/RECOVERY_SUPERVISOR.md`. Neither has been started.

## Still open

- Final `_stored_deaths` alignment review completed; see the scoped verdict below. Production rollout and other feature gates remain separate.
- Live latency and answer-quality benchmarking: not started. No measurement window was approved.
- Owner backup destination, key custody, RPO, and RTO. No owner database was read.
- Production supervisor: not installed, not armed, not observing. The observation window has not been approved to start.
- Frozen scan receipts were not edited and were not regenerated. No release was staged.

## Final death-count review — accepted, 2026-10-20

Fresh independent reviewer `/root/death_count_review` accepted the final
observe-only death-count alignment with no concrete defect found. It ran 19
CLI/policy tests and an additional 864 disposable three-observation sequences,
each followed by simulated watch restart, covering same/new process identity,
healthy, busy, broker-held and reused-process observations. No launches occurred.
The reviewer confirmed stored count is min(policy count, previous count), holds
remain held and simulated counts cannot authorize recovery. Existing real
stored count 2 remains eligible on the next armed confirmed death.

This closes independent review of this final alignment only. It is not proof of
production operation, broad security/durability, observation overhead or rollout
acceptance. No production observation, installation, arming or deployment ran.
