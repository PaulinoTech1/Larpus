# Larpus decision record

## Five specialist skills per role (2026-10-08)

Each of the twelve personas has five exclusive, locally authored specialist
skills (60 additions). The four existing shared skills and their allowlists remain
compatible. The HUD selects one skill per conversation; only that skill is
appended to the server-owned prompt, avoiding loading the entire catalog into
the 4096-token context. Changing selection clears history. See the
[role skill catalog](ROLE_SKILLS.md) for topics and exact prompts.

Skills teach subject-specific reasoning, evidence standards and terminology.
They confer no credentials, executable tools or archive access. Mathematics stays
continuous, system administration covers enterprise operations, cybersecurity
stays defensive/authorised, and psychology stays educational. Registry capacity
rises from 32 to 128 for 64 registered skills; file-size, hash, text-filter, origin,
folder and persona-selection checks remain. The sealed agent is rebuilt and its
source fingerprint repinned; the previous agent is retained stopped for rollback.

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
Opt-in CPU voice is now deployed with VoiceStudio ASR adapter and British Piper TTS;
wake-word, cloning and real microphone/speaker acceptance remain pending. Scanner findings remain warnings; compare receipt fingerprints
with current source. Host administrators, kernel/driver compromise and trusted
guard exploits are outside the claimed boundary.

See [isolation](WINDOWS-HOME-ISOLATION.md), [HTTPS](HTTPS.md),
[personas](PERSONAS.md), [DLP](OUTPUT-DLP.md) and [verification](VERIFICATION.md).

## Voice addition ? 2026-10-08

A separate network-disabled CPU worker leaves GPU capacity for Ollama. Listening
is opt-in, recordings are not retained, and generated speech follows output DLP.
Only exact station UI commands are enabled; OS actions remain outside this slice.
See [voice integration](VOICE_INTEGRATION.md) for pins, limits and rebuild steps.

## Research archive addition — 2026-10-08

Six persona catalogs each allocate 10 undergraduate student dissertations/capstone
reports, 8 master's theses and 7 doctoral theses. Journal/conference papers do
not substitute for undergraduate work. Explicit joint bachelor/master submissions
count once; conflicting university degree tags are checked against PDF title pages.
Mathematics remains continuous; systems-administration selections concern enterprise
storage, distributed services, capacity, virtualization and fault tolerance.

Cryptography has eight extra primary references outside the student quota, including
FIPS 197, SP 800-186, FIPS 203/204 and secure KEM/GCM implementation guidance.
Historical Kyber/Dilithium candidates remain distinct from standardized ML-KEM/ML-DSA.
Standards are pinned snapshots with publication-status/errata notes.

The initial archive build had 87 student PDFs and eight primary references;
63 full texts were blocked by repository human verification. After the owner
completed the browser check, downloads resumed at one concurrent request and
all 150 student PDFs were obtained. Three conflicting degree tags were corrected
against original title pages; replacements preserve the requested 10/8/7 quotas.
ZIPs and indexes report actual availability. No access
challenge is bypassed, and a citation record is never reported as a downloaded PDF.
Original documents remain private under ignored `data/research/`, separate from
the output-DLP investigation quarantine. Only catalogs, provenance and the owner-run
rebuild tool belong in Git. Preparation grants no internet access or document/tool
execution to the local model. See [research archives](RESEARCH_ARCHIVES.md).
