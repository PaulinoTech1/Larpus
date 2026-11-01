# Independent recovery supervisor

Implementation candidate only. No production supervisor is installed, running or
armed by this change. Runtime health producer metadata requires a separately
staged and prepared release before automatic recovery can support that release.
Existing releases without the producer marker are explicitly unsupported.

The owner-side supervisor remains independent of the gateway. It observes every
five seconds without overlapping cycles. Three confirmed observations of the
same dead gateway can permit a gateway-only launch. A live but unhealthy gateway,
unknown identity, occupied port or unconfirmed cancellation holds instead.
Reviewed scanner warnings never request a restart.

Recovery uses the existing release management lock, rereads selection and safety
conditions, validates frozen pins and isolation, persists an attempt before
launching, then requires fresh health from that process. It never calls general
station startup, starts WSL, warms a model, resets the broker or restarts voice.
Busy dependencies wait without spending attempts. Deployment, drain and the
owner's `data/recovery/maintenance` marker suppress recovery.

At most two attempts are allowed within 600 seconds, with a persisted 60-second
cooldown plus 0–10 seconds of jitter. Clock reversal, reboot-like monotonic reset
or a wall/monotonic discrepancy over ten seconds holds. Durable reservations
survive supervisor restart. Publication uncertainty holds and retains evidence;
an exact recorded launch can be reconciled without issuing another launch.

Owner commands below are examples for a separately approved rollout, not steps
already executed in production. Run from the reviewed owner checkout:

```powershell
python scripts/supervise.py status
python scripts/supervise.py watch --observe-only
python scripts/supervise.py arm
python scripts/supervise.py watch
python scripts/supervise.py disable --stop-gateway
python scripts/supervise.py disable
python scripts/supervise.py acknowledge
```

`status` is read-only. A missing journal is disabled. Observation-only mode
records proposed decisions but cannot launch. Arming does not start a watch or
clear a hold. Acknowledgement clears only the supervisor hold and observation
count; it preserves attempts, reservations and broker fences. An unresolved
condition immediately holds again. Intentional shutdown must use the combined
disable/drain command so durable disable precedes drain under the management
lock. Directly stopping an armed gateway can otherwise look like a crash.

The owner/SYSTEM-only bounded journal lives at `data/recovery/state.json`.
Corruption, unsafe paths, ACL changes and failed persistence refuse recovery.
Replacement uses a same-directory temporary file, flush/fsync and atomic rename.
This is focused journal durability evidence, not a guarantee against arbitrary
filesystem, hardware or power-loss failures. Do not delete state to reset a
budget. Preserve it when removing or replacing the supervisor.

Fixed status reasons include `unknown`, `reused`, `broker-fault`, `dependency`,
`integrity`, `clock`, `budget`, `reservation`, `launch-uncertain`,
`readiness-failed` and `persist-failed`. Inspect the owner-side release state and
resolve the cause before acknowledgement. No HTTP control endpoint or scheduled
task is added. LAN sessions still require a fresh login after gateway replacement.

Disposable evidence is generated with:

```powershell
python scripts/recovery_drills.py --output data/recovery-drills/report.json
```

The harness accepts an output path, never a production PID, store, command or
container target. Gateway exit uses independently spawned Python fixture gateway
and supervisor processes on an ephemeral loopback port. The real recovery policy,
journal and backend orchestration run with simulated dependency/pin/health gates.
Other scenarios reuse injected regression contracts for BM25 fallback, broker
cancellation refusal, truncated-stream transport and HUD history, ENOSPC journal
replacement and updater rollback. Receipts label this distinction. Null metrics
are uninstrumented, not zero. No model generation, real disk exhaustion, shared
worker failure or production rollback is performed.

## Observation proposal, not started

This is a request for a later 30-minute window. It does not authorize starting
that window, arming, installation, a scheduled task, or a fault.

Before the window, recompute SHA256 of these files from the owner checkout and
refuse to start if any digest differs. The inventory is the candidate that
contains the post-review drain fixes. It is not a release pin.

| Path | SHA256 |
| --- | --- |
| `scripts/supervise.py` | `37ab3a1b6d1bb90f904665d057040cb699dc2553217d973c03477101ac1da5f4` |
| `scripts/recovery_backend.py` | `75b52a02fe69a00ed4343a870a213b24dd2d69ef945011eaa59ff7d4c7bd0fa9` |
| `scripts/recovery_policy.py` | `a82c1bc2923388ed0073709b753b9a2b77fa055ce4501b741b7d951f6b9c3617` |
| `scripts/recovery_state.py` | `4331ccf94a6a6c3ca1b406d5d35c267c12318ab3a813ae009274c1b8be9e3e1f` |
| `scripts/protect-recovery.ps1` | `4f84a8cac7b0503b0751fce6fd7691a7d92bf465b389671a79b9794f8732d6ec` |
| `scripts/releases.py` | `6d455670406b51b6fc3bb43dc6d62bc888b4c10e1176eb50f5f18a4f2c753646` |

Command, from that checkout, for at most 30 minutes:

```powershell
python scripts/supervise.py watch --observe-only
```

`watch --observe-only` simulates armed decisions and writes the owner journal at
`data/recovery/state.json`. It must not call `launch`. Record the supervisor
PID, each printed decision, cycle time, the gateway pid on port 8080, and
whether that pid changes. Stop with Ctrl+C if a decision says `recover`, if
the gateway pid changes, if a cycle exceeds the 5-second interval by more than
twice, or at 30 minutes. After exit, confirm that supervisor pid is gone and
keep the journal. Do not run `arm`, `disable --stop-gateway`, or the drill
harness against production during this window.

## Arming proposal, not authorized

Arming stays closed until an observation log from the inventory above shows no
`recover` action, no gateway pid change, and no unexplained `held` reason.
A later arming request would be `python scripts/supervise.py arm` followed by
`python scripts/supervise.py watch` without `--observe-only`, with the same
hash check and an owner present to run `disable --stop-gateway` if a launch
starts. That request is not made here. A runtime change still has to be staged,
prepared, and activated on its own; this supervisor does not deploy one.
