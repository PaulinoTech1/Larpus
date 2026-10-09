# Current verification ? 2026-10-08

47 tests passed after the local voice addition. A real British TTS WAV was
transcribed by VoiceStudio ASR/Faster Whisper in the offline CPU worker. A real
home-assistant reply passed MCP/DLP and produced seven seconds of speech.
Voice internet/LAN denial, loopback-only network, non-root identity and missing
Windows-drive/quarantine checks passed. Microphone/speaker browser acceptance
remains an owner check.

45 tests previously passed after TLS/local-auth changes. Live probes confirmed local API
access without authentication (200), LAN HTTPS without a session (401), certificate
validation and rejection of plaintext LAN HTTP. Updated login JavaScript is served;
full browser QA remains unrun. Twelve personas were listed by isolated MCP.
Isolation checks passed after resealing and owner-reported Windows reboot.

Second-device trust/chat, physically disconnected reboot, voice-device acceptance and OpenShell
remain pending. Earlier scan receipts are historical; compare source fingerprints.
See [decisions](DECISIONS.md).

## Historical record

# Kickoff verification — 2026-10-07

- `python -m unittest discover -s tests -v`: 43 tests passed. Real loopback HTTP
  handlers exercised with mocked inference: persona injection, body validation,
  length boundaries, upstream failures, busy lock, host/origin rejection, static
  asset serving/traversal rejection, health states, voice stub, password gate,
  login cookies/logout, session expiry, login/API limits, LAN client scope, and
  input-filter holds before inference. Text-filter tests cover Unicode, explicit
  overrides, scan failure, preservation, and a deliberate semantic bypass.
- MCP tests exercise the actual SDK stdio subprocess, discovery, input rejection,
  and chat against a loopback mock Ollama server. Route/redirect rejection,
  child environment and server-owned payload are checked separately.
- Ollama outbound firewall script is prepared but not applied: no installed
  Ollama executable/Admin privileges here. External egress enforcement is unrun.
- `node --check web/app.js` and `node --check web/login.js`: passed.
- `npm audit`: zero vulnerabilities after updating to KaTeX 0.19.0.
- Host gateway serves the HTML, persona API, health API, and local KaTeX assets.
- Live Ollama query at 127.0.0.1:11434 timed out; Ollama and Podman commands are
  not installed here. No live model, GPU-fit, voice, or sandbox claim is made.
- Browser inspection was attempted with the available computer-use tool, which
  returned “No browser is available.” Rendered visual QA at 375/768/1440,
  keyboard navigation, reduced motion, and full UI chat interaction remain unrun.
  CSS contains those responsive breakpoints; source inspection is not visual QA.

Owner acceptance: start Ollama with the configured local model, open localhost,
send a message, switch personas and confirm history reset, test the microphone
stub, and check the reactor in idle/thinking/error and reduced-motion states.
OpenShell/rootless Podman and voice acceptance gates are in DEPLOYMENT.md and
VOICE_INTEGRATION.md. Mock tests do not establish offline egress isolation.

Local skill tests cover selected system instructions, hash drift, imported origin,
extra executable files and persona allowlists. A real Python process verifies the
scanner wrapper denies sockets. Health tests cover MCP drift and unverified/stale
states. GPU inventory was observed; real model speed, quality and VRAM fit remain
unmeasured. The live health run correctly reports missing password and offline Ollama.
Static scanner evidence lives in ignored data/security; see HEALTH.md for scope
and limitations. These checks do not prove prompt-injection immunity.

Final SkillSpector static run: all four skills and the generated MCP target reported
complete, LOW severity, score 0 and zero issues. Input fingerprint matched current
sources. docs/SECURITY-SCAN-RECEIPT.json preserves the summary; full local reports
remain in data/security. The initial missing-scope warning was resolved by declaring
existing narrow capabilities, and an export reference was corrected to its bundled
filename. No runtime permissions were expanded. Semantic checks were disabled.

Output DLP tests cover real Windows quarantine ACL setup, clean staging deletion,
sensitive output retention without release, Unicode and encoded protected values,
copied system text, limits, storage/scan failures and full capacity. The real SDK
subprocess and authenticated HTTP gateway were exercised with a synthetic leaking
Ollama reply: HTTP returned 422 and an incident ID, while the fixture remained only
in local quarantine. The test removed that synthetic fixture. Another OS identity's
read attempt and hostile same-owner/native-code containment remain unrun.
The earlier scan receipt predates DLP; consult current data/security reports for
the expanded target, including the output gate and ACL script.

Final DLP scan summary is preserved in OUTPUT-DLP-SCAN-RECEIPT.json. Four prompt
skills remain clean. The expanded MCP target retains AST4 (the trusted Windows ACL
helper subprocess) and PE1 (the combined capability declaration); the health panel stays warning rather
than claiming a clean scan. Review: fixed OS PowerShell path, fixed script and
directory arguments, shell=False, no model/user text supplied to the invocation.
The narrow storage and ACL-helper capabilities are declared for transparency;
these scanner findings are not suppressed. File reads serve fixed policy loading,
writes serve inert output staging, and the helper sets restricted ACLs. None is a
model-callable MCP tool. Windows ACL readback confirmed protected
inheritance and only current-owner/SYSTEM access. This is not a second-identity
access test or proof of an OS sandbox.

Windows Home isolation is now provisioned: dedicated Ubuntu 24.04 Larpus WSL2,
locked-password larpus UID 1000, rootless Podman 4.9.3/cgroups v2, digest-pinned
Python/Ollama images and offline Linux wheels. Default mode is wsl-podman.
Actual pod and OCI inspection, external/LAN TCP denial, DNS/UDP send denial,
zero process capabilities, no-new-privileges, owner-drive/socket absence and
owner-only noexec quarantine were exercised. Ollama is reachable only inside
the pod; Windows has no Ollama 11434 listener. Model cache and the narrowly
selected NVIDIA driver package are read-only; no quarantine volume is mounted
into the model container. Model-side absence was checked with a real process.

A real qwen2.5:14b greeting passed Windows -> WSL -> MCP -> local inference ->
DLP, and Ollama reported 100% GPU at context 4096. This is a functional/fit probe,
not a quality/speed benchmark. A synthetic credential reply returned 422/incident
only; owner inspection confirmed its held record in the Linux quarantine. The
record survived rebuild and a dedicated-distro restart. No actual secrets were
used for these tests. Startup was retested from cached artifacts after terminating
only Larpus; Docker Desktop remains the default distro. A full Windows reboot,
physical network-disconnected reboot and another LAN device's real UI session
remain unrun. Station password setup is still required; it was not generated.
Current scanner findings remain warnings, not a clean/full-audit claim.

The current isolation scan receipt is WINDOWS-HOME-SCAN-RECEIPT.json: all four
local skills passed; the expanded MCP target completed with eight findings and
MEDIUM aggregate risk (including one HIGH pattern finding). The HIGH Docker
socket pattern in namespace_probe.py is an assertion that the socket is absent;
it does not open or mount that socket. Six subprocess patterns cover the fixed
ACL helper and fixed WSL/Podman inspection, probe and owner-investigation commands.
The remaining LOW finding is the combined capability declaration. These are
reviewed static findings, retained as warnings rather than suppressed. This is
not proof against a compromised host, kernel, driver or trusted guard.

## Role-specific skills (2026-10-08)

All 49 unit/integration tests pass, including five exclusive specialist skills
per persona, rejection of every cross-role specialist selection, and the bounded
128-entry registry. All 64 skill frontmatters pass skill-creator validation;
the runtime validates their exact hashes, text and prompt-only folder contents.

The sealed image loads 12 personas and 64 skills. Live isolation probes confirm
denied external/LAN access and DNS, absent host paths, owner-only quarantine and
zero effective/bounding capabilities. Actual MCP descriptors match the approved
three-tool baseline. A selected AES skill produced a 200 response through local
Ollama and the output DLP boundary. This is a functional smoke test, not a
subject-matter quality evaluation across all roles or proof against prompt attacks.

The current offline SkillSpector receipt is [ROLE-SKILLS-SCAN-RECEIPT.json](ROLE-SKILLS-SCAN-RECEIPT.json). All 64 skills passed complete static scans with zero findings. The MCP target completed with eight findings and MEDIUM aggregate risk; these remain visible warnings, so overall health is degraded rather than falsely green. No network or LLM inference was used by the scanner.
