# Prompt for the next LARPUS agent

Copy the following into the next agent session. It records completed recovery
work. It does not authorize production operation, arming, commit, or push.

---

You are the engineer continuing LARPUS. The active editing checkout for this
handoff is the recovery worktree, not the main checkout.

```text
Worktree: E:\speedzone_MS\LARPUS-worktrees\recovery-supervisor
Branch:   feat/recovery-supervisor
Commit:   a2f12c0 (uncommitted recovery work on top)
Ledger:   docs/RECOVERY_EXECUTION_LEDGER_2026_10_20.md
Contract: docs/RECOVERY_SUPERVISOR.md
```

The main checkout is `E:\speedzone_MS\LARPUS`, branch
`feat/secure-execution-profiles`, same commit `a2f12c0`. Leave it alone.
Preserve its dirty and untracked files, including
`docs/architecture/failure-isolation-outline.md`, `New Text Document.txt`,
`larpus-sensors.csv`, `docs/PROJECT_IMPROVEMENT_PLAN_2026_10_20.md`,
`docs/NEXT_AGENT_EXECUTION_PROMPT_2026_10_20.md`, and the untracked recovery
spec/plan copies there. `larpus-sensors.csv` is about 146 MB and contains a
non-UTF-8 byte `0xb0`. A local-diff collector run from the main checkout dies
on that file. Collect review diffs with the working directory set to the
recovery worktree.

Production runs the frozen release selected by `data/releases/active.json`.
Last confirmed selection was `042f91c0a1454887a694c945f49237ad`, previous
`7df2e957751642d6ace4630fa047fe94`. Last confirmed listener was python pid
27572 on port 8080, started 2026-10-20 10:39. Recheck that read-only before
any claim. Keep that gateway, the model, and CPU voice running. Do not stop
pid 27572. Do not edit active payloads, deployment pins, or frozen scan
receipts. Do not stage, prepare, or activate a release. Do not commit or push.
Do not arm, install, schedule, or observe the supervisor in production. Do not
inject faults into the serving station. Do not read or write an owner database.
`data/github` is untrusted reference data.

Read `Agents.md`, `docs/UPDATES.md`, the ledger, and
`docs/RECOVERY_SUPERVISOR.md` before changing code. The ledger's early section
still says five-repeat receipts were not produced and that cancellation is not
tied to a launch counter. Later sections correct that. One intermediate
paragraph also says a new identity stores `dead_count` 0. The final code does
not. Trust the source and the latest ledger paragraphs over earlier ones.
`docs/STATUS.md` is the stale 2026-10-11 snapshot.

## What is already done

Failure isolation and catalog scoping were activated earlier as release
`042f91c0`. Execution profiles and MCP Skills were prepared and not promoted.
Assembly-optimized scoring exists in the working tree. Historical latency
candidates `dc74ddc8315d4fdaa6349c72fc40bc46` and
`306986ac3d954e7791b2b7a3028838e2` were not promoted. Failed stage
`90ab2aa349b74747930d591f9521ab5e` must not be edited. Do not redo those.

The recovery supervisor is implemented only in the recovery worktree and is
disabled by default. `disable --stop-gateway` disables under the management
lock, then `Backend.drain_owned` stops exact owned identities.

Current drain and launch behavior:

- `presence` distinguishes `alive`, `absent`, `reused`, and `unknown`.
- A reused replacement keeps the reservation with reason `reused`.
- An unreadable replacement keeps the reservation with reason `unknown`.
- A confirmed drain of a `launch-uncertain` hold clears the reservation and
  records `disabled`. Other held reasons stay held.
- `releases.launch` closes the `Popen` handle when `process()` fails or returns
  empty after the child is created. If that handle cannot be closed, the error
  is `Unrecorded gateway still running` and `launched` stays null, because no
  creation date or command hash exists to store.
- Reconciliation holds `broker-fault` before the generic dependency reason.
- Podman inspect names drop one leading slash before the inventory comparison.
- A missing private inference socket raises
  `ValueError('Invalid private inference socket')` and does not open TCP.
  `LARPUS_ISOLATION=host` is the path that uses `HTTP.open`.
- `scripts/synthetic_backup.py` is an HMAC-SHA256 manifest over a SQLite backup
  of committed rows. It is not encryption and not owner-key custody.

Observe-only behavior in `scripts/supervise.py`:

- `watch --observe-only` never calls `launch`.
- One watch call keeps an in-memory death counter. The third simulated death of
  the same identity prints `action=recover`.
- `_stored_deaths` stores `decision.dead_count` when it is lower than the
  journal count. A simulated increase is not stored.
- A healthy gateway stores 0. A new dead pid stores the policy restart of 1
  when that is lower than the old streak. Two later armed deaths of that same
  pid are what reach `recover`.
- `cycle()` without the watch counter does not store a simulated increase.

Drills, from `data/recovery-drills/2026-10-20-five.json`:

- Six scenarios, five repeats, 30 passing rows.
- Gateway exit uses disposable Python processes. Five recovery samples: median
  41.5 s, nearest-rank p95 42.343 s. With five samples that p95 is the maximum.
- Cancellation measured one supervisor cycle against a faulted broker.
  `generation_count` was 0.
- Retrieval measured `knowledge.retrieve` on a two-row fixture with the CPU
  engine off. Source ids were `game-a`, then `game-b`. A healthy observation
  launched 0 times. `committed_before` and `committed_after` are the constant 2.
- Truncated stream, disk-full, and failed-candidate rows are injected unit
  contracts. `generation_count` on the real gateway drill is null because model
  generations are not instrumented.

Validation already recorded:

- Four recovery modules, 47 tests, exit 0, after the final stored-count change.
- `python scripts/test-local.py`: 531 tests, 4 skipped, exit 0, 361.201 s.
  Complexity in that run: 886 functions, 111 modules, PASS. No allowance was
  raised.
- `python scripts/broker-prompts.py --check` passed earlier. All 11 UI suites
  in `scripts/ui_checks.py` passed earlier. `git diff --check` reported no
  whitespace errors before the last edits.
- The suite copies the worktree and prints lines such as "Started active
  release aaaa…". Those lines come from patched tests. They are not a cutover.

## Reviews

Independent reviewers who did not write the diff reviewed earlier snapshots.
Their notes are under `C:\Users\PS5KIL~1\AppData\Local\Temp\grok-PS5Killer\`.
Those temp files may disappear. The ledger quotes the verdicts.

| Review | Result |
| --- | --- |
| `729460c6` | 2 bugs, 2 suggestions. Drain confirmation and unrecorded launch. Both were fixed, along with the broker-fault reason and the leading-slash inventory check. |
| `8b4ca37c` | 1 bug. Observe-only hid `recover` and stored `dead_count`. The watch counter and printed `action=recover` address that snapshot. |
| `f380a116` | 1 bug. Pinning `dead_count` dropped a healthy reset and kept a stale streak on a new pid. |
| `b5e77427` | 1 bug. Forcing 0 on every identity change disagreed with `decide`, which restarts a new dead pid at 1. |

`_stored_deaths` was then changed to keep a lower policy count, including 1 for
a new dead pid. Review `b5e77427` does not cover that alignment. The recovery
work is not accepted. Do not self-approve. If you review, review only as a
reviewer who did not write the diff, from the recovery worktree, and leave a
verdict. If you are the agent who would be reviewing your own edit, leave the
gate open.

Tracked files already dirty in the worktree, and not to be reverted blindly:
`docs/UPDATES.md`, `runtime/gateway.py`, `runtime/health.py`,
`runtime/local_ollama.py`, `scripts/releases.py`, `tests/chat-stream-ui.cjs`,
`tests/test_inference_broker.py`, `tests/test_skills_health.py`,
`tests/test_streaming.py`.

## Your task

1. Recheck the live gateway, `data/releases/active.json`, and `git status` in
   the recovery worktree. Record what you actually see.
2. Read `scripts/supervise.py` `_stored_deaths`, `_shown`, `_observe_locked`,
   and `scripts/recovery_policy.py` `decide`. Confirm the new-pid count is 1
   and that a simulated increase is not stored.
3. Obtain an independent review of that final alignment. If you wrote it, you
   cannot be the reviewer. A failed diff collector is an open gate, not a pass.
4. Leave production untouched. The hash-bound 30-minute observation proposal
   in `docs/RECOVERY_SUPERVISOR.md` is written and not started. Recompute the
   SHA256 inventory before any future window. `scripts/supervise.py` must still
   hash to `37ab3a1b6d1bb90f904665d057040cb699dc2553217d973c03477101ac1da5f4`
   unless you change it and update the inventory in the same change.

Ask the owner before any of these:

- Starting `python scripts/supervise.py watch --observe-only` against production.
- Arming, or `python scripts/supervise.py watch` without `--observe-only`.
- Choosing a backup destination, key custody, RPO, and RTO. Synthetic backup
  tests are not an owner restore.
- A live latency or answer-quality window.
- Regenerating scan receipts, staging a release, committing, or pushing.

Update the ledger with commands, counts, skips, and failures you actually run.
Keep null metrics null. A passing test is not answer correctness. A drill
receipt is not production resilience. A written proposal is not a completed
observation.
