# WSL access from the Codex sandbox

Status: diagnosed on 2026-10-27. No ACL was changed and `WslService` was not
restarted. The Horizon classifier was not launched during this check.

## Result

`WslService` denies the Codex command token before a Larpus process exists.
The same `wsl.exe` calls succeed from an ordinary owner PowerShell. This is
not an eight-thread shortage, a stopped VM, or a missing distribution.

The denial also explains the failed write to
`data/releases/manage.lock`. Authenticated Users already has inherited
Modify. A restricted token must pass a second access check, and the LARPUS
tree has no Codex capability SID, so that Modify entry does not count.

## Evidence

The failing Codex session used `C:\Users\PS5Killer\.codex\config.toml`:

```toml
[windows]
sandbox = "unelevated"
```

Its shell command was `WindowsPowerShell\v1.0\powershell.exe -Command ...`.
`IsTokenRestricted` was true for that command process. Windows build
`26200.9711` reports ProductName `Windows 10 Home` and DisplayVersion `25H2`.

| Caller | Token | `wsl --list --quiet` | `wsl.exe --distribution Larpus --user larpus --exec /bin/true` |
| --- | --- | --- | --- |
| Codex unelevated session, 2026-10-26 | Restricted | `Wsl/EnumerateDistros/Service/E_ACCESSDENIED` | `Wsl/Service/E_ACCESSDENIED` before Python |
| Owner PowerShell, 2026-10-27 | Not restricted, Medium, UAC-filtered admin | Exit 0: `docker-desktop`, `Larpus` | Exit 0 in 1118 ms, empty output |
| MXC probe, 2026-10-27 | MXC workspace profile | `Wsl/E_ACCESSDENIED`, exit -1 | Not run after enumeration failed |

The owner PowerShell was `PS5KILLER\PS5Killer`, parented by `grok.exe` and
then `explorer.exe`. Integrity was Medium (`S-1-16-8192`).
`TokenElevationType` was Limited. `IsTokenRestricted` was false.
`WslService`, `vmcompute`, and `hns` were already running, as were
`wslservice` pid 6764 and `vmmemWSL` pid 11408.

MXC itself starts on this PC. This probe printed `MXC_OK` and exited 0:

```powershell
codex -c windows.sandbox=mxc -C E:\speedzone_MS\LARPUS sandbox --include-managed-config --permission-profile :workspace -- cmd.exe /d /c echo MXC_OK
```

The same MXC profile cannot enumerate distributions. Switching
`features.prefer_mxc` therefore does not make the Horizon launch work.
The legacy elevated sandbox was not tested: it runs as a separate
low-privilege account, needs administrator setup, and is not the token that
succeeded.

`manage.lock` is owned by `PS5KILLER\PS5Killer`. Inherited entries are
Administrators FullControl, SYSTEM FullControl, Authenticated Users Modify,
and Users ReadAndExecute. Codex's capability-SID map has no writable root
for `E:\speedzone_MS\LARPUS`.

## Solution

Run Larpus commands from a process whose token is not restricted. Use the
project wrapper so a sandboxed agent stops with an explicit reason instead
of starting Python:

```powershell
powershell -NoProfile -File E:\speedzone_MS\LARPUS\scripts\invoke-larpus.ps1 /bin/true
```

Arguments after the script are the Linux command. Larpus has automount
and interop disabled, so `/mnt/c` does not exist. The sweep script is
`/home/larpus/horizon_cpu_sweep.py`. The prepared Horizon sweep, still
not executed, is:

```powershell
& 'E:\speedzone_MS\LARPUS\scripts\invoke-larpus.ps1' /home/larpus/train-venv/bin/python /home/larpus/horizon_cpu_sweep.py --source /home/larpus/train-models/prompt-guard-eval/horizon-small-0e377453 --out /home/larpus/horizon-cpu-sweep.json --threads 1 2 --windows 1024 4096 --repeats 5 --budget-seconds 240
```

Start that PowerShell from Explorer or Windows Terminal, not from a Codex
tool call. The wrapper exits 2 when `IsTokenRestricted` is true and does
not call `wsl.exe`.

Verified on 2026-10-27: the wrapper's `/bin/true` launch exited 0 from owner
PowerShell. The same file launched through `codex sandbox` never reached
the token check. Sandbox PowerShell rejected it with
`DotSourceNotSupported` because the script was defined in a different
language mode. That probe's `codex.exe` process still exited 0, so a Codex
exit code alone does not prove the Linux command ran.

A Codex chat can reach the same token only by running the command outside
the Windows sandbox: approve that one command unsandboxed, or set that
chat to full access. Leave the global `[windows] sandbox = "unelevated"`
setting in place. `danger-full-access` as the default would remove the
filesystem and network boundary for every command.

Do not grant WSL by editing the `manage.lock` ACL, adding a writable root,
or restarting `WslService`. Those actions do not change the restricted
token that `WslService` rejects. A writable root can only repair the
separate lock-file write.
