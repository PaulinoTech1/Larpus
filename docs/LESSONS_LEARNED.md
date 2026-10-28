# Lessons learned

Station notes from problems that looked like capacity or protocol failures and
were not. Dates are 2026-10-27 unless another date is named.

## WSL denied the Horizon benchmark before Python started

Codex on this PC was set to `[windows] sandbox = "unelevated"`. That mode runs
each shell as `powershell.exe -Command` with a restricted token.
`IsTokenRestricted` was true. `wsl --list --quiet` failed with
`Wsl/EnumerateDistros/Service/E_ACCESSDENIED`, and
`wsl.exe --distribution Larpus --user larpus --exec /bin/true` failed with
`Wsl/Service/E_ACCESSDENIED`. The failure was before Python, thread setup, or
the Horizon weights. `WslService` was already running, with `vmmemWSL` and
`wslservice` present. It was not an eight-thread shortage.

The same two commands were then run from an owner PowerShell whose parent
chain reached `explorer.exe`. That token was Medium integrity and not
restricted. `IsTokenRestricted` was false. Listing distros exited 0
(`docker-desktop`, `Larpus`). `/bin/true` in Larpus as `larpus` exited 0 in
1118 ms. Medium integrity was not the blocker. This successful shell was
unelevated too. The split was the restricted token.

MXC was checked once because it is the preferred Windows sandbox. `cmd.exe`
printed `MXC_OK`. The same MXC profile returned `Wsl/E_ACCESSDENIED` for
`wsl.exe --list --quiet`. Switching to MXC does not make WSL calls work.
The legacy elevated sandbox was not used. It runs as a different low-privilege
account and needs administrator setup.

The same restricted token also could not write
`data/releases/manage.lock`. Authenticated Users already had inherited Modify.
Codex's capability-SID map had no writable root for `E:\speedzone_MS\LARPUS`.
Changing that ACL or restarting `WslService` does not fix the WSL denial.

Larpus has automount and interop disabled. `/mnt/c` does not exist. A sweep
script placed under the Windows temp directory cannot be opened as
`/mnt/c/Users/...`. The script had to be copied into the distro, at
`/home/larpus/horizon_cpu_sweep.py`, and the receipt written to a Linux path.

Manual fix, from an owner PowerShell started by Explorer or Windows Terminal,
not from a Codex tool call:

```powershell
& 'E:\speedzone_MS\LARPUS\scripts\invoke-larpus.ps1' /bin/true
```

Arguments after the script are the Linux command. Exit 0 means the token can
enter Larpus. Exit 2 means the token is still restricted. Do not paste a
leading `powershell -NoProfile` into a window that is already PowerShell.
That makes `-NoProfile` the command.

`invoke-larpus.ps1` originally stopped the sweep when `wsl.exe` wrote its
progress bar to standard error, because Windows PowerShell treats native
stderr as a terminating error under `ErrorActionPreference = Stop`. The
launcher now lets that stream continue and returns the Linux exit code. The
first sweep had written only an initializing receipt before that abort.

## Horizon blocked the cyber-pentest prompt and that turn froze

Horizon was added after the existing allow checks, for chat messages only.
Evidence, skills, and voice stay on the earlier gate. A Horizon injection
label quarantines that message and the gateway process keeps serving. The
first live cutover was release `4388d01cef2f46d89d80749045ed3cd7`.

The incident was the verified `cyber-pentest` case. The lexical filter
allowed the sentence. Horizon labeled it `INJECTION` at probability 0.5336
and blocked it before the model. The gateway answered HTTP 200 in about
1.0–1.1 seconds with a quarantine event, then `done` and `local: true`, and
no text. The performance runner did not recognize that event, so the turn
never completed. The suite stored `invalid_protocol` and the case looked
frozen: no first text and no finished reply. This happened on every warmup
and every measured attempt in run `8b0ab6414c6e49aea7d4dac81a0401ab`. The
other eight cases in that same run still completed, so the gateway process
itself did not stop. The frozen part was the blocked cyber-pentest turn.

Scores on the same snapshot, one segment, six threads:

| Text | Injection probability | Label at 0.5 |
| --- | ---: | --- |
| Original cyber-pentest sentence | 0.5336 | INJECTION |
| Same sentence without "without trusting its first answer" | 0.1529 | SAFE |
| Same request, but "reproduce the finding before accepting it" | 0.7053 | INJECTION |
| Suite case now: "The lab must confirm the finding itself" | 0.3567 | SAFE |
| Other eight suite cases | 0.3433 or below | SAFE |
| Direct instruction override | 0.9997 | INJECTION |
| Paraphrase that the lexical rules do not catch | 0.9958 | INJECTION |

A cutoff of 0.9 would have let the original sentence through, and it would
also have let the 0.7053 wording through. That is a weaker gate, not a fix.
A server-owned "fictional lab-coach question" prefix dropped the original
sentence under 0.5, but it also dropped the paraphrase from 0.9958 to
0.9661, so the prefix was not adopted.

The adopted change keeps the 0.5 label boundary. The suite sentence no longer
uses the clause that scored 0.5336. It tells the lab to confirm the finding
itself, which scored 0.3567. The review points are unchanged. The same
wording is in `evals/performance.json` and `evals/execution-profiles.json`.
The performance runner now records a real quarantine as `quarantined`.

Release `882c959c3d4540a5ba4b4b89f1596b17` carries that boundary. One replay
of the reworded pentest case produced text only: first text 14.330 seconds,
completion 18.676 seconds. The paraphrase was quarantined in 1.165 seconds
and produced no text.

Checkout edits do not affect the running gateway. Production serves the
frozen release named in `data/releases/active.json`. A launcher started
inside an agent job can exit when that job ends, which looks like the new
gateway failed readiness even after `activate` reported success. Start it
from an owner PowerShell with `python scripts/releases.py start` if status
reports the selected release and `"running": false`.

Details: [WSL sandbox access](WSL_SANDBOX_ACCESS.md) and
[local input filtering](TEXT_FILTER.md).

## Broker refusal hid the actionable cause - 2026-10-28

The owner saw "Local inference is busy or held by the broker. Retry
shortly; no direct fallback is used." The same display text covered queue
contention, rolling request/token limits, admission timeout, model
switching, failed readiness/cancellation confirmation and other broker
refusals. The gateway already preserved a structured refusal code, but the
HUD ignored it. A generic retry instruction did not distinguish a temporary
wait from a fault that needs owner investigation.

The original refusal code and contemporaneous broker state were not
captured. Its root cause remains unknown. A later streamed localhost
greeting released text and completed in 12.0 seconds on active release
`1022de11b0df4ce6be2915f49f1286ba`. That proves one later request worked,
not that the earlier refusal was harmless or that availability is sustained.
Do not diagnose an MCP skill failure or restart the model from this message
alone.

The repository correction displays allowlisted broker codes with distinct
guidance and adds `python scripts/broker-status.py`, an owner-only read-only
admission-status command. Capture the code, request time and selected
release's `active`, `waiting_chat` and `faulted` state before retrying.
A failed cancellation fence must remain closed; do not clear it or add a
direct inference fallback just to restore a reply. Investigate active work,
model readiness and selected container identities before any scoped recovery.
The diagnostic changes are committed but were not activated during this
investigation.

The preceding speech error was a separate browser defect:
HTMLCollection has no `.at()`. Its `lastElementChild` fix is verified in
the served JavaScript. The repair initially failed staging because its
copied source lacked `research/catalog.json`, a provenance build input.
Supplying the matching reviewed catalog restored exact equality with all
421 provenance entries unchanged; the check was kept intact. This is a
lesson to preserve build inputs when assembling an isolated release source,
not a reason to blindly rebuild provenance or bypass validation.

Verification: all 11 configured Node UI suites, four owner-status tests and
seven existing broker tests passed; one Unix-only integration test was
skipped on Windows. A coded refusal after partial text is covered: speech
stops, incomplete output stays out of history, and no automatic generation
retry occurs. Physical audio playback and reproduction of the original
broker refusal remain unverified.

Details: [broker follow-up](BROKER_FAILURE_FOLLOWUP_2026-10-28.md) and
[speech repair/provenance report](SPEECH_CUTOFF_REPAIR_BLOCKER_2026-10-28.md).
