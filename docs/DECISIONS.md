# Larpus decision record

Dated historical decisions and observations; deployment IDs and settings describe their recorded time. See [STATUS.md](STATUS.md) for the current dated snapshot. Older entries do not override later decisions.

## Name, author credits and clean speech (2026-10-09)

Every persona prompt now states "Your name is LARPUS; if asked your name, say
LARPUS" (the opening line was also capitalised from "larpus").

Research evidence items carry a `cite` field (for example "Blackwell, 1956")
from `knowledge/authors.json`, generated from the reviewed `research/catalog.json`
and shipped in the sealed image with the index. The evidence prompt asks the model
to credit authors in writing as (Author, Year) [source-id] and never invent names.

Speech is cleaned in the HUD (`speakable()` in `web/voice.js`) before synthesis:
markdown headings, bold/italic markers, list bullets, backticks, code blocks,
URLs, link syntax, bracketed source IDs and (Author, Year) credits are removed, so
LARPUS never reads symbols or citations aloud while the transcript keeps them.
`tests/speech-text.cjs` covers this.
## Butler-parody personality and natural speech pacing (2026-10-09)

The shared LARPUS character line in all twelve personas now describes an original
parody of a polished British AI butler: unflappable, quick and drily sarcastic,
addressing the owner as "boss", with a deadpan remark most of the time rather than
an occasional aside, and no servile filler. Retained rules: useful answer first,
challenge flawed assumptions with a practical alternative, pushback never targets
the person, no wit for distress, health, safety or serious incidents, and evidence
outranks performance. It explicitly must not claim to be JARVIS, Iron Man or any
trademarked figure.

Piper speech moves from `length_scale=0.85` (rushed, clipped) to natural pace
`1.0`, `noise_scale=0.6`, `noise_w_scale=0.8`, and inserts 0.22 s of silence
between sentence chunks from `PiperVoice.synthesize` (piper-tts 1.8.0). The voice
remains `en_GB-alan-medium` on CPU; a more natural CPU voice (for example Kokoro
British male voices) is a separate planned change needing offline model prep.
## Psychologist game theory sources (2026-10-09)

The research archive gains a seventh role, `psychologist`, with its own curated
quota (`ROLE_QUOTA` in `scripts/research-archive.py`: 2 doctoral theses plus
uncounted primary references); the original six roles keep 10/8/7. Added and
hash-pinned in `research/catalog.json`, indexed into the approved library:

- David Blackwell, "An analog of the minimax theorem for vector payoffs",
  Pacific Journal of Mathematics 6(1), 1956 (reference; 27 passages).
- Meng-Jhang Fong, "Essays in Behavioral Economics and Game Theory", Caltech
  Ph.D., 2024, DOI 10.7907/5xh7-yw15 (359 passages).
- Po-Hsuan Lin, "Essays in Behavioral Game Theory Solution Concepts", Caltech
  Ph.D., 2024, DOI 10.7907/kbwg-w708 (680 passages; repository lists
  "Degree: Other", PDF title page states Doctor of Philosophy).

Verified real but not downloaded because the hosts served human-verification
pages to automated requests: Blackwell "Comparison of Experiments" (Second
Berkeley Symposium, 1951, Project Euclid open access), Blackwell "Infinite Games
and Analytic Sets" (PNAS 1967, PMC223869), and Kleiman-Weiner "Computational
foundations of human social intelligence" (MIT Ph.D., 2018). They can be added
with `research-archive.py --import-dir` after a manual browser download.
Blackwell & Girshick, Theory of Games and Statistical Decisions (1954), has no
official open copy and is not archived. Rights notes are recorded per entry;
public access is not permission to redistribute.
## Failed activation readiness and failed rollback (2026-10-09)

### What happened

Activating release `d139aa4e80eb` (HUD context meter fix: replace the hardcoded
262,144 placeholder with 131,072) prepared cleanly, then `activate` failed with
`New gateway functional readiness failed`. The cutover path then tried to relaunch
the previous release `82e6ad9e3450` and hit the same readiness error, leaving
`data/releases/active.json` with `"pending": true` while the Windows gateway
process for `82e6ad9e3450` was still answering HTTP. Production chat stayed up on
the old release; the new agent container was running but not selected.

### Root causes (two independent bugs)

1. **Unloaded model trips a hard readiness gate.**
   `scripts/releases.py` `ready()` requires every named check in
   `/api/station-health` to be `"pass"`, including `model_gpu`. That endpoint
   serves `runtime.health.read_latest()`, a file written by a 60-second monitor
   and treated as stale after 180 seconds � it is not a live probe. After the
   earlier WSL memory restart, Ollama had no resident model (`model_processors`
   reported `"unloaded"`), so the cached report kept `model_gpu: warning`. Live
   `/api/health` later showed GPU after a chat load, but readiness still failed
   until the monitor rewrote the file. Voice stayed CPU-only
   (`faster-whisper` `device='cpu'`, Piper on CPU, no GPU device on the voice
   container) and was unrelated.

2. **`prune` stopped the prepared candidate.**
   After the failed cutover, `activate` still called the new `prune()` helper.
   Prune kept only the active and previous release agents/voice and the model.
   The prepared `larpus-agent-d139aa4e80eb` was not yet active, so prune stopped it.
   The next activate then failed with `Container stopped or image drifted`
   before another readiness wait.

### Thought process used to recover

- Treat a readiness failure as "which check failed?", not as "the release is
  bad". Diff live `/api/health` (immediate Ollama placement) against
  `/api/station-health` (cached monitor). `model_gpu: warning` with an unloaded
  model explained both the failed candidate and the failed restore.
- Reload the model at the configured context (`num_ctx` 131072, `num_gpu` 99,
  `keep_alive` -1) through the sealed agent's allowed chat route, then confirm
  `context_length` and `size == size_vram` from `/api/ps`.
- Fix prune before retrying: keep any release folder newer than the active
  release that already has a `deployment.json`, so prepared candidates survive
  until activation or discard. Never `rm` containers; stop only.
- Restart the stopped candidate container, clear the pending state by a clean
  `activate`, then confirm `status` shows the new id running, previous retained,
  and prune keeping only the two agents, the shared voice worker and the model.

### Resolution and follow-ups

- Release `d139aa4e80eb` was active at this decision; HUD meter default and accepted capacities include
  131072 (still accepts 4096/16384/262144 for older measurements).
- `prune` keeps prepared candidates; documented in UPDATES.md.
- Operational rule: after WSL/`wsl --shutdown`/model-cache swaps, wait for
  `model_gpu: pass` on station-health (or send one chat to load the model and
  wait one monitor cycle) before `activate`. Voice remains CPU-only by design so
  the 24 GB card can stay filled by the text model.

## q8_0 KV cache at 131K context (2026-10-09)

The live model already ran `OLLAMA_KV_CACHE_TYPE=q4_0` with flash attention
(set by `scripts/model-cache.py`), which earlier notes missed. To reduce
long-context quality loss the cache moves to `q8_0` and the context to 131072
tokens (`config/models.json` `num_ctx`, `runtime/context.py` `CAPACITY`).
Side-container fit probes on 2026-10-09 (production paused, same image and mounts):
q8_0 at 150000 was 22,313,508,535 bytes, fully GPU-resident, but the card reached
24,001 of 24,564 MiB (about 560 MB free); q8_0 at 131072 was 21,556,960,951 bytes,
fully GPU-resident, 23,547 MiB used (about 1 GB free). 131072 was chosen for
headroom so desktop GPU use cannot push layers to CPU and trip the residency check.
For comparison q4_0 at 150000 was 19,855,646,391 bytes. `model-cache.py` now
probes the configured `num_ctx` instead of a hardcoded 262144. Applied with
`python scripts/model-cache.py apply --cache q8_0`.
## 150K-token context window (2026-10-09)

The conversation context rises from 4096 to 150000 tokens (`config/models.json`
`num_ctx` and `runtime/context.py` `CAPACITY`); the output cap stays 1024 and
`INPUT_BOUND` follows as capacity minus output minus 1024. The model's advertised
262144 was tried first but backed down to keep headroom on the 24 GB RTX 3090 Ti.
Probe on 2026-10-09: Ollama loaded qwen3.5:27b-q4_K_M at context 150000 in 20.5 s,
19,855,646,391 bytes total and GPU-resident (100% GPU), about 22.5 GB VRAM in use.
No KV cache quantization is set yet; that is the next planned change and needs its
own fit probe. `runtime/models.py` benchmarks still probe at 4096/256. Earlier
references to a 4096 context below are historical. Deployed via
`scripts/releases.py` stage/prepare/activate, not a pod teardown.

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

All personas target qwen3.5:27b-q4_K_M at 131072 context. Conversational requests
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
explicit. Show latest Ollama-measured input/output token use against 131072 tokens,
including gateway omission count, rather than estimating from visible text.
Release scanning checks the exact frozen registry target inventory instead of
assuming a fixed skill count. All targets must complete and new MCP findings block.

Give every role the same original eccentric British LARPUS character: concise
wit, evidence-led pushback and practical alternatives, with no insults, invented
objections or loss of specialist boundaries. See [implementation contract](MICROSOFT_IMPLEMENTATION.md).

## CPU semantic search and reranking (2026-10-09)

The owner approved one online preparation fetch: BAAI/bge-small-en-v1.5 ONNX
(revision 5c38ec7c405ec4b44b94cc5a9bb96e735b38267a) and BAAI/bge-reranker-base
ONNX (revision 2cfc18c9415c912f9d8155881c133215df768a70), plus onnxruntime 1.23.2,
tokenizers 0.23.3 and numpy 2.2.6 wheels installed with `--no-deps`. Every file
size and SHA-256 is pinned in `config/cpu-retrieval.json`; wheel hashes are also
in `requirements-retrieval.txt`. `scripts/prepare-retrieval.py` fetches, verifies,
syncs to the WSL build cache and builds the index; the agent image gets them only
from that offline cache (models in their own reused layer).

Retrieval stays BM25-first: up to 10 BM25 candidates plus 6 embedding neighbours
are scored by the cross-encoder within a 0.9 s budget, with BM25-rank and reviewed
brief priors; semantic-only passages need a non-negative relevance score. Version,
platform and topic-anchored questions and repository scopes never gain semantic
rows. Existing filters, per-source caps, budgets and continuations apply after
ranking. Study notes are reranked within 0.4 s. Any missing package, model or index,
hash mismatch or runtime error falls back to the previous BM25 order. The index
(`knowledge/embeddings.npy`, float16, 43,549 unique passages) is bound to the
approved database hash and embedder revision; rebuild it after every library rebuild.

ONNX Runtime uses only the CPU provider (asserted), 8 intra-op threads, no GPU,
no Ollama and no network. Agent container limits rise from 1 GB/2 CPUs to
12 GB/8 CPUs. Hybrid ranking added about 1 s per question on a busy host.

## Persistent CPU retrieval worker (2026-10-09)

Each chat starts a fresh MCP child, so loading the retrieval models per process
added 3.5-4.6 s per chat. The agent image now runs `runtime.retrieval_worker`
as its main process: it hash-verifies the models and embedding index once at
start, keeps them loaded (8 CPU threads, about 1.7 GB RSS) and answers on an
owner-only (0600, same-UID peer) Unix socket in the agent's private /tmp.

Unlike voice, it stays inside the agent container: the caller is the MCP child in
that container, so a separate container would need a shared mount or network path
and would add a new boundary. No TCP listener, mount, device or egress is added;
the pod remains network-disabled and within the 12 GB/8 CPU agent limits.
Requests are strict, size-bounded JSON (question, at most 32 passages, budget at
most 5 s); the database is still read and filtered in the chat process. In the
image (`LARPUS_RETRIEVAL_WORKER=remote`) a chat never loads models itself: a
missing, failed or slow worker means BM25 order. The worker stays alive without
listening if verification fails. Host tools still load models in-process.
## Mathematics library expansion and training_use rights tag (2026-10-10)

The mathematician archive gains 37 owner-approved documents: 5 doctoral theses
(Cambridge, Imperial, Georgia Tech, Utrecht, ETH Zurich) and 32 textbooks/course
notes in calculus, real/complex analysis, measure theory, ODE/PDE, functional
analysis, linear algebra, convex optimization and topology. `ROLE_QUOTA` in
`scripts/research-archive.py` sets mathematician to 10/8/12 (phd 7 -> 12); the
textbooks/notes are uncounted `references` (degree field states they are not
student quota entries), following the existing NIST/Blackwell convention.
22 hosts were added to `RESEARCH_HOSTS`, each commented with its institution. DOI
and handle resolver URLs (doi.org, hdl.handle.net) were replaced by the ETH Research
Collection and Georgia Tech repository record URLs, so no resolver is allowlisted.

Rights review: 10 items carry no explicit licence (faculty course notes or
books publicly posted on university domains): hunter-measure-theory, driver-analysis-tools, hunter-pde-notes, dunkel-1804-complex-analysis, princeton-mat330-complex-analysis, nemirovski-modern-convex-optimization, hatcher-point-set-topology-notes, hatcher-3-manifolds, may-concise-algebraic-topology, cavalieri-math490-topology. The owner approved
them on 2026-10-10 for private offline use only. Each new entry has a
`training_use` field: `private-only` for those 10, `allowed` for the rest
(explicit open licence or author permission statement). `research_policy.vet()`
rejects any other value. Missing `training_use` (all pre-existing entries) means
not cleared; any shareable fine-tuning export must include only `allowed` entries.
Note that two theses state "copyright the author / all rights reserved" with an
open-access deposit; they were tagged `allowed` per the owner instruction and
should be re-checked before any public dataset release.

The approved index was rebuilt offline (`prepare-knowledge.py --reuse-research`)
and the CPU embedding index rebuilt afterwards. Study notes pick up the new
windows automatically on the next nightly run (content-hashed keys).
## Linux kernel / virtualization security sources and HTML archive format (2026-10-10)

The research archive gains an eighth role, `linux-kernel-expert` (LABELS/FOCUS in
`scripts/research-archive.py`, `ROLE_QUOTA` phd 5), with 39 owner-approved items:
5 doctoral theses, NIST SP 800-123/125/125A/125B/190, CISA advisories, the
Thunderclap NDSS 2019 paper, Qubes architecture/security docs, kernel.org KVM,
VFIO, IOMMU, Kconfig and self-protection docs, KSPP settings, QEMU and Xen security
policies/XSAs, Ubuntu CVE pages and Arch/Kali/Mint security pages. 21 hosts were added
to `RESEARCH_HOSTS` with institution comments (including academiccommons.columbia.edu,
the Columbia degree-evidence record).

The pipeline was extended minimally for official HTML documentation: optional
`format` (`pdf` default, or `html`), file extension follows the format, the PDF
magic check applies only to `.pdf`, and `prepare-knowledge.py` parses `.html`
with the existing `text/html` extractor. Pinning, vetting and passage filtering
are unchanged.

Rothwell, "Exploitation from malicious PCI Express peripherals" (Cambridge
UCAM-CL-TR-934) is level `phd`. Correction (same day): the PhD is confirmed by the
University of Cambridge record and `degrees` now states that.

Rights: 19 items are `training_use: private-only` (no explicit open licence,
site terms or author copyright), the rest `allowed` (public domain, GPL, CC BY-SA,
GFDL). All 39 were owner-approved for private offline use.
## Second linux-kernel-expert batch, path-prefix allowlist and TXT format (2026-10-10)

30 more owner-approved items: Intel VT-d and AMD IOMMU specifications, 7 Qubes
Security Bulletins (QSB text), Qubes/kernel/Ubuntu/Arch/Kali AppArmor, LSM,
kernel-parameter and security-team documentation, the Arch security tracker, CSI
Linux update guide, Linux Mint's 2016 ISO compromise statement and 4 doctoral
theses (KU Leuven, Luebeck, Maryland, TU Graz). `ROLE_QUOTA` linux-kernel-expert is
now phd 9. 22 of the 30 are `training_use: private-only`.

`raw.githubusercontent.com` is NOT an allowlisted host. `RESEARCH_PATH_PREFIXES` in
`scripts/research_policy.py` accepts only URLs starting exactly with
`https://raw.githubusercontent.com/QubesOS/qubes-secpack/` (case-sensitive, no
query/fragment, no `..`, `%` or backslash); anything else on that host is refused.
`tests/test_research_path_prefix.py` covers accept and reject cases.

`blog.linuxmint.com` is an owner-approved exception (2026-10-10): it is the project's
official incident statement for the 2016 ISO compromise. Other new hosts, each
commented with its institution: cdrdv2-public.intel.com, www.intel.com (Intel spec
landing page), docs.amd.com, csilinux.com, security.archlinux.org,
lirias.kuleuven.be, www.its.uni-luebeck.de, diglib.tugraz.at, www.cs.umd.edu and
drum.lib.umd.edu (Maryland degree record).

`format: txt` is accepted alongside pdf/html: stored byte-exact as `<id>.txt`,
SHA-256 pinned, and indexed as UTF-8 plain text through the existing extractor.
## Peer-reviewed postdoctoral papers (2026-10-10)

15 owner-approved peer-reviewed papers with a postdoctoral author (evidence quoted in
`degree_evidence`) were added as uncounted `references` with `career_stage: postdoc`,
`venue`, `peer_reviewed` and `doi` fields: 6 cryptographer (IACR ToSC/TCHES), 3
quantum-mechanics-professor (Quantum), 1 mathematician (Forum of Mathematics Sigma),
2 psychologist (Judgment and Decision Making; Journal of Economic Psychology via KU
Leuven Lirias), 1 system-administrator and 2 linux-kernel-expert (USENIX Security).
New hosts: tosc.iacr.org, tches.iacr.org, quantum-journal.org, www.cambridge.org,
www.usenix.org. DOI landing URLs were replaced by the publisher article pages, so
doi.org stays off the list; the postdoc-host evidence pages on hexhive.epfl.ch and
www.mpi-inf.mpg.de are kept as text in `degree_evidence`/`host_institution_evidence`
rather than allowlisted (the paper PDF is the vetted evidence URL).
4 of the 15 are `training_use: private-only`.
## Early-career peer-reviewed papers (2026-10-10)

11 owner-approved peer-reviewed papers whose first author is early-career
(`career_stage: early-career`, `phd_year`, `years_since_phd`), as uncounted
`references`: 5 statistician (Project Euclid: EJS, Annals of Statistics, Statistical
Science), 1 linux-kernel-expert (NDSS 2025), 2 system-administrator (USENIX Security
2017; TU Delft repository), 2 psychologist and 1 it-larp-coach (USENIX Security 2020,
SOUPS 2022). Three were written in the author's final PhD year (Votipka x2, Kaur 2022);
the owner approved them explicitly. New hosts: projecteuclid.org and
repository.tudelft.nl (www.usenix.org and www.ndss-symposium.org were already listed).
PhD evidence (faculty pages, Math Genealogy, university records) is quoted as text in
`degree_evidence`; those personal/faculty hosts are not allowlisted, and the vetted
evidence URL is the publisher PDF. 8 of the 11 are `training_use: private-only`.
## Early-career papers, second set (2026-10-10)

7 more owner-approved early-career peer-reviewed papers (uncounted `references`):
3 psychologist (Judgment and Decision Making via Cambridge; Computers & Security via the
University of Bath repository) and 4 mathematician (Electronic Journal of Linear
Algebra; one via the CWI repository). New hosts: journals.uwyo.edu, ir.cwi.nl,
purehost.bath.ac.uk. DOI landing URLs replaced by the publisher/repository URL.
ec4-mat-01 and ec4-mat-03 use PDF font encodings that standard text extraction cannot
decode; whatever text extracts is indexed (possibly little or metadata-only) and a
math-aware extraction upgrade is being evaluated separately. 4 of the 7 are
`training_use: private-only`.


## Owner-controlled teaching adaptation (2026-10-10)

The owner requested the first build of versioned teaching profiles and an
experiment journal. Use browser-local storage matching companion memory, scoped
to exact persona + skill. Owner-selected enum settings guide pedagogy at user
level; journal prose is never an instruction channel. The model can suggest
experiments in chat but cannot persist, approve or promote its own changes.
Three completed replies bound each trial; then the accepted style resumes pending
owner review. Acceptance and restoration append versions with explicit reasons.
This supports deliberate teaching-style evolution; it is not model-weight
training, mastery certification, or automatic learning-outcome measurement.
No new dependencies, downloads, source allowlist changes, permissions, model/voice
changes or production activation are included. Existing uncommitted changes stay.
See TEACHING.md for limits, storage/export behavior and validation scope.


## Deferred capability comparisons (2026-10-10)

The owner requested capability trials but explicitly deferred live trials until
nightly notes for the current sources are finished. Added an owner-only
standard-library comparison CLI, an authored eight-case linear-algebra bank
(four practice/four held-out), profile selection from browser exports, resumable
private response artifacts, manual 0-2 rubric scoring and paired summaries.
Offline prepare leaves state deferred and performs no inference. Future live runs
require explicit notes-finished/bank-reviewed attestations, daytime Eastern, idle
note task/processes, and a hash-verified prepared release through sealed MCP.
This is cooperative scheduling, not an exclusive GPU lock or automatic proof of
corpus completion. No scheduled run, activation, notes interruption, download,
automatic grading or profile promotion. See CAPABILITY_TRIALS.md.

## Private inference broker (2026-10-11)

The owner requested a broker to strengthen LLM isolation. Move the trusted
agent into its own network-disabled namespace and retain Ollama in its existing
network-disabled pod. A minimal stdlib broker in that model pod exposes only a
private UID1000 Unix socket mounted read-only by the agent. This avoids a new
host port and makes raw model TCP unavailable from the agent. The broker has no
GPU, model files, corpus, quarantine, owner credentials or container socket.

Pin the current model, 131072 context, GPU99 and non-thinking behavior; permit
bounded text chat, optional JSON format, streaming and filtered model status.
Reject administration, arbitrary destinations, tools, images and unexpected
options. Keep a 6000-token output ceiling for existing nightly notes. Explicit
host development remains outside this boundary; isolated failure never falls
back to host inference. Preserve model/voice containers and resume the nightly
writer against the new agent at cutover. Retain pinned rollback, while stopping
old raw-access agents after activation. Rollback to an older release restores
its weaker boundary. This limits API reachability, not prompt semantics or DLP
correctness. See INFERENCE_BROKER.md for limits and verification evidence.

## Study-notes stuck windows, transport diagnostics and overlap dedupe (2026-10-15)

Owner-approved fixes to `scripts/study-notes.py` (continuous loop, retries,
inference budget and 6000-token ceiling unchanged):

- Truncation: counts of `done_reason=length` per window are persisted in a new
  `truncations` table in `notes.build.sqlite`. After 3 truncations a window is
  split near the middle (paragraph, then sentence, then whitespace boundary)
  into resumable units `<key>:h1`/`<key>:h2`. A half that also truncates 3 times
  is marked done with 0 notes and reason `skipped: persistent truncation`
  (logged). When both halves are done the parent key is marked done, so
  `status.windows_pending` (the auto-publish gate) counts it as complete; status
  also reports `units_skipped`. Notes from halves are stored under the parent key.
- Diagnostics: on LARP-NOTES-TRANSPORT / worker errors, `scripts/notes_diagnostics.py`
  writes a private JSON file under `data/diagnostics/` (exception type/message and
  cause type, worker stderr tail, `podman logs --tail 200 larpus-model`, notes and
  model container State.Status/ExitCode/OOMKilled/RestartCount, nvidia-smi
  memory/utilisation). Secret patterns are redacted; files are capped at 64 KB and
  rotated to the newest 50. Prompts, passages and notes are never captured. The
  main log gets a `diagnostic_file` pointer line.
- Overlap dedupe: chunk overlap (longest suffix/prefix match, 16-400 chars) is
  removed from window text sent to the model. Window boundaries and keys are still
  computed from the raw concatenation, so no completed window is reprocessed.
  Existing stored note contexts were not rewritten (cosmetic; avoided risk to the
  live build DB); new notes get deduplicated contexts.

## Owner-approved one-time exception: hosted Codex comparison (2026-10-15)

Owner-approved one-time exception (2026-10-15): up to 833 library passages plus
provenance were sent to OpenAI-hosted Codex (gpt-6.1-sol, tools/web/MCP disabled)
solely to compare against LARPUS-generated study notes. Not to be repeated without
a new owner decision; no runtime cloud path exists.

The owner-side runner (`data/codex-full-notes.py`, private) was stopped by its
`STOP` marker at 21:40 Eastern on October 15 with 652 complete, 181 manually
approved, 3 failed and 2 bibliography-only windows out of 13,737. Private logs show
twelve worker processes launched at 21:28 Eastern, more than the three-worker
extension described in the comparison doc. Results never write the Qwen notes
database or approved index. The runner pins the pre-2026-10-15 `study-notes.py`
hash and refuses to resume against the current validator. See
[Codex notes comparison](CODEX_NOTES_COMPARISON.md).

## Host-side owner-run fetches (2026-10-16)

These were deliberate owner-run downloads on the Windows host, not new runtime
network paths. The deployed station keeps no internet, cloud fallback or telemetry.

- Model weights: Larpus 3.8 27B Q4 (`unsloth/Qwen3.8-27B-GGUF`, `UD-Q4_K_M`,
  revision `4ca720788d1e01f1bff70c033e0d0028fd02e502`) downloaded from Hugging
  Face on October 16, 23:08-23:23 Eastern. Size (16,464,440,224 bytes) and SHA-256
  `322e194f…3482` were verified before use. Weights stay in ignored `data/`.
- Web sources: eight IT / Cyber coach sources plus AI product pricing/model pages
  were fetched with `scripts/prepare-knowledge.py` (allowlisted hosts, screened
  and checksum-pinned). See [Cyber AI week](CYBER_AI_WEEK_2026_10_12.md).

## Optional study-note screening exclusion (2026-10-18)

Recorded from [evidence rejection fix](EVIDENCE_REJECTION_FIX.md) (2026-10-16). A derived
study note that fails a *completed* screen is excluded with diagnostic
`LARP-EVIDENCE-NOTE-EXCLUDED` instead of failing the whole retrieval. Scanner
unavailability or incomplete scans still fail closed. Originals use exact
owner-reviewed reference hashes (`config/reference-reviews.json`, see
[reference review](REFERENCE_HUMAN_REVIEW.md)). Retrieved items carry
compact offline freshness signals ([source freshness](SOURCE_FRESHNESS.md)).
These signals annotate; they do not certify accuracy.

## Voice: empty synthesis chunks and replay admission (2026-10-18)

Recorded from [empty chunk fix](VOICE_EMPTY_CHUNK_FIX.md) and
[replay admission fix](REPLAY_ADMISSION_FIX.md) (2026-10-16). Punctuation-only
cleaned fragments yield a valid silent chunk rather than a worker error. HUD
synthesis is serialized, so replay waits for unfinished synthesis and superseded
replays never reach the worker.

## Chat latency and CPU tuning (2026-10-18)

Recorded from [chat latency](CHAT_LATENCY.md) (2026-10-16), [CPU tuning](CPU_TUNING.md)
(2026-10-17) and [CPU follow-up](CPU_TUNING_FOLLOWUP_2026_10_18.md). Successful
replies carry an additive numeric `timing_ms`, with no prompt or evidence text. Station
OCI inspection is parallelised. The owner approved a scoped WSL change to
`processors=20`, keeping 48 GB memory. That restart was an interruption of about
140 s, not zero downtime. Unmeasured latency gains are not claimed.

## Station-wide local model selection: Larpus 3.5 / 3.8 (2026-10-18)

Recorded from [model switching](MODEL_SWITCHING.md) (2026-10-17). A fixed allowlist
of two pinned identities (`config/model-selection.json`) can be switched station-wide
from the HUD, behind auth and Origin checks. The broker reads a read-only selection
mount validated by isolation preflight. Switching blocks new inference and restores
the prior model on failure. No HUD/MCP download or arbitrary tag is accepted.
Derived notes now record their producing model (`note_producers`). Activation
refuses a stale prepared selection.

## Reliability follow-ups (2026-10-18)

Recorded from [project review](PROJECT_REVIEW_2026_10_17.md) and
[reliability](RELIABILITY_2026_10_17.md) (2026-10-17). On 401, the HUD keeps the
conversation and shows in-page sign-in, and never resends automatically. UI suites
are listed once in `scripts/ui_checks.py` for CI and release preparation. The
study-notes worker transport moved to `scripts/notes_transport.py`, unchanged in
behaviour, and still writes `data/diagnostics/` files.

## Performance suite and baseline (2026-10-18)

Recorded from [performance suite](PERFORMANCE_SUITE.md) and
[baseline](PERFORMANCE_BASELINE_2026_10_17.md). The fixed local API workload
(`evals/performance.json`) gave a first baseline: 24/24 requests, median first
checked text 6.726 s, median completion 9.064 s on Larpus 3.8. This is a
baseline, not a claimed improvement.

## Assembly retrieval scoring (2026-10-18)

Recorded from [native retrieval spike](NATIVE_RETRIEVAL_SPIKE_2026_10_17.md),
[native assembly experiment](NATIVE_ASSEMBLY_EXPERIMENT_2026_10_18.md) and
[assembly pipeline](ASSEMBLY_PIPELINE.md). An optional Linux x86-64 AVX2/FMA/F16C scorer
(`runtime/native/score_half.S`) is the startup default, with a HUD switch and
automatic fallback to NumPy. The measured gain is about 1 ms of scoring time;
no overall chat-latency gain is claimed. The compiled `runtime/native/liblarpus_score.so`
is **not committed** (gitignored). Build it on the owner side with
`python scripts/build-assembly.py`, which uses the pinned Linux Zig 0.17.0:
`zig cc -target x86_64-linux-gnu -shared -nostdlib -O3
-Wl,--build-id=none,-z,now,-z,relro,-z,noexecstack score_half.S -o liblarpus_score.so`.
`runtime/native/manifest.json` pins the artifact's SHA-256/size, and a mismatch or
missing artifact falls back to NumPy. The owner PC must keep its local copy, because
releases stage `runtime/` from the checkout.

## Conversation progress and persona tone (2026-10-18)

Recorded from [conversation progress](CONVERSATION_PROGRESS_2026_10_18.md) and
[precision personas](PRECISION_PERSONAS.md). Shared guidance puts the latest
update first, stops recycling earlier replies or advice that was ruled out, and drops
jokes and psychological labels around feelings. All twelve personas make humour
optional. Approved chat templates get `repeat_last_n=4096` and `repeat_penalty=1.1`
in the broker. Mathematics/quantum personas state assumptions and verification status.

## Behaviour tuning and teacher-student pilot: planning only (2026-10-18)

[Behavior tuning plan](BEHAVIOR_TUNING_PLAN.md) and
[teacher-student pilot](TEACHER_STUDENT_PILOT.md) are proposals. No training has
started. Any further exchange with a hosted teacher model needs its own owner
decision, like the 2026-10-15 exception above.

## Windows-only owner-subprocess test is skipped elsewhere (2026-10-18)

`test_owner_subprocess_preserves_numeric_failure_without_output` exercises
`runtime.model_backend.Backend.call`, whose `runtime.isolation.wsl_command`
deliberately refuses to build a command when `os.name!='nt'`. The test now uses
`skipUnless(os.name=='nt')`, so Linux CI no longer errors on it. It still runs on Windows
(owner PC and the `windows-2025` runner), where it already passed. It needs no `wsl.exe`
because `subprocess.run` is mocked, so there is no `which('wsl')` check. Other tests in
the file keep running on all platforms. The production guard is unchanged.

## Windows CI: quarantine ACL helper pre-applied, with a bounded CI-only timeout (2026-10-18)

On `windows-2025` runners, `test_mcp` real_child_chat returned 503. The DLP gate's
`protect-quarantine.ps1` call timed out (`TimeoutExpired`, 10 s) inside the
console-less MCP child, and the gate correctly withheld the output. The owner approved
two CI-only mitigations:

- The Windows job runs the same helper twice on a stable `$RUNNER_TEMP\larpus-quarantine`
  before the tests. This confirms the helper is idempotent and warms Windows
  PowerShell/.NET. `runtime.dlp` uses that directory (`LARPUS_CI_QUARANTINE_DIR`, which
  must be absolute) only when `GITHUB_ACTIONS=true`. The helper still runs on every
  gate call; nothing is skipped.
- `LARPUS_CI_QUARANTINE_TIMEOUT` can raise the helper timeout only on GitHub Actions,
  and only to between 10 and 60 seconds. Values outside that range or malformed raise,
  so the gate returns 503 (fail closed). Without `GITHUB_ACTIONS=true` both variables
  are ignored. Production keeps `data/quarantine` and the 10 s default.

The MCP child's environment allowlist forwards only these three named variables when
they are set. Tests cover the unchanged default, the cap, invalid values, the fail-closed
gate and the narrow forwarding (`tests/test_dlp_ci_overrides.py`).

## Quarantine ACL helper uses no cmdlets; PowerShell gets no MCP stdin (2026-10-18)

Root cause of the slow `protect-quarantine.ps1` call on `windows-2025`, measured with a
temporary, reverted CI diagnostic that launched the helper from a child process with
piped stdin:

| Launch condition | Time |
|---|---|
| Runner's full environment, or allowlist plus the runner's `PSModulePath` | 0.25–0.4 s |
| MCP child allowlist (no `PSModulePath`) | 24–30 s, once >60 s |
| Allowlist plus inbox-only `PSModulePath` (the Oct 12 attempt) | 19–37 s |
| Allowlist plus each of `LOCALAPPDATA`, `APPDATA`, `ProgramFiles`, `PATHEXT`, … | ~24 s |
| Allowlist with `stdin=DEVNULL` or `CREATE_NO_WINDOW` | ~24 s |

So the problem was neither console allocation nor inherited stdin. It was Windows
PowerShell 5.1 module discovery. The script's one cmdlet, `Get-Item`, makes 5.1 resolve
the command through PSModulePath module analysis. This is slow on hosts with many
installed modules (the runner has Az and SQL Server modules) when the MCP child's
allowlisted environment does not carry the PSModulePath the analysis cache was built for.

Why the Oct 12 attempt (`e22523d`, merged via `d4584e3`, reverted by `a99bee0`) failed:

- It added `CREATE_NO_WINDOW`, `-ExecutionPolicy Bypass` and a 30 s timeout, and pinned
  `PSModulePath` to the inbox module directory.
- On a cold runner the inbox-only path is still slow (measured above). The HUD request
  in `test_mcp` real_child_chat then exceeded its 10 s client timeout (run 38265577136:
  `TimeoutError`, 162 s test time).
- It was reverted because it did not fix the problem. Nothing else broke.

This fix:

- `protect-quarantine.ps1` now uses .NET only: `[IO.DirectoryInfo]` replaces `Get-Item`,
  and a missing target throws. No cmdlet is resolved, so no module discovery runs
  whatever the environment.
- The ACL semantics are unchanged:
  - reparse points are rejected;
  - inheritance is removed (`SetAccessRuleProtection($true,$false)`);
  - every rule is removed;
  - FullControl CI/OI Allow is granted to the current user and SYSTEM only;
  - a readback is verified.
- `runtime.dlp` also passes `stdin=subprocess.DEVNULL`, so PowerShell can never read the
  MCP child's JSON-RPC stdin. Flags, timeout and environment are otherwise unchanged:
  - no `CREATE_NO_WINDOW`;
  - no `-ExecutionPolicy` change;
  - no PSModulePath forwarding.

  PSModulePath is deliberately not forwarded: a pwsh 7 parent would prepend 7.x module
  paths, which broke 5.1 before (see the `Get-Acl` note above).
- Tests in `tests/test_quarantine_acl.py`:
  - the exact command and subprocess arguments;
  - the script contains no cmdlets;
  - on Windows only: running the helper with the MCP child's own environment, the
    production 10 s timeout and an advapi32 ACL readback asserts that the DACL is
    protected, holds only the user SID and S-1-5-18 with FullControl OI|CI and no
    inherited ACEs, and is the same after a second run;
  - a missing target and a junction both fail closed.

Follow-up: the CI-only `LARPUS_CI_QUARANTINE_TIMEOUT` override from the earlier entry is
removed. With this fix the helper finishes in well under a second inside the MCP child,
so the fixed 10 s timeout applies everywhere and the variable is neither honoured nor
forwarded. The Windows pre-apply step and `LARPUS_CI_QUARANTINE_DIR` stay. They are a
cheap smoke test of the helper in the runner's own shell, and they still apply only when
`GITHUB_ACTIONS=true`.

## Phone access through self-hosted Headscale (2026-10-15)

The owner decided to reach LARPUS from his Google Pixel through a self-hosted
Headscale control server and the stock open-source Tailscale Android client.
No cloud anywhere: no Tailscale SaaS, no Tailscale-hosted DERP (embedded DERP
enabled, default DERP map stripped), no third-party IdP and no cloud DNS. Optional
self-hosted OIDC may add a sign-in layer. Authelia is recommended over Authentik
for its smaller footprint. LARPUS's existing password auth remains required.

Rationale: WireGuard end-to-end encryption, with control and relay on owner
hardware, keeps the local-first, single-owner, no-account principle. The gateway
is never exposed to WAN, and only Headscale's control/DERP ports would be reachable.
Headscale runs in its own rootless Podman pod, separate from the offline larpus
pod. This supersedes the Tailscale SaaS route in TAILSCALE_DEMO.md for ongoing
access.

Constraint: no port forwarding on the home router of any kind (no 443, no 3478,
no UPnP), and no inbound IPv6 pinholes. The home PC makes outbound connections only;
LAN.md's no-forwarding rule stands unchanged. Reachability is therefore either
LAN-only (recommended: zero external infrastructure) or Headscale with embedded DERP on an
off-site owner-controlled host. A rented VPS would be third-party infrastructure,
mitigated by end-to-end WireGuard (the relay sees only ciphertext), disk encryption
and no LARPUS data there. Design only: nothing is deployed. Reachability, OIDC, WSL networking and
Android CA trust remain owner decisions or open questions. See MOBILE-ACCESS.md.
The design follows zero-trust tenets (NIST SP 800-207): no implicit trust from tailnet
membership, a default-deny Headscale policy allowing only the tagged Pixel to reach the gateway port
(no routes, exit node or SSH), single-use pre-auth keys, expiring and revocable node keys,
per-request gateway authentication and local-only logs. Device posture on stock Android
remains an acknowledged gap.

Hardening profile (proposal, same date; the owner asked for "extremely secure"): add MFA at
the gateway on top of the password, with WebAuthn preferred. This means a hardware FIDO2 key, or another device-bound
credential, rejecting cloud-synced passkeys. TOTP is the fallback, with hashed one-time recovery codes,
local-only enrollment, step-up for sensitive actions and a lockout that never blocks the local console.
Default-deny allowlists for the Pixel's node identity apply at the Headscale, host-firewall and gateway layers,
and the LAN path is rejected for mobile. Local exponential bans and separate login, MFA and chat
rate buckets keyed by session and node identity, rather than by the forwarder's single IP. TLS 1.3
only, HSTS, `__Host-` cookies, mandatory Origin plus a CSRF token, and a stricter CSP. A local
audit log, Windows toast alerts and a remote kill switch that can only be re-opened locally. No cloud MFA push, SMS
or hosted threat feeds. WebAuthn requires a stable hostname and phone-trusted TLS, so it waits
on the CA questions. Implemented later as phased code PRs H1-H6, each needing approval.


## Remote access through Tailscale SaaS with Tailnet Lock (2026-10-15, 11:54 PM ET)

The owner replaced the Headscale design with the Tailscale coordination service plus
Tailnet Lock. This is an **explicit, scoped owner exception** to the no-cloud principle. It covers
only the coordination plane and Tailscale DERP relays for remote access (plus the SSO login
Tailscale requires). No inference, data or telemetry goes to the cloud: client logging is opted
out with `TS_NO_LOGS_NO_SUPPORT` where supported, and the offline larpus pod stays network-less.

Rationale: home port forwarding is prohibited, no off-site owner hardware is available, and
the Raspberry Pi 5 at home sits behind the same router, so it cannot provide reachability. Tailnet
Lock keeps trust over which nodes may join on owner devices: the PC and the Pi 5 as signers, with
disablement secrets stored offline. It does not hide metadata, guarantee availability or sign the
policy, so the Pixel-only Windows Firewall rule, gateway allowlist, password and MFA remain
independent of Tailscale. All zero-trust and hardening controls stay unchanged. The PC uses the official Windows
client so the gateway can bind only to its tailnet IP. Self-hosted Headscale remains the documented
alternative and exit path.

Identity provider (owner decision, same night, superseding a brief self-hosted OIDC idea): **Google**,
with a dedicated Google account used only for this tailnet. It has two hardware FIDO2 security keys (primary and backup),
Google's Advanced Protection Program (its "two security keys" configuration), and no SMS or phone recovery.
Rationale: Google's account-attack detection and patching beat a self-maintained IdP's upkeep for a
single owner, and **Tailnet Lock limits trust in both Google and Tailscale**: neither can add a node
without a PC or Pi signature. Self-hosted Authelia through Tailscale custom OIDC is only a documented alternative.
Tailscale requires custom-OIDC IdPs to be publicly reachable with a custom-domain WebFinger, which conflicts
with no-port-forwarding unless a second cloud tunnel is accepted. Design only; see MOBILE-ACCESS.md.

## Mobile access decisions approved (2026-10-16, 12:14 AM ET)

The owner approved the recommendations in MOBILE-ACCESS.md:
- D2: a dedicated Google account in Advanced Protection with two FIDO2 keys and no phone recovery.
- D3: the Raspberry Pi 5 as the second Tailnet Lock signer.
- D4: gateway sessions of 15 minutes idle and 4 hours absolute.
- D5: the LAN HTTPS listener turned off, so LARPUS is reachable on localhost and the tailnet only.
- D6: a hardware FIDO2 key as LARPUS's second factor, with TOTP as backup.
- D7: the local CA for the gateway's MagicDNS hostname.
- D8: no disablement secret shared with Tailscale support (approved as part of "all recommendations").

D5 retires LAN clients, the start-lan and LAN firewall scripts, and the Tailscale demo bridge, and requires
rewriting HTTPS.md, AUTH.md and LAN.md in the implementing PR. None of this is implemented yet. The code PRs
H1-H6, the thresholds and the open questions each still need separate approval.
