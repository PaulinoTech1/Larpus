# Larpus decision record

Updated 2026-10-08. Accepted choices, their consequences and current evidence
are recorded here. Historical scan receipts keep their original fingerprints;
they are not verification of later changes.

| Decision | Rationale and consequence |
|---|---|
| Single-owner, local-only station | No cloud inference, accounts or external runtime services. Public downloads occur only during explicit artifact preparation. |
| Windows 11 Home: dedicated Larpus WSL2 and rootless Podman | Works with the installed OS; OpenShell remains a future layer. Docker Desktop's separate distro is left alone. |
| Default executor is wsl-podman | Fixed stdio MCP and sealed source/image checks fail closed. Unsandboxed host mode requires explicit LARPUS_ISOLATION=host. |
| Production pod uses network=none | Only shared pod loopback connects MCP to Ollama. No published inference port, external/LAN connections or DNS transport. PID/IPC/filesystems remain separate. |
| Read-only code, models and narrow GPU mounts | Agent has no Windows drives, home, credentials, sockets or GPU. Only the model receives /dev/dxg, WSL libraries and one read-only NVIDIA package. |
| DLP owns private output quarantine | Every generated reply is checked before release. Flagged output is held for owner CLI investigation; the model cannot mount evidence. Detection has encoding/semantic limits. |
| Local filters and three fixed MCP tools | Input is checked before inference. Only list_personas, local_status and chat_local are exposed; no model-callable shell, file or internet tools. Filters supplement OS isolation. |
| Locally authored skills only | Four prompt-only skills have registry hashes and persona allowlists. No imported/executable skills. SkillSpector runs static/no-LLM through an offline wrapper; findings remain visible. |
| Keep qwen2.5:14b baseline | Installed and functionally tested on the RTX 3090 Ti, with Ollama reporting 100% GPU. Qwen3 14B awaits local evaluation; no quality/speed benchmark claim. |
| Personas are configurations | Twelve selectable roles share the installed model and approved skills. Distinct educational prompts support roleplay, not fabricated qualifications. Psychology is educational, not clinical care. |
| Torus and integral remain the visual identity | Repeating formation sweep, equation and larger torus-set definition retain the HUD. Percentage is decorative, not inference progress; reduced motion is static. |
| Local HTTP has no password | http://127.0.0.1:8080 bypasses authentication only when listener and peer are loopback. Local processes can use this access. /login redirects existing access to the HUD. |
| LAN uses password-protected HTTPS | https://192.168.1.2:8080 uses a local CA, TLS 1.2 minimum, Secure/HttpOnly/SameSite cookies, scheme-aware origins and home-subnet checks. Plaintext LAN HTTP is rejected. |
| Hidden local password setup | Salted scrypt hash stays in ignored data/password.json. Failed logins say "You're Larping already". Both listeners share one gateway's authentication and rate limits. |
| Private artifacts stay outside Git | Password hashes, TLS keys, deployment pins, health data and archives stay under ignored data/. Quarantined replies stay in the Linux volume. Share only ca.crt for client trust. |
| Restart is manual | Start the dedicated pod, verify isolation, then launch the gateway. No autostart task is installed. Password, certificates and quarantine persist. |

## Evidence and pending work

45 tests passed after TLS/local-auth updates. Live probes verified local API
access without authentication, LAN HTTPS rejection without a session, certificate
validation, plaintext LAN rejection and network-denial boundaries. Twelve personas
were listed by isolated MCP. A synthetic credential reply was held in quarantine,
and its evidence survived redeployment/restart.

The backend restarted after owner-reported Windows shutdown/reboot. A physically
network-disconnected reboot, another device's CA trust and authenticated chat,
browser visual acceptance, voice and OpenShell remain unverified or unimplemented.
Voice is a stub. Scanner findings remain warnings; compare receipt fingerprints
with current source. Host administrators, kernel/driver compromise and trusted
guard exploits are outside the claimed boundary.

See [isolation](WINDOWS-HOME-ISOLATION.md), [HTTPS](HTTPS.md),
[personas](PERSONAS.md), [DLP](OUTPUT-DLP.md) and [verification](VERIFICATION.md).
