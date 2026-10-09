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

## Voice correction and playback controls (2026-10-09)

Push-to-talk and transcript review are defaults because ambient sound and Whisper
hallucinations can create unwanted messages. Hands-free and auto-send remain explicit
choices. The browser chooses a microphone by exact device ID; audio processing stays
local and no device metadata leaves the page. VAD, deterministic decoding and segment
confidence checks reduce false recognition without claiming perfect accuracy. Playback
is independently controlled, retains position on pause, has a speed slider and can
replay any displayed reply. Replay text is bounded and rechecked by input filtering
and DLP before TTS; the isolated generated-output quarantine path remains intact.
Wit is a scoped persona instruction, not a speech-model capability or invented
credential. No new ports, mounts, tools, external downloads or accounts were added.

## Qwen3.5 27B Q4 GPU, CPU voice (2026-10-09)

All personas target qwen3.5:27b-q4_K_M at 4096 context. Conversational requests
disable thinking, request GPU layers and retain the loaded model. The runtime
checks actual Ollama GPU residency before releasing a generated response; CPU or
partial-offload answers fail rather than silently becoming slow. Health and the
HUD distinguish loaded-model placement from mere NVIDIA hardware availability.
Voice remains CPU-only in its existing network-disabled, device-free container.
System RAM usage is not evidence of CPU-only inference: the previous qwen2.5:14b
was verified 100% GPU before this switch. Public weights are retrieved only by a
temporary, separate preparation container, which is stopped after verification.
See [model deployment and verification](MODELS.md).

## Sentence streaming with cumulative DLP (2026-10-09)

The HUD releases inspected sentences during generation over the existing local
MCP progress channel and a same-origin NDJSON route. CPU speech runs as a separate
FIFO queue with one WAV prepared ahead, so synthesis does not block text delivery.
Whole-response chat remains available. Every release stages and checks the full
generated prefix, with incomplete protected phrases held across boundaries.
Later holds stop remaining output and audio; already released clean sentences
cannot be retracted. Incomplete replies never enter browser conversation history.
See [streaming behavior and verification](STREAMING.md) for the exact contract
and limits. GPU inference, CPU voice, LAN authentication/TLS, rate limiting and
network-disabled containers retain their existing scopes.

## Vetted local evidence rather than model browsing (2026-10-09)

Owner-reviewed publisher snapshots and checksum-pinned archived research feed a
CPU-only SQLite FTS index inside the read-only agent image. Retrieval is trusted
runtime code behind the existing chat tool; there is no new filesystem/browser
tool or network access. Roles receive only permitted, bounded, rescanned passages
as quoted data, with actual source metadata displayed after the answer. The
model can reason about this evidence to bridge training-era gaps without weight
updates. Exact kernel/distribution versions and snapshot dates matter; backports
and release candidates are distinguished from upstream stable releases.
Blocked downloads remain recorded; official-source factual briefs are labelled,
and image-only PDF coverage is marked as metadata-only. Public CPU product facts
are discussable while host-inventory claims retain a scoped output check.
See [curation, retrieval and rebuild contract](APPROVED_KNOWLEDGE.md).

## Shared reading with role priorities (2026-10-09)

The owner explicitly replaced document read restrictions with shared access.
All twelve configured personas can retrieve any approved document; source role
labels now influence ranking rather than authorisation. Native-role relevance
gets a modest boost, shared rows are deduplicated and named comparisons preserve
evidence for each subject. Specialist skill selection allowlists remain exclusive.
Evidence remains bounded, untrusted and subject to input/output checks.

The home assistant prioritises official AI product/model/pricing references.
ChatGPT Plus/Codex, GPT-6.1 Sol, GPT-6 Astra, SuperGrok/Grok Bot, Claude Pro and
DeepSeek V4 Pro/Flash are dated reference snapshots, not installed services.
API rates are distinct from subscriptions; retired Flash aliases and peak/cache
conditions are preserved. Muse remains unidentified pending an owner URL/name.
See [AI references and price conditions](AI_PRODUCT_REFERENCES.md).

## Keep production independent of checkout updates (2026-10-09)

Production executes a frozen source/UI/approved-index snapshot and a separately
pinned offline agent. Checkout edits, tests, builds and static scans prepare a
candidate beside production. Owner activation drains existing requests, briefly
rebinds the same listeners, checks functional station health and restores the
previous release if startup fails. Shared GPU model and CPU voice stay running.
No new network service or model update tool was added. Owner state remains shared;
incompatible migrations and shared dependency upgrades need separate planning.
This provides preparation availability and recoverable cutovers, not zero downtime.
See [update workflow and limitations](UPDATES.md).

## Meta Muse identification and agent recommendations (2026-10-09)

The owner identified Muse as Meta's personal agent, replacing the earlier pending
identification. Three reviewed official snapshots and six compact local briefs
cover Muse, Muse Spark/related families, API tiers and the Grok Bot comparison.
The home persona compares practical tasks, eligibility, costs and privacy rather
than treating agents as model names. Every persona retains shared reading access.
The owner-reported billion-token referral bonus is included with explicit
primary-source verification limits: its announcement was inaccessible, so no
eligibility, code, cap, expiry, cash value or API entitlement is promised.
External agents remain reference subjects; local model/voice and egress isolation
are unchanged. Deployment uses the available-update workflow.

## GitHub access through owner-side archives (2026-10-09)

The owner authorised downloading all owned GitHub repositories. Authenticated,
paginated owner discovery and native Git/GCM run only during preparation. Full
Git mirrors and inert commit snapshots remain outside the model sandbox; screened
source/docs join the shared read-only reference index. No GitHub credential,
network client, write tool or downloaded skill is exposed to the LLM.
Repository queries scope to named projects, reserve comparison evidence and
provide a complete local catalogue. Original files are not served by the gateway.
Windows-incompatible paths stay in mirrors, with explicit snapshot exclusions.
See [archive, screening and refresh contract](GITHUB_ARCHIVES.md).

## Microsoft coaching and continuous conversations (2026-10-09)

Add individually reviewed Microsoft Learn snapshots for Intune, Entra ID, Azure,
Microsoft 365 and BitLocker to the shared reference library, with five local
implementation skills shared by System Administrator and IT/Cybersecurity Coach.
Preserve existing role-exclusive skills. No live tenant integration or cloud
runtime access is introduced. Treat Windows Home edition constraints explicitly.

Switching skills and personas retains browser-memory conversation; RESET remains
explicit. Show latest Ollama-measured input/output token use against 4096 tokens,
including gateway omission count, rather than estimating from visible text.
Release scanning checks the exact frozen registry target inventory instead of
assuming a fixed skill count. All targets must complete and new MCP findings block.

Give every role the same original eccentric British LARPUS character: concise
wit, evidence-led pushback and practical alternatives, with no insults, invented
objections or loss of specialist boundaries. See [implementation contract](MICROSOFT_IMPLEMENTATION.md).
