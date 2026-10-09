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

## Qwen3.5 27B Q4 GPU deployment (2026-10-09)

53 Python tests and the voice UI state checks pass. The new GPU residency guard
rejects CPU, partial-offload and unloaded placement, and malformed reports fail
closed. Fixed loopback routes still reject model pulls, arbitrary URLs and redirects.

The real installed qwen3.5:27b-q4_K_M reports 100% GPU at context 4096 and stays
loaded indefinitely. Warm fixed probes measured 40.86 and 41.57 tokens/s; the cold
probe took 31.587 seconds total, including 26.256 seconds model loading. Numeric
receipts and limitations are in [model deployment](MODELS.md). All twelve live
HUD personas target this model. A real localhost request completed gateway ->
MCP -> GPU model -> isolated DLP -> CPU speech synthesis in 6.31 seconds, returning
an approved 92-character reply and a 244,268-byte WAV. This one short probe is
not an arbitrary-reply latency or speech-recognition quality benchmark.

Actual health reports model_gpu and voice as pass, along with network-isolation
and other functional checks. It remains degraded for the eight retained static
MCP findings. The temporary network-enabled download container was stopped and
removed after Ollama SHA-256 verification. Only the production no-network model,
agent, voice and infra containers remain running; no ports or mounts were added.

## Sentence streaming (2026-10-09)

61 Python tests, `npm run test:voice-ui` and `npm run test:chat-ui` pass. The
streaming tests cover early gateway flush, cumulative/quarantined DLP including
split protected values, unchanged MCP descriptors, GPU placement, bounded
NDJSON, incomplete UI history and ordered/prefetched/paused/cancelled speech.
The agent was rebuilt with `--pull=never --network=none`; its prior container is
retained stopped for rollback. All six isolation checks pass. A six-sentence
sealed-MCP probe released first text at 4.513 seconds and completed at 8.246
seconds. See [streaming contract and limitations](STREAMING.md). Physical audio
and second-device LAN acceptance are separate from these automated checks.

A live gateway probe then streamed first text at 3.136 seconds, returned the first
sentence's CPU WAV at 5.936 seconds while generation continued, and completed
at 6.190 seconds. Local HTTP returned 200 without authentication; local-CA-verified
LAN HTTPS returned 401 without authentication. The [streaming scan receipt](STREAMING-SCAN-RECEIPT.json)
retains the same eight MCP warnings and 64 clean skill targets. Functional health
checks pass; overall status remains degraded for the scanner warnings.

## Approved local knowledge (2026-10-09)

72 Python tests pass through `scripts/test-local.py`, which uses a temporary
public fixture index and copies no owner credentials, private PDFs or recordings.
Both voice and chat UI suites pass, including separate source display and speech.
New checks cover role restrictions, immutable SQL, index tampering, selected
instruction injection, bounded context, fail-closed missing evidence storage,
mixed-vendor CPU shorthand and public specifications versus station claims.

The deployed index contains 201 distinct documents and 36,092 role-scoped
passages (passages shared across roles count separately). It includes 43 prepared
documentation/brief items and the existing 158 research PDFs. Eleven PDFs remain
explicitly metadata-only; 1,634 passage instances were excluded by preparation
checks. Six original documentation downloads remain unavailable, with labelled
reviewed briefs covering the requested CPU/RHEL facts. This is selected coverage,
not a complete distribution manual, OCR completion or a quality audit of every
research result. See [knowledge contract](APPROVED_KNOWLEDGE.md) and
[documentation catalog](../knowledge/CATALOG.md).

The agent image was rebuilt with `--pull=never --network=none`. All six behavioral
isolation checks pass, and MCP descriptors remain the same three approved tools.
Real sealed-MCP probes produced cited Ubuntu GA kernel comparisons, RHEL backport
explanations, stable versus release-candidate distinctions, and both CPU briefs.
The numerical-PDE probe declined to invent a limitation absent from its selected
excerpts; this illustrates both grounded uncertainty and lexical retrieval limits.
These focused probes verify the data path, not general scientific accuracy or
complete resistance to prompt attacks. Original research PDF bytes are unchanged.

The restored gateway streamed the cited Ubuntu comparison with first text at
5.390 seconds and completion at 6.077 seconds in one live probe. CPU speech
returned a 361,516-byte WAV for a public CPU specification sentence. Local HTTP
and persona discovery returned 200 without a password; CA-verified LAN HTTPS
persona discovery returned 401 without authentication. Physical playback and
second-device LAN acceptance were not performed in this check.

The [knowledge scan receipt](APPROVED-KNOWLEDGE-SCAN-RECEIPT.json) matches the
deployed source fingerprint: all 64 local skills completed cleanly; the MCP
target retains eight findings and MEDIUM aggregate risk. These visible warnings
keep overall health degraded. Functional checks, including approved knowledge,
GPU placement, CPU voice and network isolation, pass. Focused model responses
are recorded in [probe evidence](APPROVED-KNOWLEDGE-PROBES.json).

## Shared reading and AI references (2026-10-09)

This update supersedes the earlier document role restrictions: every configured
persona can retrieve all approved documents, with role-based relevance preference.
Skill selection permissions remain unchanged. 77 Python tests and both UI suites
pass, including all-persona shared access, native-role ranking, duplicate-row
handling, mixed-model comparisons and exact official AI-document URL validation.

Seven new official publisher pages downloaded through the vetted HEAD/GET path;
seven separately labelled factual briefs were added. The rebuilt index contains
215 documents and 36,149 passages (including shared-role duplicate physical rows),
with eleven metadata-only research documents and six earlier unavailable originals.
The new agent image was built without network/pulls; all six isolation probes pass.

Live sealed-MCP answers returned dated DeepSeek peak/off-peak prices, both model
references, both subscription references and cross-subject Linux evidence for the
home assistant. These are data-path checks, not general accuracy certification.
The [retained probe evidence](SHARED-KNOWLEDGE-PROBES.json) explicitly records a
wrong inferred Sol/Astra cache-write ratio, an unsupported Claude Code interface
claim and missing inline citations in some replies. Actual selected references
still reach the HUD. Users should check generated calculations against the cited
figures. Muse remains pending product identification.

The [current static scan receipt](SHARED-KNOWLEDGE-SCAN-RECEIPT.json) matches the
source and deployed image fingerprint: 64 clean skills and the same eight MCP
warnings (MEDIUM aggregate risk). Functional health checks pass; overall health
remains degraded for those warnings. The restored gateway returned all eight
requested Sol/Astra base/cache prices with source IDs, first text at 4.707 seconds
and stream completion at 11.078 seconds in one focused probe. CPU TTS returned
a 251,436-byte WAV. Local HTTP returned 200 without authentication and CA-verified
LAN HTTPS returned 401 without authentication. See
[gateway probe](SHARED-KNOWLEDGE-GATEWAY-PROBE.json). Physical audio and a second
LAN device were not tested. Changes were not committed or pushed.

## Available updates (2026-10-09)

Live chat returned HTTP 200 during checkout drift (6.694 seconds) and during the
candidate static scan (5.508 seconds). The frozen candidate passed 85 Python
tests, both UI checks, all six isolation probes, and the static scan gate:
64 clean skills and the same eight previously reviewed MCP warnings. Functional
health passes; those warnings keep overall health degraded.

A live streamed reply reached `done` while rollback drained the serving gateway;
the rollback operation completed in 8.92 seconds, including checks and draining.
Deliberately exiting the owned candidate gateway at startup caused automatic
restoration of the previous release. An unprepared candidate was rejected with
the active gateway PID unchanged. The new release was activated again and left
running with no pending journal. Local HTTP is password-free; CA-verified LAN
HTTPS still returns 401 without authentication. CPU voice returned audio.

The first activation exposed an owner readiness endpoint error; it was corrected
to `/api/station-health`. Regression coverage also preserves a restored gateway's
new PID when clearing an interrupted journal. The current checkout has 88 Python
tests (the frozen candidate predates three owner-tool tests). See
[live probes](AVAILABLE-UPDATES-PROBES.json) and the
[candidate scan receipt](AVAILABLE-UPDATES-SCAN-RECEIPT.json). Physical audio and
second-device LAN use were not tested. There is a brief listener interruption;
LAN sessions require login again. Changes remain uncommitted.

## Meta Muse home reference update (2026-10-09)

Three official Meta pages were downloaded through reviewed exact URLs and pinned
by SHA-256; six compact local briefs cover the agent, conditional referral claim,
Spark versions, related families, pricing and Grok Bot comparison. The rebuilt
shared library contains 224 documents and 36,181 passages. All twelve personas
retrieve Muse evidence; three focused retrieval tests cover referral uncertainty,
Spark shorthand/audio limits and representation of both compared agents.

The candidate passed the configured Python suite (91 tests), both UI checks,
six isolation probes and the scan gate: 64 clean skills, unchanged eight MCP
warnings. Live production chat returned 200 in 6.468 seconds during preparation.
The prepared release was activated with its previous release retained. Functional
health passes; overall health stays degraded for the existing scan warnings.
Local HTTP chat is password-free, and CA-verified LAN HTTPS still returns 401
without authentication.

Sealed candidate replies correctly distinguished the two agents and qualified
the billion-token report; focused replies covered limited free usage and Spark
1.3 audio support. The combined comparison omitted an explicit free-tier answer,
covered by the focused probe. After activation, a live reply distinguished agent
credits from API billing but invented an expiry assertion and gave an imprecise
API price range. The sources do not establish expiry, and contain exact tier/unit
prices. These limitations are retained rather than counted as fully accurate
answers. Referral terms remain not independently primary-source verified; no
vendor account, balance or promotion redemption was tested.

Evidence: [retrieval](META-MUSE-RETRIEVAL-PROBES.json),
[candidate comparison](META-MUSE-CANDIDATE-PROBE.json),
[focused candidate answers](META-MUSE-FOCUSED-PROBES.json),
[live gateway](META-MUSE-GATEWAY-PROBE.json), and
[static scan receipt](META-MUSE-SCAN-RECEIPT.json). No cloud inference service,
external account or model replacement was introduced. Changes are uncommitted.

## Local GitHub repository archive (2026-10-09)

Authenticated connector and native REST owner listings agreed on 22 repositories,
including two private repositories. Every full Git mirror passed `git fsck`;
default-branch snapshots materialised 19,534 files (416,186,199 bytes). Another
200 Windows-incompatible paths remain in the mirrors. No LFS pointers were found
in materialised snapshots. This does not cover issues, release assets or external
submodule targets. No downloaded project code/hooks/skills were executed.

The combined index contains 247 documents and 44,034 passages, including 7,853
GitHub source/catalogue rows. All twelve personas retrieved scoped repository
evidence. Six new tests cover Windows path escapes, excluded credential/prompt
paths, secret/injection screening, source/manifest drift, optional configuration,
catalogue selection, project scoping and comparison coverage. The candidate's
configured Python suite (97 tests), both UI checks and six isolation probes passed.
The scan gate passed with 64 clean skills and the unchanged eight MCP warnings.

Production chat returned 200 in 4.797 seconds during preparation. Sealed candidate
replies listed all 22 names and answered DMARC/JML questions from their READMEs.
The new release was activated, retaining the previous release for rollback. Live
local HTTP chat then listed every expected repository name (200, 10.25 seconds).
CA-verified LAN HTTPS remains authenticated (401 without a session). Functional
health checks pass; overall health remains degraded for existing scan warnings.
No pending cutover journal remains. Original repositories and private probe reports
are outside the runtime/web tree under ignored `data/github`.

See [summary evidence](GITHUB-ARCHIVE-VERIFICATION.json),
[scan receipt](GITHUB-ARCHIVE-SCAN-RECEIPT.json) and
[archive/refresh limits](GITHUB_ARCHIVES.md). Original mirrors are complete Git
objects, while the searchable index is bounded and excludes recognised sensitive
or instruction-bearing content. Retrieval and focused replies do not certify all
generated conclusions, repository security or exhaustive secret detection.
No GitHub credentials, internet connection or write tools were added to the LLM.
Changes remain uncommitted.

## Microsoft implementation and context controls (2026-10-09)

Eleven individually reviewed Microsoft Learn HTML snapshots and five authored
briefs were downloaded, SHA-pinned and screened into the shared library. All
sixteen have indexed passages. The library contains 263 documents and 44,500
role-tagged passages, preserving the previous research and GitHub references.
Five new local-authored prompt-only skills are allowlisted for System
Administrator and IT/Cybersecurity LARP Coach, bringing the registry to 69.

The new Python checks cover scoped skill selection with retained history,
measured context metadata on streaming and non-streaming paths, invalid/missing
counts, original personality boundaries, exact Microsoft URL/query scope and
exact release scan targets with missing/duplicate/unexpected-target rejection.
The new Node regression checks retained skill and persona conversations,
measured meter updates, invalid counts and explicit reset. Existing voice and
sentence/DLP streaming regressions remain in the preparation gate.

A final candidate two-turn MCP probe retained the Copper Finch pilot name after
switching Entra to BitLocker skills, returned dated source IDs, streamed five
approved reply chunks and omitted zero history messages. Measured contexts were
1,442 input / 122 output and 1,674 input / 106 output tokens; these are observations,
not fixed benchmarks. The earlier verbose prompt omitted history sooner, prompting
removal of duplicate character guidance before the final candidate was staged.
Active production chat succeeded during preparation (HTTP 200, 6.28 seconds).

Browser automation reported no available surfaces; both in-app browser and Chrome
creation were unavailable. Rendered visual checks at 375, 768 and 1440 pixels,
real browser dropdown interaction and actual screen-reader behaviour remain
unverified. Node DOM regressions do not establish visual or browser usability.
Generated coaching remains probabilistic: focused reference/citation and memory
checks do not certify every licensing or implementation conclusion. Review a
proposed change against its official snapshot and current tenant requirements.

An earlier full candidate scan blocked all five Microsoft skills for a negated
credential phrase and added an MCP prompt-leakage match on a prohibitive comment.
The reports matched words inside explicit prohibitions, rather than an operation
that reads credentials or returns instructions. Wording was clarified without
weakening the prohibition; registry hashes were repinned. Focused static rescans
then completed with zero skill findings and the same eight baseline MCP findings.
No scanner rule, threshold or release gate was relaxed. Blocked candidates were
never activated. Private intermediate reports remain under ignored data/ folders.

Final prepared release `807c76f50c2c4f38ac9d859be935c713` is active, with
`1fb042ecf3a74d4ea4c0d4604d7a1534` retained for rollback and no pending cutover.
All 103 Python tests, three Node regression suites and six isolation probes passed.
All 69 local skills completed clean static scans; MCP completed with the unchanged
eight warnings (MEDIUM aggregate risk). Functional health passes and overall
health correctly remains degraded. See [receipt](MICROSOFT-VERIFICATION.json).

Live local HTTP serves the updated HUD and all 69 skill definitions. Two streamed
requests retained Copper Finch across Entra/BitLocker skill changes (7.17 and
6.97 seconds, 7 and 4 approved chunks), with zero history omissions and dated
Microsoft source metadata. Actual token totals were 1,540 and 1,720 of 4,096.
CA-verified LAN root redirects to login; its unauthenticated persona API returns
401. Local loopback HTTP remains password-free. No model/voice image, binding,
credential, cloud runtime or volume change was made. Work remains uncommitted.

## Owner project attribution (2026-10-09)

All 22 archived repositories have separate searchable inventory records. Home,
sysadmin and cryptographer retrieval checks return the complete local catalog.
The owner declaration now enters every persona's shared evidence instructions:
these PaulinoTech1 repositories are the owner's work, with upstream/contributor
credits and licenses preserved and no inferred production experience.

Release `0aa208337b6e479ebfdf97af0554213e` passed 105 Python tests, three UI
regression suites, six isolation probes, 69 clean skill scans and the unchanged
eight MCP warnings. It is active with the prior release retained. A live gateway
reply listed all 22 exact repository names, omitted none, cited github-catalog,
and explicitly attributed the collection to the owner (HTTP 200, 9.95 seconds).
Functional health passes; overall health remains degraded for the known warnings.
See [public count-only receipt](OWNER-ATTRIBUTION-VERIFICATION.json). Detailed
replies and private source inventories remain in ignored data/github. Raw Git
mirrors, credentials, local search database and private archive pins are excluded
from the commit. The model remains offline with no GitHub write or browsing tool.
