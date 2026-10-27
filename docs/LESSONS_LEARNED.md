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

## Horizon quarantined the cyber-pentest case

Horizon was added after the existing allow checks, for chat messages only.
Evidence, skills, and voice stay on the earlier gate. A Horizon injection
label quarantines that message and the gateway keeps serving. The first live
cutover was release `4388d01cef2f46d89d80749045ed3cd7`.

The verified performance suite `8b0ab6414c6e49aea7d4dac81a0401ab` then failed
`cyber-pentest` on every warmup and measured attempt. The gateway returned
HTTP 200 in about 1.0–1.1 seconds with no text. The suite stored
`invalid_protocol`. A replay showed the stream was a quarantine event and
then `done` with `local: true`. The lexical filter had allowed the sentence.
Horizon's own label was `INJECTION` at probability 0.5336, so the message
was removed before the model. The suite did not understand the quarantine
event and called the parse a protocol error.

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
