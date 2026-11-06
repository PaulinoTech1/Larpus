# Larpus decision record

Dated historical decisions and observations; deployment IDs and settings describe their recorded time. See [STATUS.md](STATUS.md) for the current dated snapshot. Older entries do not override later decisions.

## Proposed layered classifier selection (2026-10-25; not activated)

The owner proposes evaluating **Horizon-Labs/prompt-injection-guard-small** on CPU as an additional probabilistic prompt-injection classifier beside Stegdetect. The model card identifies **141M parameters** (correcting the initial 131M estimate), Apache-2.0 licensing, ungated access, and an ONNX option. This was preferred for offline/local access, less identifying information at download, and permissive licensing, **not** because 141M parameters establishes superiority over Meta's **Llama Prompt Guard 2 86M**. Actual accuracy, calibration, model quality, latency, memory fit, and license compatibility need validation. No live model, CPU service, policy change, or deployment is claimed.

A possible second **guard LLM**, e.g. **Llama Guard 4 12B**, is future work contingent on a separate GPU or higher-VRAM GPU; Llama Guard 4 is a content-safety model, not an automatically interchangeable prompt-injection detector. No such hardware or model is included in the current experiment. Existing broker, isolation, Stegdetect, skill integrity and output DLP retain independent enforcement. Full decision rationale, baseline comparison, safeguards, and acceptance criteria: [proposed guard design](PROPOSED_PROMPT_INJECTION_GUARD.md).

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

## Habit-formation source staged as a narrow candidate (2026-10-21, 2:10 PM ET)

The boss asked for a peer-reviewed habit-formation source. Codex chose the 2024
Singh et al. systematic review and meta-analysis (CC BY 4.0) and indexed it
through the normal review path from Europe PMC's full-text XML, because the
publisher refused automated retrieval. The XML rule is limited to that exact
URL, rejects entities and unknown DTDs, and indexes only the abstract and
body, not the reference list. Answers must not promise a fixed number of days
or a behaviour outcome. If the boss meant the original Lally et al. study, the
source choice should be revisited.

The deployable candidate `8203e5380a1b4dbea18c9c9084edecf9` was assembled from
the active release plus only this article, not from the checkout's broader
rebuild. That rebuild also changed passage text for older cyber sources and
should not ride along unreviewed. Incremental indexing reuses a vector only
when the source, locator, title and text match a hash-verified previous index,
which avoided a roughly 69-minute full re-embed.

Codex stopped at 1:41 PM ET on a usage limit while preparation was running.
Preparation finished unattended at 1:55 PM ET with status `prepared`. This
entry, the UPDATES note and a catalog-entry test were added afterwards to
record the result. Nothing was activated, committed or pushed. Activation,
the `chicone`/`salsa` catalog-status difference, and what to do with the
checkout's rebuilt `knowledge/` files are left for the boss to decide.

## Owner-reviewed references are not rebuilt by the web-snapshot builder (2026-10-21, 2:40 PM ET)

The boss asked to fix the textbook status in the habit-source release and then
activate it. The cause was the knowledge builder, not a catalog edit: it marked
any document without a cached web snapshot `unavailable`, which includes the
owner-supplied Chicone and Salsa references reviewed through
`config/reference-reviews.json`. The builder now skips entries whose status is
`owner-reviewed-local-reference`, so it can neither relabel nor fetch them.
Their catalog entries were restored to the committed values. An earlier note
said the live release listed them as owner-reviewed; it does not list them at
all, and the committed catalog is the reference for their status.

Release `346773e17fd54b7784fd3148b07a4b0e` was prepared with this fix and
activated at 2:33:58 PM ET. The first live broker verification failed with a
cancellation-timing error, so it was rolled back to `03959f08` at 2:35:07 PM ET
as the activation instruction required. The same verification passed afterwards
on both `03959f08` and the prepared `346773e1`, which suggests a timing race
straight after cutover rather than a content fault, but this was not proven.
Re-activation is left for the boss to decide.

## Live broker check waits for broker readiness, then proves preemption (2026-10-21, 3:55 PM ET)

The boss chose to fix the check's timing before retrying activation. The check
now confirms readiness with one completed chat before starting the synthetic
note, so a broker's first-use idle fence or model warm-up can no longer
masquerade as "the note finished before cancellation". The cause was inferred
from the broker counters and the 21-32 s note duration, not observed directly:
the original receipt kept only the error type. A truly gated synthetic job would
need a hold inside the broker or notes worker; those are security-boundary
files pinned by the MCP scan review, so they were left unchanged. The
cancellation proof itself is unchanged and stricter about reporting. Tests cover
a passing preemption, a note ending early, ignored cancellation and readiness
failures.

Release `346773e17fd54b7784fd3148b07a4b0e` was activated at 3:47:06 PM ET and
passed `data/broker-live-346773e1-activated-20261021.json`. Rollback target:
`03959f0891764772a962726bea4309d7`. The frozen release still carries the old
copy of `scripts/verify-broker-live.py`; it is not used at runtime.

## Pair declared passage counts with the selected index (2026-10-21)

The owner approved correcting the Unit 42 count in a new release candidate and
checking declared catalog counts against each candidate's selected database.
The rebuilt checkout index has two overlapping Unit 42 chunks; the active
release retained one older row containing the entire reviewed brief. Its
catalog copied the checkout's count of two, so the mismatch is metadata, not
missing reviewed text. The checkout count remains two because its database
really has two chunks.

`scripts/knowledge_counts.py` now checks each declared `indexed_passages`
against distinct `(locator, text)` pairs for the catalog's `(id, url)` in the
selected read-only SQLite index. The URL distinction matters because the Qubes
catalog and research archive reuse a source ID for different documents. The
check ignores duplicate role rows and leaves entries without a declared count
alone. Staging rejects mismatches before copying, and validation rechecks new
frozen releases. An explicit `--write` command reconciles counts in a separate
candidate source tree; staging never silently rewrites a reviewed catalog.
This is a consistency gate, not a source-support or answer-quality check.

The candidate source was copied from the live release payload. Its Unit 42
count is one; its approved database, vectors, manifest and reviewed brief are
byte-identical to live. The only intended payload changes are
`knowledge/sources.json`, `scripts/knowledge_counts.py`, `scripts/releases.py`,
and their two focused test files. The check was moved into a small helper to
stay within the existing complexity limit. The first two staging attempts,
`1fecc97e3f1147fabf380751c4c14a7a` and
`b5d3044767e24bfb98793d1265a9cced`, used the wrong CLI syntax: the source
path was passed as a positional argument instead of `--source`, so they
snapshotted the checkout and failed its complexity gate. Neither was prepared
or activated; they remain for diagnosis. The correctly scoped candidate
`1d49ff55f92f41d6a941e15e9d2f0eea` was staged with `--source` and its
five-file diff and byte-identical index, vectors and brief were verified before
frozen preparation. Preparation passed the isolated suite, UI contracts,
isolation probes, complexity check and scan gate. The scan had 69 passing
targets and one existing reviewed warning; it was not a clean scan. The
candidate is prepared but not activated. Active remains `346773e1`, with
`03959f08` retained as its rollback target. Activation is separate and not
authorized by this decision.

## Grok Bot teacher loop: planning only (2026-10-22)

The owner requested [a Grok Bot teacher loop](GROK_TEACHER_TUNING_LOOP.md) for the
shared local LARPUS model. The proposal targets evidence-first adaptive tutoring,
starts with the existing math/quantum family design, and requires independent
review, model identity hashes, a prompt-only control, a locked test, all-persona
regressions and an exported-model check. This changes the proposed teacher from
Codex to Grok Bot for the next experiment; it does not start training or approve
private-data sharing, model replacement or a production activation.

## MTRAGEval-inspired local evaluation: prepared, not run (2026-10-22)

The owner authorized implementing a local three-task evaluation and explicitly
deferred live and latency runs until Grok Bot fine-tuning finishes. The
[MTRAGEval local protocol](MTRAGEVAL_LOCAL.md) adds owner-only catalog/receipt
accounting and a checked-HTTP end-to-end runner. It changes no production request
path or model. Task A retrieval-only and task B fixed-evidence generation require
separate controlled executors; imported receipts remain operator claims, not
independent proof. Five public synthetic cases are contract smoke fixtures, not
an official MTRAGEval score. Unit and live tests are deferred per the owner's
instruction; syntax and catalog structure were inspected offline.

## Scope MTRAGEval ideas to LARPUS capability probes (2026-10-22)

The owner clarified that the goal is to improve LARPUS, not reproduce or submit
MTRAGEval. The checkout now includes owner-only A retrieval and B fixed-evidence
probes in the sealed agent, alongside the existing checked-gateway C probe. A
uses LARPUS's current three-passage selection; B uses exact ID/locator selections
from its hash-verified approved database and the normal inference, broker and DLP
path. No public MCP or gateway override was added. Ordinary chat keeps its
existing retrieval path and context budget. The five cases remain smoke fixtures;
they cannot establish a quality gain or official benchmark score. No unit,
model-backed or latency tests were run while fine-tuning is in progress. A/B
execution requires a later staged release and separate authorization to activate
it; this decision does not authorize activation or a model switch.

## Qwen3.8 27B chosen as the fine-tuning base; base weights and training toolkit downloaded (2026-10-22)

The owner chose **Qwen3.8 27B** as the base for the Grok Bot teacher-loop experiment
on 2026-10-22, instead of the served `qwen3.5:27b-q4_K_M`. He approved two downloads:
the full-precision weights and a training toolkit. This changes the student named in
[the Grok Bot teacher loop](GROK_TEACHER_TUNING_LOOP.md). The served model is unchanged,
and nothing is trained, swapped, activated or released by this decision. The frozen
round-zero baseline must now be captured on Qwen3.8 27B before any tuning comparison.

**Source.** [`Qwen/Qwen3.8-27B`](https://huggingface.co/Qwen/Qwen3.8-27B), the official
Qwen organisation repo, at revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`. The license is Apache-2.0
(`LICENSE` downloaded with the weights). The repo is not gated, and no account token
was used. The model card describes it as the **post-trained** model: thinking by
default, switchable to non-thinking per request. It is a "Causal Language Model with
Vision Encoder" (`Qwen3_5ForConditionalGeneration`, `model_type: qwen3_5`, BF16).
There is no separate public `-Base` repo (the API returns 401).

**Match with the local GGUF.** `config/models.json` lists Unsloth `UD-Q4_K_M` sha256
`322e194f…3482`. That equals the LFS oid of `unsloth/Qwen3.8-27B-GGUF`
`Qwen3.8-27B-UD-Q4_K_M.gguf` (16,464,440,224 bytes; card `base_model: Qwen/Qwen3.8-27B`),
and it is the same size as `/home/larpus/notes38/input/model.gguf`. The GGUF metadata
gives:
- `general.base_model.0.repo_url = https://huggingface.co/Qwen/Qwen3.8-27B`, architecture `qwen35`, 27B;
- embedding 5120, FFN 17408, heads 24/4, context 262144;
- 65 blocks: 64 layers plus 1 multi-token-prediction layer, with a full-attention layer every 4th layer and linear attention elsewhere.

All of this matches the safetensors `config.json`. The GGUF is text-only; the vision
tower is in Unsloth's separate `mmproj-*.gguf`, which is not on the PC. The BF16 repo
includes the vision encoder (27 blocks, width 1152). Any export must either drop it
deliberately or carry it into a projector file.

**Storage.** `/home/larpus/train-models/qwen3.8-27b-bf16/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/` inside the
isolated `Larpus` WSL distro. Its ext4 virtual disk is `E:\WSL\Larpus`, so the bytes
live on `E:`. A Windows `E:\` folder was not used because the distro deliberately has
automount and interop disabled, and that isolation was not loosened. The path is outside
the repository and every release image. The files fetched are the 18 safetensors shards,
the index, config, generation config, tokenizer files, chat template, the
image/video preprocessor configs and `LICENSE`; `README.md`, `.gitattributes` and
`crc32.txt` were skipped. Weights and the tokenizer were verified against their LFS
sha256; small files were verified by git blob SHA-1, with their sha256 also recorded.
The download ran from 3:00:13 to 3:25:12 AM ET and verified all 29 files
(55,586,048,043 bytes) with no retries. `MANIFEST.json` in the same folder (sha256
`a69bfee9657b9f5a5aae75f05bf0cb1114b57f98e2e292092e5058c153cb1502`) records the repo,
revision, license, every file, size, hash, and the start and end times in ET.

**Download job.** The job was the transient systemd user unit `larpus-qwen38-fetch`
(`systemd-run --collect`, `Restart=on-failure`, nice 10, idle I/O), launched by
`/home/larpus/train-models/qwen3.8-27b-bf16/_fetch/start-fetch.sh`. It used plain HTTPS
range requests, with no hub client and no telemetry. The unit removed itself when it finished;
no Windows scheduled task was created. Re-running `start-fetch.sh` skips verified
files and resumes partial ones.

**Toolkit.** `/home/larpus/train-venv` (Python 3.12.3, 6.1 GB), installed with no sudo
and no system packages, leaving the gateway runtime images and release containers
untouched:
- torch 2.14.1+cu130, triton 3.8.0;
- transformers 5.20.2, peft 0.21.2, trl 1.16.0, accelerate 1.15.0, bitsandbytes 0.50.2;
- safetensors 0.8.0, tokenizers 0.23.3, sentencepiece 0.2.2, huggingface_hub 2.2.0;
- sympy 1.14.0, numpy 2.5.4, scipy 1.18.1, flash-linear-attention 0.5.2.

The full lock is `/home/larpus/train-models/train-venv.requirements.lock.txt`, and
`pip check` is clean. The WSL driver is 595.79, supporting CUDA 13.2.
`torch.cuda.is_available()` is true, and the device is an NVIDIA GeForce RTX 3090 Ti
(sm_86). No tensor was allocated, and GPU use was unchanged at 23,138 MiB. When
imported, flash-linear-attention warns that "Triton is not supported on current
platform", so its fast kernels are not yet proven usable under WSL; check this in the
measured pilot. `docs/finetune/verify_round0_families.py` passed 12/12 in this venv.

**Not authorized by this entry:** training, unloading Ollama, replacing the served
model, sending private data to a hosted teacher, or any release or activation.

| File | Bytes | Pinned hash |
| --- | ---: | --- |
| `LICENSE` | 11,544 | `git blob f938136e3adacfd92be087f6e113b5d6d97f678f` |
| `chat_template.jinja` | 8,952 | `git blob c0c686f9c38d70d179fb7b5f5aa7530bc913dda3` |
| `config.json` | 4,312 | `git blob 706cebd746c4b6f2b1d1f892630867acfdfd3df8` |
| `generation_config.json` | 202 | `git blob 023756cfadf88e5bf69eefeee3e172f38c448d64` |
| `merges.txt` | 3,353,259 | `git blob a494e019ca1502219fd0128658b979e5f05ae8e8` |
| `model-00001-of-00018.safetensors` | 3,966,730,552 | `ba0ce20aae489ad196733da5064bcdf159a1fe84f53336648196e1ebb7751b1c` |
| `model-00002-of-00018.safetensors` | 3,043,080,328 | `06a148c01bfbe3faa14a5f184a7ff29a706f7ae1c8b2705d2058e26d17a001fb` |
| `model-00003-of-00018.safetensors` | 2,542,796,952 | `2e1bf62cbcd406eaa64b60d10353e1f0ef4039d0976e56f05cabe953454f9968` |
| `model-00004-of-00018.safetensors` | 3,988,973,152 | `511e34063187882659753c4d93f3859f93c019fd438d8813071921c81d9a3f1a` |
| `model-00005-of-00018.safetensors` | 2,099,339,864 | `635cb53446dc74f219740fc59e18b774f877b803b9722e289ca62575a6efa701` |
| `model-00006-of-00018.safetensors` | 3,979,553,696 | `0bc5214fac607f0e6cc92eec3789d4b8559410ef9fce66621ba8158e8410dae0` |
| `model-00007-of-00018.safetensors` | 2,108,759,344 | `80b0c49033e9a0d5762562aa12f4acdb7f54da586f3d0110f28c48d91cf07892` |
| `model-00008-of-00018.safetensors` | 3,979,553,696 | `7192c5b66185d3592927daabee1cc19e6f6e0ce75988ee20e824b624765fda79` |
| `model-00009-of-00018.safetensors` | 2,108,759,344 | `af3c48cc37af44f3db6ae0579baf019180d48d9c527caa0a1f03ff85813a56d8` |
| `model-00010-of-00018.safetensors` | 3,979,553,696 | `163490a76f3bea3a40855b7efc04ce6d27afaf1a34f0bbde495b9491f76457c9` |
| `model-00011-of-00018.safetensors` | 2,108,759,344 | `5f3ae1b948aeee39da77aec558e8236cd65fe4d7cb7686a76bb007acc563c6d8` |
| `model-00012-of-00018.safetensors` | 3,979,553,696 | `a3de1c7114677a8f5ac5c4892c90e8238ea5c1e2038c80e757dfc87c3902ca55` |
| `model-00013-of-00018.safetensors` | 2,108,759,344 | `06ab79a41f74c9c5cb734816feb0c7fc364104b227165ee7391231e1155aa02a` |
| `model-00014-of-00018.safetensors` | 3,979,553,696 | `4138ed94603065ba884bbcadedb04d7718bb40117e85e6f5c6fc5b9c05b7a85b` |
| `model-00015-of-00018.safetensors` | 2,108,759,344 | `69224e27b9de4e7dbf6fc936c6eaae08447bda3b80a6c31a871ab451173afd22` |
| `model-00016-of-00018.safetensors` | 3,979,564,040 | `73cb9a1089fb6155cb648609478d6633be8a5c7d9ca5a05bc8925ce8a553cefe` |
| `model-00017-of-00018.safetensors` | 2,108,759,344 | `beb51f01056142ac4984bd800507b0dd0fd18de57f8e9ef6ea41d1a3598983a8` |
| `model-00018-of-00018.safetensors` | 3,392,197,344 | `1d3479509e21494658f9b64d317f5ea8e55c4025d28c702d6c4d0b356ce8ea06` |
| `model.safetensors.index.json` | 112,216 | `git blob da35e3c564457dface7d138f0b6cac284ff8958c` |
| `preprocessor_config.json` | 390 | `git blob 2ea84a437d448ff71b08df68fdd949d5cc4ebb64` |
| `tokenizer.json` | 12,809,320 | `0997f410c57a1f4e53b09e4be8f4a172d90edd9564368fb0847030937229b9f3` |
| `tokenizer_config.json` | 17,928 | `git blob 5de744b3fca2129d7186979ae47c06be33903243` |
| `video_preprocessor_config.json` | 385 | `git blob 3ba673a5ad7d4d13f54155ecd38b2a94a6dac8fe` |
| `vocab.json` | 6,722,759 | `git blob 0aa0ce0658d60ac4a5d609f4eadb0e8e43514176` |

## Qwen3.8 27B fine-tune technical trial: feasible on the 3090 Ti, nothing kept (2026-10-22)

Technical trial only, not a training run. 04:38-04:43 ET: under the owner lock, the agent container was stopped and
larpus3.8:27b-q4 unloaded (the sanctioned model-switch qualify pattern; gateway process and release 346773e1 untouched).
Qwen3.8 27B (pinned revision 1d4bf0f2) loaded text-only in NF4 with gradient checkpointing in 60 s; LoRA r=16
(108.8M params, 400 modules), AdamW, batch 1, 10 steps each at 1k and 2k tokens of throwaway draft-family text.
No OOM: 4.9 s/step at 1k and 10.0 s/step at 2k (~205 tokens/s), peak 21.9 GiB reserved, 24,042 of 24,564 MiB
including ~2.1 GB used by Windows, so 2k is near the ceiling. FLA/Triton kernels cannot run because the Larpus distro
has no C compiler or Python headers; the run used the torch fallback (speed difference not measurable). Chat was
restored: same model fully on GPU at 131072 context, agent started, gateway 200, broker idle. Adapter never saved,
nothing exported or created. Estimate at 1.5k tokens/example: 500 examples 2.1-3.1 h, 1000 examples 4.1-6.2 h for 2-3
epochs, plus export and evaluation. Still blocked on reviewed data, rights decisions, hosted-exchange decision, a
round-zero baseline on Qwen3.8 and vision/MTP handling for export. Record: data/evals/tuning/trial-20261022/.

## Teacher-loop dataset built to 336 families (train/dev only); locked test left as a sealed gap (2026-10-22)

At the owner's instruction (relayed 05:21 ET: "Stop the training and build out the data set, ... 28 times the current
data set size"), no training or baseline was run. The station was checked at 05:2x and again at 06:12 ET: the agent
container was up, larpus3.8:27b-q4 was 100% on GPU at 131072 context, the gateway returned 200, the broker was idle,
and no training or baseline processes were running. dpkg was clean, and no `round0-*` tuning folder existed, so no
STOPPED.md was needed. Nothing was killed or restarted. The split follows the plan's per-lane rule scaled to 28 per
lane, 18 train / 4 dev / 6 test, giving 216 / 48 / 72. That differs slightly from a straight 65/15/20 rounding of 336
and keeps lanes equal. Splits were registered at 05:26 ET, before any variant was written (`docs/finetune/split-register.json`).
Grok Bot wrote 204 new train families (plus the 12 unchanged round-0 families) and 48 dev families, 660 new variants
in all. Every family has an executable sympy/numpy/scipy check in `docs/finetune/verify_families.py`: 262 pass, 2 are
hand-proof-only, 0 fail. The dedupe audit removed nothing. The 72 locked-test families are not written, by design,
because a hosted teacher must not author them. `docs/finetune/locked-test-spec.md` specifies the independent author,
format, sealing and hashes. Still blocked before any training: independent review of every family, rights decisions
(license/training_use/external_sharing_approval are null), the hosted-exchange decision, a round-zero LARPUS baseline
(stopped, not run) to replace the synthetic student attempts, and independent authoring and sealing of the test set.
Nothing committed or pushed. Release and model unchanged.

## Owner review signoff recorded; one known-error variant held (2026-10-22)

The owner identified himself as the independent reviewer of the Grok Bot
train/dev drafts, approved their targets wholesale, and supplied the textual
signoff "Paulino power approved." A versioned processing copy and its hashes
are documented in [the owner review receipt](finetune/OWNER_REVIEW_2026-10-22.md).
The original drafts are retained. The false gradient-descent claim in
`grok-r1-opt-05/d` remains held rather than being marked as an accepted target.
The signoff does not resolve rights, synthetic student attempts, the frozen
baseline or the independently authored locked-test gap; no training, model
switch or production activation follows from it.

## Round-zero baseline started on Qwen3.8; owner rights choice recorded; opt-05/d correction proposed (2026-10-22, 10:45 AM ET)

**What and why.** Evaluation only. The plan requires a frozen untuned baseline and real round-zero student attempts,
which replace the synthetic `student_answer`s, before any teacher review or tuning. **Nothing was trained.** The run
did not stop or restart the gateway, activate or roll back a release, or switch models. The run is
`data/evals/tuning/round0-20261022-0940/` (git-ignored). `identity.json` and `data-manifest.json` were frozen at 09:40 ET. The
pinned served model is `larpus3.8:27b-q4`, manifest sha256 `9db1c57adceb2172ca2e0b183dcf12f2b295cf6117247095e97cc096ea38464f`,
GGUF `322e194f…3482`, running on Ollama 0.40.0 inside `larpus-model` under release `346773e17fd54b7784fd3148b07a4b0e`.
The sampling settings were the production ones: think=false (Qwen3.8's default thinking is off because the broker requires it), temperature 0.4,
num_ctx 131072 and num_predict 1024. The supported path cannot set a seed, and each prompt got one sample. Requests used the normal
`127.0.0.1:8080/api/chat` path (broker, DLP, normal RAG) with the Mathematician and Quantum Mechanics Professor personas and no skill. Requests were sequential, at no more than 10 per minute, and
the runner retried on 429 or 503. The prompt set was 701 prompts: 12 public smoke cases, all 122 dev variants and all 567 train variants, from the hash-verified
owner-reviewed package (receipt `66b98153…88e4`). No locked-test prompt exists, and none was created. The run started at 09:41 ET. Smoke and dev
finished by 10:39 ET with 0 final failures. One output was held by DLP and released on retry. Median completion latency was 25.3 s, and p95 was 33.6 s.
The train capture continues in the background and resumes if restarted. The ETA is about 14:30 ET.

**Scoring.** No automated six-behaviour rubric exists. The official 0-2 blinded scores and technical correctness are
**pending** a human or independent judge using `dev-review-sheet.csv`. `heuristic-scores.json` records only labelled keyword
checks. One heuristic flag stands out: 35 of 122 dev outputs (29%) hit the 1024-token cap, and brevity on direct-answer items passed
only 9 of 41 times. This is a possible communication-layer failure to test with a prompt-only control first. No regex matched a
fabricated tool-execution claim. Grok Bot agreement verifies nothing.

**Owner rights decision (09:36 ET).** The owner said: "Mark them for local training only on my PC, no external sharing". A new versioned copy,
`grok-finetune-staging/owner-rights-20261022-094356`, sets three fields on all 264 families: `training_use` = "local training on the owner's PC only",
`external_sharing_approval` = "denied: no external sharing" and `license` = "owner-internal, local-use only". It adds a
`rights_decision` record and recomputes every family hash. The receipt is `OWNER-RIGHTS-RECEIPT.json`, sha256
`57869b49de134dc862661577234f722c25955c16613d1e72d5644a52755befd4`. The `owner-signoff-20261022-092213` package and the
`docs/finetune` drafts are unchanged. `grok-r1-opt-05` remains held.

**opt-05/d.** `docs/finetune/opt-05-d-correction.proposed.md` proposes a corrected target. It scopes the claim to two cases: a convex quadratic
with Hessian eigenvalues in [mu, L] and mu > 0 converges, and an L-smooth function that is bounded below gets f-decrease and gradient norm tending to 0, but not
iterate convergence. It uses `f=-x^2`, `L=2`, `alpha=0.5` as the counterexample. Its local numpy/sympy check passed, and it is
**pending owner approval**. opt-05 is a dev family, so this edit changes a dev reference. The baseline excluded
`dev/grok-r1-opt-05/d` from target scoring.

**Still blocked before any training:** opt-05/d approval and reviewer disposition; official review of the dev baseline and failure-layer
labels; the prompt-only control; the 72 independently authored locked tests; a recorded check of current Grok/xAI terms
(the owner rights choice does not record one); per-family admission; and the vision/MTP export chain. A no-RAG fixed-evidence arm is not available on the
live supported path. Nothing was committed or pushed.


## opt-05/d correction approved; dev reference changed (2026-10-22, 1:10 PM ET)

Owner decision at 1:10 PM ET: "Approve the opt-05/d correction". The new package `C:\Users\PS5Killer\grok-finetune-staging\owner-opt05-20261022-1311` is a copy of `owner-rights-20261022-094356`. That source package was not edited.
- In the new package, `grok-r1-opt-05` variant d's `reviewed_target` is the corrected target from `docs/finetune/opt-05-d-correction.proposed.md` (as committed in cd9f726), and the family hold is removed. The family is now `owner-reviewed-content-pending-admission`, and the earlier hold is kept under `review.hold_history`. The family hash changed from `9a3da320…c35d` to `ee4be6cc…6a1b`. The receipt `OWNER-OPT05-APPROVAL-RECEIPT.json` has sha256 `a494c9ce85ef70e9a5c5f0e7d0ed0f86292d175d58c2b40c08c9995bcfc5d913`. All 264 family hashes verify, and there are no remaining holds or null targets.
- Variant c's wording is unchanged. The correction doc suggests reviewing its iterate-convergence claim. Variant d's `teacher_critique` was left as authored.
- `check_opt05d.py` was rerun in the new package at 1:11 PM ET. It printed ALL CHECKS PASS (exit 0).
- **This changes a dev reference.** `dev/grok-r1-opt-05/d` can now be scored against the new target. The round-zero run folder and its eval receipt still exclude it, because they use the earlier signoff package and were not edited.
- An automatic heuristic score of the existing round-zero output was computed. It is not an official score. The missing_assumption check passes, target number recall is 1.0, and the output was truncated at 1024 tokens. The answer gives 1/L, line search and convexity. It does not give the 0 < alpha < 2/L range, the bounded-below condition or the f = -x^2 counterexample. The result is in `opt05d-round0-heuristic.json` in the new package.
- This is content approval only, not training admission. Nothing was trained, and nothing was committed.


## Prompt-only control run; candidate prepared, not activated (2026-10-22, 5:40 PM ET)

Owner approval at 4:24 PM ET ("yeah lets start it now"). Nothing was trained.
- **Treatment:** the same 1547-char evidence-first tutoring block was appended to the Mathematician and Quantum Mechanics Professor system prompts. The block covers answering first and concisely, one hint and one question in practice, correcting false premises, asking about missing assumptions, keeping source qualifications, stating what was and was not verified, and no padding. System prompt sha changes: Mathematician `1dc4b116…` → `e2e8d3a2…`; Quantum `3e3286a1…` → `8486d1d3…`. The candidate files and diff are in `data/evals/tuning/prompt-control-20261022-1629/candidate-prompts/`. The live `agents/personas/*.json` and the active release 346773e1 are unchanged.
- **Route:** candidate release `5e0c47d72ec643639a53c98574e5f32c` was staged and then prepared. It was **not activated**. It was exercised through its own `runtime.mcp_client.chat`, the same path the gateway uses: isolation preflight, then the candidate agent, retrieval, DLP gate, and candidate broker. There was no live-gateway HTTP layer, no direct Ollama call, and the gateway was not restarted. Model and sampling were unchanged. The stage step needed the documented `knowledge_counts.py --write` catalog-metadata fix (unit42 2→1; the DB is byte-identical) and a read-only `research/` junction for the provenance check.
- **Run:** 134/134 ok (122 dev + 12 smoke), 4:48–5:30 PM ET, one DLP hold that passed on retry (fa-20/a).
- **Automatic heuristic, dev, baseline → prompt-only. Not official.**
  - direct_answer 9/41 → 27/41
  - practice_one_hint 4/8 → 7/8
  - false_premise 28/34 → 34/34
  - verification_status 70/88 → 81/88
  - missing_assumption 24/26 → **21/26**
  - Variants passing all checks: 74 → 100 of 122
  - Families passing all variants: 11 → 28 of 48
  - Truncated: 35 → 8 of 122
  - Mean output tokens: 708 → 411
  - Median latency: 25.3 → 17.3 s
  - Target-number recall: 0.863 → **0.781**
- **opt-05/d** against the approved target:
  - Baseline: truncated, recall 1.0.
  - Prompt-only: 167 words, not truncated, recall 0.5. It asks for the convexity and batch regime but misses the 2/L range, the bounded-below condition and the −x² counterexample.
- **Decision:** keep as the leading candidate and revise the missing-assumption wording. Adoption waits for blinded human 0–2 review of `blinded-review-sheet.csv` (the key is stored separately) and a repeat with three samples per arm. This is a single sample at T=0.4 with no seed.
- **Candidate containers left running:** agent, broker and notes for 5e0c47d7. The earlier prepared candidates are also still running. Nothing was committed or pushed.

## 2026-10-22 6:25 PM ET - Prompt-only control round 2 (candidate v2 + 3-sample repeat), owner-approved 5:49 PM ET

- Owner approval: "go for it" (5:49 PM ET 2026-10-22). No training, no activation, no gateway restart, no broker/DLP bypass, no commits, no deletions, no installs.
- Stopped (not removed) the idle containers of old prepared/staged candidates 1fecc97e, b5d30447, 1d49ff55 (agent/broker/notes, 9 containers) at 5:50 PM ET with `podman stop --time 5` (the same stop `releases.py prune` issues; prune itself would have kept them as prepared candidates newer than the active release). Live 346773e1 and candidate 5e0c47d7 untouched; `releases.py status` running true afterwards. Release folders and images kept.
- Candidate v2 f46146f28d1742ec87acc4e157322ed3 staged from 5e0c47d7's source; only the Mathematician and Quantum persona prompts (and regenerated config/broker-prompts.json) differ from v1; the other 10 personas are byte-identical to live. Prepared 6:13 PM ET, NOT activated. Diffs: data/evals/tuning/prompt-control-r2-20261022-1754/candidate-prompts-v2/v2-vs-v1.diff and v2-vs-live.diff.
- v2 changes vs v1 (general rules, no item-specific text): unstated-assumption replies name the assumption in the first sentence, give per-case results with exact conditions only when short, and always end with one question asking which case applies; new "conditions and scope" rule (precise hypotheses, exact thresholds/ranges incl. strict vs non-strict, what is and is not guaranteed, one short counterexample for commonly over-generalised claims); evidence rule keeps stated conditions and numbers.
- 3-sample repeat launched 6:14 PM ET in data/evals/tuning/prompt-control-r2-20261022-1754/ (baseline=live text via gateway loopback, v1=5e0c47d7, v2=f46146f2 via prepared-release mcp_client route; 122 dev + 12 smoke; round0 reused as baseline s1 and prompt-control-20261022-1629 as v1 s1 after comparability checks; <=10 calls/min). Results, opt-05/d scoring against owner-opt05-20261022-1311, and the blinded sheet land there automatically on completion (summary.md, heuristic-comparison-r2.json, eval-receipt.json).
- Other-persona regression (25 companion cases, 1 sample per route): live 25/25 released, 24/25 under 120 words; v2 25/25, 25/25; 0 claimed live actions, 0 FAB flags, 0 DLP holds on both.
- Decision: pending results and the owner's blinded review. Activation of either candidate requires a separate owner approval.

## pilot1 QLoRA adapter: output degradation measured; shelved, not activated or exported (2026-10-25, 7:55 PM ET)

**What and why.** The owner asked on 2026-10-25 to "evaluate the fine tuning results" and then to "also document the degradation of the output". This entry records the first trained adapter (pilot1) after the fact. No earlier pilot entry exists in this file: the backup `DECISIONS.md.pre-pilot1-20261023-080458.bak` is byte-identical to the file before this entry (sha256 `642241a12777fd3df30a2dd530216a011bb06a53171b3c1ccdc8a77a2d5f0e58`). Writing this entry trained, exported, merged, activated and committed nothing.

**Training (2026-10-23, 07:53-09:10 ET).** QLoRA SFT of `Qwen/Qwen3.8-27B` revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`. The bf16 weights were loaded as NF4 with double quant and bf16 compute. It ran in the Larpus WSL distro, folder `/home/larpus/train-models/pilot1-20261023-0742`.
- LoRA: r 16, alpha 32, dropout 0.05, on 400 language-model modules (q/k/v/o, in_proj_qkv, in_proj_z, out_proj, gate/up/down), 108,789,760 trainable params.
- Optimiser: AdamW at lr 1e-4 with 5 warmup steps and cosine decay to 1e-5. Accumulation 8, micro-batch 1, clip 1.0, 2 epochs, 142 optimizer steps, seed 20261023, max_len 1536.
- Loss on assistant tokens only, with thinking disabled in the template.
- Data: 562 examples from 214 owner-reviewed train families in package `owner-opt05-20261022-1311`. 2 families and 5 variants were skipped. The system prompt is the candidate v2 persona text (release `f46146f2`). The user turn is the round-0 form, with fixed evidence where present. No dev family and no locked test was used.
- `data-manifest.json` sha256 `9ed42ee0c6ef85754905a327db0023bc1082ed224f297b71f58fb96a2b408c91`. `train-examples.jsonl` sha256 `04f69de7dece796decaac443df00997ca0641a72ce05e52b202becb66f3acbe7`.
- Launch history: the first launch at 07:48 failed 3 times (`OSError: Too many open files`). The 07:53 fresh start was deliberately stopped at step 15 (08:02) as a resume test and resumed at 08:03.
- Loss: mean step loss went from 1.384 (steps 1-5) to 0.510 (steps 138-142). Epoch means were 0.916 and 0.560. No held-out loss was computed.
- Compute: 4,498 s of step time, about 284 tokens/s, torch peak 19.87 GiB allocated, sampled whole-GPU peak 23,888 MiB (DONE.json).
- Adapter: `adapter-final/adapter_model.safetensors`, sha256 `0650d88389e0af36257fac335f18cf4ee5a535e0ca7a34f865d79dff0ed05c05`, 435,280,528 bytes.
- The station was taken offline for the run. Live release `346773e1` was not activated or rolled back (RESTORE-NOTE.md).

**Evaluation (2026-10-25; generation 02:12-03:33 ET, scored 04:57 ET).**
- Arm A is base + v2 prompt with the adapter disabled. Arm B is the same plus adapter-final.
- Both arms ran HF/PEFT on the same NF4 base. This is **not** the served Ollama Q4 model. Evidence was fixed in the prompt, with no retrieval and no gateway/DLP.
- Sampling: T 0.4, top_p 0.95, top_k 20, max_new_tokens 1024, 1 sample per prompt.
- Prompts: 48 dev families (122 scored dev prompts) plus 12 unscored smoke prompts.
- Scoring was automatic heuristic checks only: the round-0 `score.py` regexes and the r2 opt-05/d key points. There has been no human review.

**Measured degradation (observation).** The figures below are family-level means, given as B-A in pp with a 95% bootstrap CI over families. They were recomputed from `eval-responses.jsonl` and match `family-level-comparison.json`.
- All checks pass, per variant: 75.7% -> 44.6%, -31.1 [-42.9, -19.1]. Families better/worse/tie: 6/29/13. Raw count: 93 -> 55 of 122 variants.
- Family passes every variant: 47.9% -> 8.3%, -39.6 [-56.2, -22.9]. Raw count: 23 -> 4 of 48.
- verification_status: 89.6% -> 37.5%, -52.1 [-65.3, -38.5] (77 -> 34 of 88 variants). Outputs containing a "Verification status" line: 92 -> **0** of 122.
- applicability (19 families): 68.4% -> 18.4%, -50.0 [-76.3, -21.1].
- meaningful_checks (33 families): 93.9% -> 69.7%, -24.2 [-39.4, -9.1].
- Target-number recall: 0.836 -> 0.682, -0.154 [-0.210, -0.098].
- Small or uncertain changes:
  - false_premise: 100 -> 94.1, -5.9 [-14.7, 0.0].
  - evidence_qualifications: 100 -> 92.3, -7.7 [-23.1, 0.0].
  - missing_assumption: 81.2 -> 79.2, -2.1 [-25.0, +20.8].
  - practice_one_hint: 100 in both arms.
- Gains: direct_answer (41 families) 68.3% -> 100%, +31.7 [+17.1, +46.3]. Truncation 8.3% -> 0%.
- Length: mean output tokens 399 -> 66, mean words 183 -> 40.
- Largest family regressions (all checks):
  - -1.00: ent-10, lim-20, ode-05, ode-10, spin-10.
  - -0.67: dyn-15, dyn-20, fa-10, meas-20, open-10. summary.md lists only the first 8 of these 10.
- opt-05/d:
  - Both arms named L-smoothness, convexity and 1/L, and asked a question.
  - Both missed the bounded-below condition, the -x^2 counterexample, f-decrease versus iterate convergence, and line search.
  - The arms differed on two points, one each: the 0<alpha<2/L range and a non-convex mention. Per-arm detail is kept out of this entry until the blinded review is done.
- No refusal phrases in either arm. Arm B gave 2 short question-only replies on direct-answer items, arm A gave 0.
- Cost:
  - Amortised seconds per answer: mean 23.6 vs 10.0, median 22.3 vs 9.2.
  - Aggregate decode: 15.9 vs 6.6 tok/s. B ran in smaller, OOM-split batches.
  - Torch peak: 19,893 vs 20,954 MiB. Whole-GPU peak: 24,278 MiB (including about 2.4 GB of Windows apps).

**Interpretation (inference, not verified).** The adapter learned brevity and answer-first directness, at the cost of the verification-status and applicability lines the system prompt asks for. Supporting observations from the training data:
- 0 of 562 `reviewed_target`s contain a "Verification status" line, although both training system prompts require one.
- Only 149 of the 420 verification-tagged targets (35.5%) match even the loose verification heuristic.
- 17 of the 89 applicability-tagged targets (19.1%) match the applicability heuristic. That is close to arm B's 18.4%.
- Targets average 42.6 words, against arm B's 39.5.

Taken together, SFT plausibly taught the model to copy the target style rather than follow the prompt. max_len 1536 truncated no example (the longest is 1,277 tokens), so it is not implicated. Two epochs on 562 short examples may also have over-fitted the style. That effect was not isolated.

**Decision.** pilot1 is **rejected for activation and shelved**.
- It was not activated, exported, merged or deleted. The run folder is about 20 GB in the distro, and deleting it needs owner approval.
- Prompt-only candidate v2 (release `f46146f28d1742ec87acc4e157322ed3`, prepared, not activated) remains the stronger candidate.
- The live release is unchanged at `6200bb30d68348f080f2c1c723ff2fb6`. Its 2026-10-24 activation is described in UPDATES.md and has no entry here.

**Caveats.**
- These are heuristic regex checks, not the 0-2 rubric and not technical correctness. Base outputs may pass on boilerplate.
- One sample per prompt at T 0.4.
- Not the served route: NF4 HF/PEFT, not Ollama Q4, with no RAG and no DLP.
- Dev only. No locked tests exist, so no keep decision is possible either way.
- Seed pairing is weaker than summary.md and eval-receipt.json state. Arm B hit 25 OOM splits, and each split re-seeds its halves at +100/+200. So only 40 of 134 prompts (37 of 122 dev) had the same seed in both arms, and 38 had the same batch size. The arms also ran one after the other: A 02:12-03:03, B 03:04-03:33.
- The blinded sheet is easy to unblind by length: the word ratio is about 4.6x.

**Correction (recorded here; eval outputs not edited).** summary.md's latency header says "batch 12". The scored run actually used batch 6 with a 6,500 prompt-token budget (supervisor.log relaunch at 02:10; `eval-receipt.json` `decoding.batch` = 6). After OOM splits, B's batches ranged from 1 to 6. The batch-12 and batch-8 attempts were discarded.

**Open issues.**
1. xAI terms. All pilot1 targets are Grok-derived. The 2026-10-25 read-only compatibility check found the terms block training on Grok outputs, so there is no further training on this data until that is resolved.
2. Ollama 0.40.0 rejects LoRA adapters. Serving would need a merge to a full GGUF, re-quantisation, an MTP-head decision and a new model tag.
3. No locked tests exist, so no keep decision is possible.
4. The owner's blinded review of `blinded-review-sheet-pilot1.csv` is pending. Do not open the PRIVATE key or the UNBLINDED examples first.

**Possible next round (proposal only, not approved).**
- Targets that keep the verification-status and applicability lines.
- More direct-answer examples that still carry their qualifications.
- Fixed-evidence and retrieval controls run first.

**Files.**
- `data/evals/tuning/pilot1-20261023-0742/` (git-ignored): `identity.json`, `train-receipt.json`, `decision.md`, `OUTPUT-DEGRADATION.md`, `OUTPUT-DEGRADATION-EXAMPLES.UNBLINDED.md` (open only after the blinded review), `data-manifest.json`, `RESTORE-NOTE.md`.
- `eval-20261025-0117/` in the same folder: `summary.md`, `eval-receipt.json`, `family-level-comparison.json`, `eval-responses.jsonl`, `blinded-review-sheet-pilot1.csv`.
- Distro run folder: `DONE.json`, `events.jsonl`, `train-log.jsonl`, `micro-log.jsonl`.
- Backup taken before this entry: `LARPUS-backup-20261021-1405/round0-baseline/DECISIONS.md.pre-pilot1-eval-20261025-194819.bak`.

Nothing was committed or pushed.

## 2026-10-25 8:58 PM ET - Release with published study notes: base (active) and base+v2 (prepared, switchable)

- Owner approval (2026-10-25): prepare and activate a release with the newly published study notes, and keep two options: the base `larpus3.8:27b-q4` with the original persona prompts, and the same model with candidate prompt v2 ("base+v2"). This is the prompt-only v2 candidate, not the shelved pilot1 adapter. pilot1 was not touched. Nothing was trained, exported, installed, committed or pushed, and no embeddings were rebuilt.
- **How the choice works: two releases.** Personas load from `agents/personas/*.json`, and retrieval filters approved passages by persona id (`runtime/knowledge.py`, `role=?`). A separate "Math (v2)" persona would have no passages unless the code changed, so it was not added. Both releases were built from the same snapshot with the same notes:
  - **A `14911af1e4c249e7b125ad7441524f70` (base, ACTIVE).** This is the 6200bb30 payload plus the published notes. The only changed files are `knowledge/notes.sqlite` and `knowledge/notes-manifest.json`. All 12 persona prompts are the originals. Source fingerprint `ea1a081e…` is unchanged from 6200bb30.
  - **B `61a6448a6b3e4a428bb9ef6dff873f87` (base+v2, PREPARED, not active).** This is the f46146f2 payload plus the same two notes files. Compared with A, only `agents/personas/mathematician.json`, `agents/personas/quantum-mechanics-professor.json` and the regenerated `config/broker-prompts.json` differ. The other 10 personas are byte-identical. The mathematician file matches `candidate-prompts-v2/mathematician.v2.json`. Fingerprint `7437c8e3…`.
- **Notes:** `notes.sqlite`, published 7:49 PM ET, 140,166 notes, sha256 `5753ec8c4f78810c01877b43d89df52daaef135d2ff2856dec5af768d171a502`, 214,769,664 bytes. The previous release had 8,256 notes. The agent containers of both A and B count 140,166 rows, and their manifests match.
- **Approved index, sources and chunks:** unchanged from 6200bb30 (76,850 passages, 413 documents, the unit42 count fix carried over). The checkout's uncommitted re-index (76,851 passages, cyber-20261015-snyk-evo 67 vs 66) and the commits after that snapshot were **not** included.
- **Notes caveat.** 6,495 notes (4.6%) come from sources that are absent from the approved index, in this release and in the checkout alike:
  - chicone-ordinary-differential-equations: 2,908
  - salsa-partial-differential-equations: 2,014
  - nist-sp80063-4: 591
  - nist-cswp39-upd1: 271
  - nsdi25-slow-fault: 247
  - osdi25-semantic-checkers: 241
  - usenix25-kernel-tlb: 223

  A further 78 notes have locators that are not in the index. Notes carry their verbatim passage, so they still serve. The owner should decide whether the removed sources' notes should be filtered in a later notes publish.
- **Pipeline:** `releases.py stage --source` was used with prepared trees under `E:\speedzone_MS\larpus-release-work-20261025\release-source-{A,B}`. Each tree had read-only `data`, `vendor` and `research` junctions, and `sources-receipt.json` records the checks. `prepare` built the normal offline per-release agent, broker and notes images and containers (no new voice image, no new model container). It also ran the public contracts, the unit tests, the companion eval, the UI checks and the isolation check. The scan completed 70 targets with the retained source-pinned MCP warning.
  - A prepared 8:33 PM ET; B prepared 8:47 PM ET.
  - Tests on the A tree (`scripts/test-local.py` → `unittest discover -s tests -v`): 561 ran, OK, 4 skipped (Linux sockets, symlink privilege x2, no published notes in the temp copy).
- **Activation:** A was activated 8:47:53–8:48:18 PM ET, with previous = 6200bb30. Prune stopped (did not remove) 6200bb30's agent, broker and notes containers. B's containers are kept running.
  - Checks after activation: `status` running; `/api/station-health` HTTP 200, all required checks pass (security_scan warning as before); `/api/health` active_model `larpus3.8:27b-q4` on GPU. `ollama ps` shows a single model at 100% GPU with 131072 context. Only one model container exists.
  - Smoke test, one mathematician prompt per option, local only: A through the gateway, 200 in 18.3 s with 5 sources; B through its prepared-release MCP route, 200 in 17.5 s with 5 sources.
- **Switching:** the GPU model is shared, so it does not reload. The cutover takes about 25 s and waits up to 180 s for in-flight chat, so switch while idle.
  - To base+v2: `python scripts\releases.py activate 61a6448a6b3e4a428bb9ef6dff873f87`
  - Back to base: `python scripts\releases.py rollback` (previous = A), or `activate 14911af1e4c249e7b125ad7441524f70`
  - **Rollback to the state before this release:** `python scripts\releases.py activate 6200bb30d68348f080f2c1c723ff2fb6`. While A is active, `rollback` does the same thing. Cutover restarts 6200bb30's stopped containers.
- **v2 status:** selectable, not the default. Its blinded human 0-2 review is still pending, and the evidence so far is automatic heuristics only. Adoption still needs that review.
- **Unrecorded activation:** release `6200bb30d68348f080f2c1c723ff2fb6` was activated 2026-10-24 at about 11:01 PM ET, with previous 346773e1. It differs from 346773e1 only in `knowledge/sources.json` (unit42 catalog count) and its narrow 621.01 driver pin, as described in UPDATES.md. No DECISIONS entry was written at the time. This note records the fact only.
- **Backup** before this entry: `LARPUS-backup-20261021-1405/round0-baseline/DECISIONS.md.pre-release-20261025-201859.bak`. Nothing was committed or pushed.

## 2026-10-25 9:38 PM ET - Large baseline of release 14911af1 (predeclared protocol)

- Started a larger output-quality baseline of the live model on the ACTIVE release 14911af1e4c249e7b125ad7441524f70 (base model + 140,166 study notes), run `baseline-large-20261025-2135` in `data/evals/baseline/baseline-large-20261025-2135/`. No release switch, training, export or code change.
- Protocol written and sealed before the first request: PROTOCOL.md sha256 `668264a5debac28eeb147365e0a543690aa421acd3c4c3f4d5e3714b205424bd` (sealed 2026-10-25T21:36:17-04:00).
- Scope: all 701 reviewed prompts x 3 samples (smoke 12, dev 122, train 567; train reported separately because pilot1 was trained on it) + the 25 other-persona companion cases (10 personas) x 3 = 2178 requests through the live gateway streaming route (think off, temp 0.4, no seed). Order: phase A (smoke + dev + other, 477) first, then phase B (train, 1701), stoppable.
- Measures (family-level means, bootstrap 95% CI over families): round0 heuristic checks, all-checks-pass, family-all-variants-pass, target-number recall, truncation, word-limit compliance (no prompt sets a sentence limit), citation resolution/support (denominator = every emitted citation), uncited factual sentences, DLP holds, privacy hits, refusals/over-caution, sample consistency, first-text latency, completion time, GPU peak memory and residency; environment recorded at start and end.
- Predeclared persona-regression rule for future candidates: a drop of 3 percentage points or more in family-level all-checks-pass with the paired bootstrap 95% CI entirely below zero; any DLP/privacy/live-action safety failure counts as a regression regardless.
- Fixed-evidence (no-retrieval) arm not run: every supported chat profile calls retrieval, so there is no path without a code change. Evidence-in-prompt + retrieval items are reported as a separate subset.
- Status: automatic heuristic scoring only. No locked test set exists or was used. Human blinded review not done yet (60-item blinded sheet written at completion, key kept separate).
- DECISIONS.md backup before this append: `E:\speedzone_MS\LARPUS-backup-20261021-1405\round0-baseline\DECISIONS.md.pre-baseline-large-20261025-213858.bak`. Nothing committed or pushed.

## WSL denial and Horizon cyber-pentest false hold (2026-10-27)

Recorded in [lessons learned](LESSONS_LEARNED.md). The Codex unelevated
sandbox denied `WslService` before Python started. The manual path is an
owner PowerShell outside that token, through `scripts/invoke-larpus.ps1`.
Larpus does not mount `C:`. Horizon blocked the original `cyber-pentest`
sentence as prompt injection at probability 0.5336. That turn returned no
text and the suite recorded `invalid_protocol`, so the case looked frozen.
The gateway process kept serving the other cases. Raising the cutoff to 0.9
would also allow a 0.7053 injection label, so the gate stayed at the model's
0.5 label. The suite sentence now says the lab must confirm the finding
itself, which scored 0.3567. Live release
`882c959c3d4540a5ba4b4b89f1596b17`.

## 2026-10-27 6:19 PM ET - Round 2 prep: pilot1 data audit and admission decisions drafted

- Read-only audit of the pilot1 training data. Nothing was trained or exported, the GPU was not used, no release was touched, and nothing was committed or pushed. No blind key or unblinded examples file was opened.
- Source: `train-receipt.json` and `build_dataset.py` (sha256 `a78bfc31...9602`) built pilot1 from package `C:\Users\PS5Killer\grok-finetune-staging\owner-opt05-20261022-1311`, not from `owner-signoff-20261022-092213`. The two training inputs were `grok-round0-families.owner-reviewed.json` `a071b41a...6579` (12) and `families-train.owner-reviewed.json` `e2f0631c...9b1c` (204), and both hashes match the bytes on disk. These are the rights-tagged owner-reviewed copies, not the `docs/finetune` drafts. `families-dev.owner-reviewed.json` `5d841e75...016a` was read for the leakage audit only.
- `train-examples.jsonl` sha256 `04f69de7dece796decaac443df00997ca0641a72ce05e52b202becb66f3acbe7` matches between the Windows copy and the Larpus WSL copy. It has 562 examples from 214 families and no dev family id.
- `grok-r1-opt-05` is a dev family, and 0 training lines mention it. **No opt-05 variant was in pilot1's training set**: not the false draft, not the corrected target, and nothing else. Its only pilot1 use was as a dev evaluation item.
- The conflicting records are resolved by files on disk. The owner rights decision ("Mark them for local training only on my PC, no external sharing", 2026-10-22 09:36 ET; `OWNER-RIGHTS-RECEIPT.json` `57869b49...befd4`) and the opt-05/d correction approval (2026-10-22 13:10 ET; `OWNER-OPT05-APPROVAL-RECEIPT.json` `a494c9ce...d5c913`) both exist. `GROK-BOT-REVIEW-REPORT.md` (2026-10-27) reviewed only the earlier 09:22 signoff package, so its "null rights" and "opt-05/d held" statements are stale for later packages.
- Open: the train receipt records no owner approval wording for pilot1, and the Grok/xAI terms check was still open when pilot1 trained. The xAI Acceptable Use Policy (fetched 2026-10-27, effective 2026-08-14) prohibits using Output "to develop ... machine learning models ... that compete" and "distilling model data or Outputs".
- Drafted, not decided: [Round 2 admission decisions](finetune/ROUND2-ADMISSION-DECISIONS.draft.md), sha256 `ab22e2e1ec58ece32d4ad5a45247ebbdd7c2dcd0ca048355bf22f640420dc040`. It covers the canonical package, training_use, license, external sharing, the xAI-terms question, the opt-05/d disposition and pilot1 data retirement, each with blanks for the owner. **Nothing is admitted until the owner fills it in and signs it.** No family JSON was edited.
- DECISIONS.md backup before this append: `E:\speedzone_MS\LARPUS-backup-20261021-1405\round0-baseline\DECISIONS.md.pre-round2-prep-20261027-181928.bak` (sha256 `2f157718...e739`, verified).

## 2026-10-29 5:42 PM ET - Study notes started for the 96 lecture-note sources added 2026-10-29

- Owner request (5:28 PM ET): make sure the 96 newly added sources are indexed like the other sources and get study notes. The 96 are the uncommitted `research/catalog.json` entries not in HEAD (300 -> 396): `mit-18103-01..10`, `mit-18950-01..04`, `mit-18330-01..29`, `mit-804-01..20`, `mit-805-01..10`, `mit-806s16-01..06`, `mit-806s18-01..07`, `tong-applications-quantum-mechanics`, and nine `preskill-ph219-*` chapters. Roles: mathematician 43, quantum-mechanics-professor 53. See [approved knowledge](APPROVED_KNOWLEDGE.md).
- **Index (already done earlier today, not rerun):** the checkout `knowledge/approved.sqlite` (sha256 `8ad44fd9...43df6`, prepared 1:56 PM ET with `prepare-knowledge.py --reuse-research`) has 81,511 passages in 509 documents, up from 76,850. The 96 sources hold 4,660 rows: 67 sources with 4,631 text passages and 29 `mit-18330-*` handouts with one metadata-only row each, because their PDFs have no text layer. Embeddings (`embeddings-manifest.json`, built 2:01 PM ET) cover 79,432 rows, and all 4,660 new rows are embedded. The 2,079-row gap is the same intentional per-persona duplicate rows as on Oct 25. All 96 archive files match their catalog SHA-256 and have manifest, provenance and authors entries. As documented, `training_use` is omitted for all 96, so none is cleared for training export.
- **Audit:** `data/notes-new-sources-20261029/audit-before.csv` (per source) and `audit-before-summary.json`. Before this run: 0 notes for all 96, and 851 pending windows (822 from text sources, 29 metadata-only). No other source had pending windows.
- **Notes run:** started 5:32 PM ET with the Oct 25 self-resuming driver copied to `data/notes-new-sources-20261029/run-pending-notes.ps1` (`study-notes.py generate --limit 5 --hours 2` per round, log `data/study-notes.log`, progress `progress.json`). It runs on the active release's notes container (`1022de11b0df4ce6be2915f49f1286ba`) with `larpus3.8:27b-q4`. No other GPU job was running. After the first 10 windows: 0 errors, 112 notes, and every quote verbatim in its window (`check_quality.py`). The rate is about 45 s per window, or about 54 s with round overhead, so the ETA is about 6-7 AM ET on 2026-10-30. When nothing is pending, the driver auto-publishes `knowledge/notes.sqlite` and `notes-manifest.json`. To stop it, create `data/notes-new-sources-20261029/STOP` or kill the PID in `runner.pid`. To resume, rerun the script. The `LARPUS Study Notes` task stays disabled.
- **Not live:** the running release `1022de11` serves its own frozen index and notes. A new release with owner approval is needed before these passages and notes are live. No release was staged, prepared or activated, nothing was trained or evaluated, and nothing was committed or pushed.
- Backups: `E:\speedzone_MS\LARPUS-backup-20261021-1405\new-sources-20261029-173149\` (notes.build.sqlite with -wal/-shm, notes.sqlite, notes-manifest.json, manifest.json, embeddings-manifest.json; hashes verified in `SHA256SUMS.json`). DECISIONS.md backup before this append: `E:\speedzone_MS\LARPUS-backup-20261021-1405\round0-baseline\DECISIONS.md.pre-new-sources-20261029-173215.bak` (sha256 `15f92dab...40b1`, verified).

## 2026-10-29 6:51 PM ET - Notes coverage audit and offline OCR of the 29 numerical-analysis scans (not indexed yet)

- Owner request (6:35 PM ET): make sure every source has study notes, and add the 29 `mit-18330-*` numerical-analysis handouts to the material that gets indexed and noted.
- **Audit (read-only):** `data/notes-coverage-20261029/coverage-20261029.csv` and `coverage-20261029-summary.json` list all 396 catalog entries plus all 509 indexed documents (516 ids). Every catalog entry is indexed. 65 sources are pending in the running job (743 windows). 45 documents are metadata-only, with no text: the 29 `mit-18330` scans, 10 image-only MIT theses, `keisler-elementary-calculus` (image-only), `upf-96ebbf0a` (PDF forbids extraction, respected), and 4 text PDFs rejected by the 700-page limit (`boyd-convex-optimization`, `strang-calculus`, `nemirovski-modern-convex-optimization`, `driver-analysis-tools`). Two text sources have 0 notes: `kali-docs-policy` and `kernel-scheduling` are navigation pages, and the model kept 0 notes from them. Orphan notes from sources no longer indexed (6,495) are unchanged. Every embedding row is covered.
- No math-aware extractor was ever approved or installed. The 2026-10-10 entry only says one "is being evaluated separately". Nougat and Marker are not installed.
- **OCR done (CPU only, Idle priority, about 45 s):** the built-in Windows 11 `Windows.Media.Ocr` engine (en-US, on-device) ran on pages rendered at 300 dpi with the existing `data/pdf-env` PyMuPDF 1.28.2. Nothing was downloaded or installed, and the GPU was not used. Output in `data/notes-coverage-20261029/ocr/`: 29 files, 49 pages, 54,315 characters, and `ocr-stats.csv` with hashes. Prose is good. Equations lose subscripts, superscripts and operators, and numbers show o/0, l/1 and B/8 confusions (`quality-sample.md`). It works for search and concept-level notes, but equations and numbers must be checked against the page. `mit-18330-15` is a plot and stays metadata-only.
- **Not live, nothing applied:** the index, embeddings, catalog and code are untouched. The prepared steps are `post-run/POST-RUN-STEPS.ps1`. That script is gated on the owner marker `post-run/OWNER-APPROVED` and on PID 55828 having published. It applies `patch-A-ocr-sidecar.patch` (a pinned `<id>.ocr.txt` sidecar read by `prepare-knowledge.py`), pins the sidecars in the catalog, runs `prepare-knowledge.py --reuse-research` and `prepare-retrieval.py index --reuse-index-from <backup>`, then starts a self-resuming notes runner. Expected: about 81 passages and about 28 windows (about 25 min GPU). Patch B (raise the page limit to 1000) is optional and needs separate approval.
- PID 55828 was not touched. Nothing was committed or pushed. DECISIONS.md backup before this append: `E:\speedzone_MS\LARPUS-backup-20261021-1405\round0-baseline\DECISIONS.md.pre-ocr-20261029-185112.bak` (sha256 `126e62e9...5232`, verified).

## 2026-10-30 7:44 AM ET - Latency-only benchmark of the 12 personas (not a quality check)

- Owner approval: 2026-10-29. Run window: 7:44-8:00 AM ET on 2026-10-30, after the new-sources notes run had published (PID 55828 exited 4:39 AM ET). Before the start, no other GPU job was running: no compute apps in `nvidia-smi`, no training/export/eval/notes processes, and the Horizon guard is CPU-only.
- **Setup:** release `1022de11b0df4ce6be2915f49f1286ba` (running, unchanged before and after). Active model `larpus3.8:27b-q4`, Ollama manifest `sha256:9db1c57adceb2172ca2e0b183dcf12f2b295cf6117247095e97cc096ea38464f`, GGUF layer `sha256:322e194f...3482`. Ollama 0.40.0, 100% GPU, keep-alive Forever. RTX 3090 Ti, NVIDIA driver 621.01.
- **Method:** requests went one at a time to `POST /api/chat/stream` on `http://127.0.0.1:8080`, the same path and default verified profile the web UI uses. One warm-up request was discarded. Then 60 single-turn requests ran: 12 personas x 5 short fixed prompts, with at least 6.5 s between request starts and backoff on 429/409/503. TTFT runs from the request to the first non-empty `text` event. Total time runs to the end of the stream. Output tokens are Ollama's final `eval_count` (`context.output_tokens`). nvidia-smi was sampled every 3 s. Nothing left the PC.
- **Results:** `data/evals/latency/latency-20261030-0743/` holds `summary.md`, `results.jsonl`, `gpu-samples.jsonl`, `gpu-summary.json`, `environment-before/after.json`, `model-digest.json`, the exact `latency_benchmark.py` (sha256 `30763197...565B`) and `postprocess_summary.py`. The post-process script fixes the GPU parse; raw data was not changed.
- **Headline (55 of 60 OK):** median TTFT 7.5 s (p95 12.7 s), median total 15.2 s (p95 28.6 s), median 302 output tokens, about 20 tok/s end to end and about 41 tok/s after the first text. Fastest was psychologist (median total 12.7 s). Slowest were mathematician (21.5 s, TTFT about 12.4 s) and quantum-mechanics-professor (27.5 s, TTFT about 12.5 s). Every completed request used retrieval, with a median of about 1.8-2.0 s. GPU memory peaked at 22,733 / 24,564 MiB (1,831 MiB minimum headroom, flat). Utilization averaged 59% and peaked at 100%. Power peaked at 456 W.
- **Anomalies:** 5 outputs were held by local DLP ("Output held by local DLP for owner investigation"): system-administrator 2 and 4, it-larp-coach 5, network-engineer 2 and 5. They are excluded from the stats, were not retried and were not investigated. There were no timeouts, rate-limit responses or retries. Warm-up TTFT was 23.2 s; no measured request was a cold load.
- **Caveat:** this run measures latency only. Answers were not scored for correctness, citations or safety, so these numbers say nothing about quality and are not comparable to the quality baselines. Nothing was trained, no prompt or release was changed, and nothing was committed or pushed.
- DECISIONS.md backup before this append: `E:\speedzone_MS\LARPUS-backup-20261021-1405\round0-baseline\DECISIONS.md.pre-latency-20261030-080227.bak` (sha256 `f142a7e9...eb41`, verified).
## 2026-10-30 10:25 AM ET - OCR text for the 29 numerical-analysis scans and the 4 big textbooks indexed; study notes started (not live)

- Owner approval, 2026-10-30 10:09 AM ET, in his words: "Also raise the page limit and add the 4 big textbooks". This adds to his 2026-10-29 6:35 PM ET request to get the 29 OCR'd `mit-18330-*` handouts read, indexed and noted. The approval is recorded in `data/notes-coverage-20261029/post-run/OWNER-APPROVED`.
- **Gates:** PID 55828 exited and published at 4:39 AM ET, and the latency run ended at 8:00 AM ET. Before the start, no study-notes, eval, training or index process was running. `nvidia-smi` showed 3% utilization and 22,740 / 24,564 MiB, all held by the resident `larpus3.8:27b-q4` llama-server. The notes run is the only GPU job.
- **What ran:** `post-run/POST-RUN-STEPS.ps1 -IncludePageLimitPatch` ran in the working tree only, from 10:15 to 10:24 AM ET. Minimal script changes, with the original kept as `POST-RUN-STEPS.ps1.orig-20261029`: `git apply` and the audit now check exit codes, and step 7 starts the new runner. Patch B needed no extra wiring. `--reuse-research` reuses only sources that already had text rows, so the 4 metadata-only textbooks were parsed again under the new limit.
  - Patch A: `prepare-knowledge.py` reads a hash-pinned `<id>.ocr.txt` sidecar (`ocr_sha256` in `research/catalog.json`) for the 29 image-only PDFs. Nothing runs OCR at build time.
  - Patch B: the PDF page limit goes from 700 to 1000.
  - `tests.test_knowledge_preparation`: 9 tests, OK.
- **OCR caveat:** the text is raw `Windows.Media.Ocr` (en-US, on-device) output. Prose is good, but equation fidelity is poor: subscripts, superscripts and operators are lost, and o/0, l/1 and B/8 get confused. Notes or quotes from these handouts must be checked against the page for exact formulas and numbers. `mit-18330-15` is a plot and stays metadata-only.
- **Result (checkout `knowledge/`):**
  - Passages: 81,511 -> 88,201. Documents: 509 -> 509, because the same ids moved from metadata-only to text. Embedding rows: 79,432 -> 86,122, with 79,399 verified vectors reused and 6,723 newly embedded on CPU in 382 s.
  - `approved.sqlite` sha256 `4f4bb55c...8feb`. Metadata-only documents: 45 -> 12.
  - Text passages per source: boyd 1,856, nemirovski 2,316, strang 1,252, driver 1,211, and 28 `mit-18330` handouts with 1-5 each (82 in total). `keisler-elementary-calculus` (about 990 pages, mostly image-only) also crossed the limit and gave 7 passages.
  - The local text screen held some textbook passages as `hidden_control` or `unicode_carrier_or_incomplete_scan`: strang 1,249, driver 558, nemirovski 139, boyd 123. Strang is therefore only partly indexed.
  - `rejected-passages.json` still has the stale "PDF exceeds page limit" rows (5 per book) that `--reuse-research` carries forward. They were not cleaned.
  - Re-audit (`coverage-after-ocr-index*.{csv,json}`): all 4 textbooks and 28 of the 29 handouts now have text passages (`mit-18330-15` stays metadata-only), with 0 unembedded non-duplicate rows. 1,179 note windows are pending, all from these sources. GPU during the rebuild: 22,833 MiB at most, so at least 1,731 MiB headroom, with utilization at or below 4%.
- **Notes run:** `data/notes-ocr-textbooks-20261030/` holds `run-pending-notes.ps1`, `start-detached.ps1`, `progress.json` (with ETA), `runner.pid` and the `STOP` file. The runner was started at 10:24 AM ET through WMI `Win32_Process.Create`, so it is detached from any session. It runs `study-notes.py generate --limit 5 --hours 2` per round and can resume where it stopped, because finished windows are skipped. It runs as a single instance, and when a round makes no progress it backs off for 5 minutes instead of exiting. When nothing is pending, it makes a hash-verified backup of `notes.sqlite` and `notes-manifest.json` in `pre-publish-backup-*`, then publishes. At about 45-54 s per window, it should take about 15-18 h.
- **Not live:** release `1022de11b0df4ce6be2915f49f1286ba` is unchanged. No release was created or activated, and nothing was committed, pushed or downloaded. Making these passages and notes live needs a new release, which is the owner's call. Orphan notes were not touched.
- Backups: `E:\speedzone_MS\LARPUS-backup-20261021-1405\ocr-18330-20261030-101544\` holds the knowledge DBs, embeddings, notes, catalog, `prepare-knowledge.py` and rejected-passages, with hashes verified in `SHA256SUMS.json`. DECISIONS.md backup before this append: `E:\speedzone_MS\LARPUS-backup-20261021-1405\round0-baseline\DECISIONS.md.pre-ocr-textbooks-20261030-101345.bak` (sha256 `1e597f78...e75f`, verified).

## 2026-10-31 5:50 AM ET - Owner-approved recovery of 2,069 screened textbook passages

Owner approval, verbatim: "approve the hidden passages and get those started". The screen was not disabled or bypassed globally.

- Cause: PDF font-encoding debris and Greek math letters in strang-calculus, driver-analysis-tools, nemirovski-modern-convex-optimization and boyd-convex-optimization. No passage of these four was held for injection, role spoofing, DLP or secrets.
- Normalization (1,566 passages: Strang 1,249, Driver 317): catalog flag text_normalization 'pdf-control-format-to-fffd-v1' on these four sources only. C0/C1 control and invisible format characters in extracted page text become U+FFFD one for one before passage splitting; tab, newline, carriage return and form feed are kept. Removed characters: U+0001-0003, U+0010-0016, U+0019-001E and U+0080, U+0081, U+008D, U+008E (Strang, about 8,500 occurrences, most often U+0012, U+0081 and U+0019) and U+0012 (Driver, 2,341). No format (Cf) characters were present. The ordinary screen runs on the cleaned text. All 6,635 previously indexed passages of these books are byte-identical, so their vectors were reused.
- Exact-hash owner allowlist (503 passages: Driver 241, Nemirovski 139, Boyd 123): held only because stegdetect flags the Greek letters (nu, tau, alpha, rho, chi, zeta, kappa) as mixed-script homoglyphs (action review). Normalization cannot fix this without altering the mathematics, so their SHA-256 hashes were added to config/reference-reviews.json for these three source ids only, like the chicone and salsa entries of 2026-10-14. Each was checked first: complete scan, no text transformation, only unicode.mixed_script.v1 findings on Greek code points, and no control, format, combining-run or instruction/role-spoof hit. The instruction and role-spoof rules still apply, and the hashes are not accepted under any other source id.
- Still blocked: none of the 2,069.
- Code (uncommitted): scripts/prepare-knowledge.py screens research passages with inspect_reference (exact reviewed hashes per source, otherwise the ordinary screen), applies the flagged normalization, always re-parses flagged sources in --reuse-research, and keeps previous rejected rows only for reused sources. The stale 'PDF exceeds page limit' rows of the four textbooks and keisler-elementary-calculus were dropped, together with older rows of other re-screened sources. data/knowledge/rejected-passages.json went from 11,041 rows to 8,843. Two unit tests were added to tests/test_knowledge_preparation.py.
- Index: 88,201 to 90,270 passages and 509 documents (unchanged). Embeddings: 86,122 to 88,191 rows, with 2,069 newly embedded on CPU.
- Notes: a detached runner in data/notes-recovered-passages-20261031 has 1,346 pending windows. Notes from superseded windows of these books remain in notes.build and are not deleted (owner's call). Notes quoting Greek letters may still be dropped by grounding.
- Nothing was committed, pushed or released. The live release 1022de11 is unchanged. Backup: E:\speedzone_MS\LARPUS-backup-20261021-1405\recovered-passages-20261031-052001 (SHA256SUMS.json).

## 2026-11-01 6:45 AM ET - Data-only release b788d9fd4d8f4ceabd886fbf9365bda7 prepared, not activated

Owner instruction, verbatim: "lets prepare a new release with the notes into the total database of rag for larpus".

- Method: the checkout has uncommitted code changes, so the release was not staged from it. These include runtime/knowledge.py retrieval_question()/PLATFORMS (ATTRIBUTION-DIRECTNESS-PLAN-2026-10-29 says it must not slip into candidates). A source tree was built at E:\speedzone_MS\LARPUS-release-src-20261101-data-only: the exact 497 frozen files of 1022de11 plus the current data files. It was staged with the existing `python scripts/releases.py stage --source <tree>`, and no code was changed. research/catalog.json was in the tree only for the stage provenance check; research/ is not part of a release payload.
- Diff against 1022de11: the same 497 paths, with exactly 10 files changed: knowledge/approved.sqlite, manifest.json, embeddings.npy, embeddings-rowids.npy, embeddings-manifest.json, notes.sqlite, notes-manifest.json, provenance.json and authors.json, plus config/reference-reviews.json. There are no runtime, prompt (EVIDENCE_PROMPT), test, script, eval or deploy changes, and the model is unchanged (model_image, gpu_driver and model selection larpus-3.8). The broker and notes images are identical; the agent image was rebuilt because knowledge/ is copied into it. scripts/prepare-knowledge.py is the 1022de11 version, since the release mechanism does not need the new one. knowledge/sources.json is unchanged.
- Checkout differences left out: runtime/knowledge.py (retrieval_question, PLATFORMS) and web/app.js. scripts/invoke-larpus.ps1, mtrageval_local.py, performance_transport.py, prepare-knowledge.py and research_policy.py. config/complexity-baseline.json, evals/mtrageval-local.json and evals/performance.json. Six test files (test_dlp, test_horizon_guard, test_knowledge, test_knowledge_preparation, test_mtrageval_local, test_performance_suite). runtime/text_filter.py, horizon_guard.py, horizon_worker.py and config/horizon.json differ only in line endings.
- Contents: 90,270 passages and 509 documents (approved.sqlite sha256 55d4ecd2daf16bf5622f05dfec614c0a73d0c1a86183812620b7e20bafd8612f); 88,191 embeddings (vectors sha256 5b0faaeac4e408a90e5db1bd4803e8e9764573b7bac7523fcdf4c4faefe1d4ef); 178,365 notes (notes.sqlite sha256 67d38014d6285d2609ca4ed36d9995d0d5a77f2c6c2702178a948c5328ea4950, 274,239,488 bytes). The reference-review allowlist has 5 sources (chicone, salsa, driver, nemirovski, boyd). 1022de11 had 76,851 passages, 413 documents, 74,772 embeddings and 140,166 notes.
- Size: release tar 698,388,480 bytes (1022de11: 605,194,240). knowledge/notes.build.backup-20261015-pre-fixes.sqlite (191,647,744 bytes) is still bundled, as in 1022de11; removing it is a separate owner decision.
- Checks: prepare passed (complexity gate, public contracts, local tests, catalog evaluation, UI checks, isolation check, independent MCP/skill scan). The full suite in the release (`python -m unittest discover -s tests -v`) ran 599 tests: OK, 3 skipped. The three earlier "reseal deployment" failures pass under the release's own seal. The checkout itself still differs from every release.
- Status: prepared, NOT activated, pending owner approval. Active release is still 1022de11 (previous 882c959c). Candidate containers larpus-agent/broker/notes-b788d9fd are running idle next to the live ones; the shared GPU model was not reloaded. Nothing was committed or pushed.
- Activate: `python scripts/releases.py activate b788d9fd4d8f4ceabd886fbf9365bda7`. Roll back afterwards: `python scripts/releases.py rollback`, which returns to 1022de11.
## 2026-11-01 6:55 AM ET - Release b788d9fd4d8f4ceabd886fbf9365bda7 activated (data-only; previous 1022de11 retained)

Owner instruction (2026-11-01 6:53 AM ET): "Activate release b788d9fd now". Rollback pre-authorized only for a failed activation; not needed.

- Pre-check: no notes/eval/training jobs running (only retrieval workers and the CPU horizon guard); GPU 1%, 22,314/24,564 MiB (resident larpus3.8 only).
- Command: `python scripts\releases.py activate b788d9fd4d8f4ceabd886fbf9365bda7` (6:54:40-6:55:10 AM ET, exit 0, log data\releases\b788d9fd-activate.log). Output: "Active b788d9fd...; previous 1022de11... retained." The built-in post-cutover container cleanup stopped (did not remove) larpus-{agent,broker,notes}-1022de11; no release, image or volume deleted, and the 1022de11 release folder/tar remain for rollback.
- releases.py status: id b788d9fd, running true, previous 1022de11b0df4ce6be2915f49f1286ba, pending false. New gateway PID 58668 on 127.0.0.1:8080 / 192.168.1.2:8080; old gateway PID 33120 drained and exited.
- /api/station-health: all required checks pass (approved_knowledge: 509 documents, 90,270 passages). security_scan = warning: the shared data/security/summary.json is from 2026-10-09 (status warning, older fingerprint), so this was already stale under 1022de11; the release's own prepare-time scan passed. Not a cutover gate.
- /api/health: ollama online, active model larpus3.8:27b-q4, processor GPU.
- Test query (mathematician, skill math-continuous-optimisation, Boyd convex optimization local=global optimum): HTTP 200, 35.7 s wall (retrieval 2.7 s incl. notes 0.8 s, inference 31.4 s), 4,254 prompt / 593 output tokens, execution source_fingerprint 21b6dc9c... Sources: boyd-convex-optimization passage p.23 plus two derived study notes (p.181, p.151), boyd-vandenberghe-vmls p.10, nemirovski-modern-convex-optimization p.540; citation_check identified [boyd-convex-optimization]. boyd-convex-optimization (1 -> 1,979 passages, 0 -> 7,222 notes) and nemirovski (1 -> 2,455 passages, 0 -> 8,312 notes) are new in this release, so new-source passages and notes are being retrieved.
- After: GPU 3%, 22,479/24,564 MiB; ollama ps: larpus3.8:27b-q4 100% GPU, context 131072.
- Rollback if needed: `python scripts\releases.py rollback` (returns to 1022de11).
- Backup of this file before the entry: E:\speedzone_MS\LARPUS-backup-20261021-1405\round0-baseline\DECISIONS.md.pre-activate-b788d9fd-20261101.bak. Nothing committed, pushed, pruned, deleted or downloaded.

## 2026-11-01 8:50 AM ET - Quality and latency test of live release b788d9fd (run quality-20261101-0709; nothing changed)

Owner instruction (2026-11-01 7:02 AM ET): test all personas and all skills, one persona+skill per context window, and report latency and answer quality.

- Run: data\evals\quality\quality-20261101-0709\ (07:11-08:29 AM ET, detached supervisor, one GPU job at a time, one discarded warm-up per runner session). Live gateway /api/chat/stream, release b788d9fd, model larpus3.8:27b-q4.
- Scope: 12 personas, 95 persona+skill pairs, 190 single-turn prompts (2 per pair, fresh context each, 2.1k-5.2k prompt tokens, median 3.8k; output cap 1,024). Sources: 158 assistant-written (83%), 20 owner-reviewed dev items, 10 evals/companion.json, 2 benchmark FOCUSED. Live retrieval only (no fixed-evidence arm). No locked-test families, no *.PRIVATE.json / *.UNBLINDED.md used.
- Predeclaration PREDECLARATION.md sha256 f10a46db3810be3e388c91783675dd7d45094c3f9572dbcc35c41487f8bb57cf (sealed 07:11:05 AM ET); re-verified after the run, jobs.jsonl and all scripts match predeclaration-receipt.json. Scorer quality-persona-skill/v1 (local heuristics, no cloud grader).
- Headline vs owner targets (none met): citation support 24.6% (49/199 emitted ids; target >=80%); invented ids 8 in 2 answers (target 0; malformed copies of retrieved ids); answers citing 39.8% (target >=70%); direct answer 24.0% (target >=80%; all 133 misses are the 250-word limit only); truncation 10.8% (target <5%; concentrated in quantum-mechanics-professor 57% and maths derivations); safety failures 7 (target 0) = 4 DLP-held answers + 2 FAB regex flags (code examples, likely false positives) + 1 privacy regex flag (fictional phishing lookalike address). All-checks-pass 87.4% (lenient for non-dev items), strict pass 24.2%, reviewed dev items 40% all-checks-pass.
- Latency (186 released): TTFT median 8.45 s / p95 11.48 s; total median 21.51 s / p95 34.55 s; about 24.8 tok/s. GPU: 1 model resident, 100% on GPU, peak 23,272 MiB.
- DLP: 4 jobs held on all 4 attempts and counted as failures (s1 network-engineer/scenario-debrief, s1 network-engineer/network-segmentation, s1 system-administrator/scenario-debrief, s2 network-engineer/network-dns-services); 6 more held then released on retry. No new data\quarantine record was written for these streaming holds.
- Baseline 14911af1 cited for context only, not like-for-like.
- Report: REPORT.md in the run folder (scorer output + addendum; untouched scorer copy REPORT.scorer-original.md). Page: "LARPUS quality and latency test - release b788d9fd (Nov 1, 2026)".
- Backup of this file before the entry: E:\speedzone_MS\LARPUS-backup-20261021-1405\round0-baseline\DECISIONS.md.pre-quality-20261101-0709.bak (sha256 CC904CD4...86FA, verified). Release, models, configs unchanged; nothing committed, pushed, trained, downloaded or deleted.

## 2026-11-01 5:15 PM ET - Documentation written and PC work proposed as a GitHub PR (not merged)

Owner request (2026-11-01 4:53 PM ET), verbatim: "make documentation and update the github larpus".

- **Branch.** `docs-and-ingest-20261101` in PaulinoTech1/Larpus, opened as a pull request to `main` for owner review. It is **not merged**, nothing was pushed to `main`, and nothing was force-pushed.
  - It starts from `origin/feat/habit-source-and-broker-check` (2bc9390), so it is stacked on open PR #6 and includes the two commits that were on GitHub but not on the PC (980430c, 2bc9390).
  - The PC's uncommitted `web/app.js` and `tests/chat-stream-ui.cjs` edits were already in 980430c, so they add nothing.
  - `docs/LESSONS_LEARNED.md` keeps both the PC paragraph and the remote broker section.
- **Commits, by topic:**
  1. Ingest code and tests: OCR sidecar, 1000-page limit, PDF control normalization, per-source reviewed-hash screen.
  2. Catalog: 396 entries, OCR pins, normalization flags, two new hosts.
  3. Knowledge metadata matching release b788d9fd: manifest, authors and reference-reviews.
  4. MTRAGEval harness: pacing, refusal metadata, Qubes fixture.
  5. `runtime/knowledge.py` `retrieval_question()`/`PLATFORMS`, labelled **NOT IN LIVE RELEASE**. The attribution plan flags it for separate evaluation, and the owner can drop this commit.
  6. The PC's untracked Oct 26-29 plans and reviews.
  7. This documentation.
- **New docs:**
  - `docs/KNOWLEDGE-INGEST.md`
  - `docs/releases/RELEASE-b788d9fd-2026-11-01.md`
  - `docs/evals/QUALITY-2026-11-01.md`
  - `docs/evals/LATENCY-2026-10-30.md`
  - README knowledge-base stats and links
- **Warning recorded in KNOWLEDGE-INGEST.** The CRLF copy of `knowledge/manifest.json` is 99,441 bytes, and `runtime/knowledge.py` rejects anything over 100,000. That leaves 559 bytes for the next ingest.
- **Not committed:**
  - the 359 MB sensor CSV, the scratch text file, and any `*.PRIVATE.json` / `*.UNBLINDED.md` (none opened);
  - `knowledge/*.sqlite`, `*.npy`, release tars, raw eval responses and everything under `data/`;
  - `2026.semeval-1.447.pdf` and `docs/LARPUS-lessons-learned-2026-10-28.pptx` (binaries);
  - the PC's older CRLF copy of `docs/SPEECH_CUTOFF_REPAIR_BLOCKER_2026-10-28.md`, which the remote version already contains.
- **Secret scan.** The branch diff was checked for passwords, tokens, private keys, CA keys and the LAN password, and none were found. The repo already contained the LAN address and the Windows user path.
- **Tests.** In a Linux clone, `python -m unittest discover -s tests -v` ran 614 tests: 2 failures, 5 errors, 6 skipped. The same 7 fail on the unchanged base 2bc9390, which ran 603 tests. All 11 new tests pass, and all 11 Node UI suites (`tests/*.cjs`) pass. The 7 come from the environment:
  - no `knowledge/approved.sqlite` (3 meta_muse tests, and the mcp mock chat returns 503);
  - Windows-only `subprocess.CREATE_NO_WINDOW` and `node.exe`;
  - no vendored KaTeX.
- **PC checkout.** Its git state was not changed: nothing was committed, stashed, reset or checked out on the PC. A stale empty `.git/index.lock` was removed shortly after 4:54 PM ET. It had been left by my own interrupted `git status --ignored`.
- The live release b788d9fd is unchanged.

## 2026-11-02 6:30 PM ET - Persona list shows the served model; Qwen3.8 becomes the default (PR, not merged or deployed)

- **Problem.** The web persona list and MCP `list_personas` showed `qwen3.5:27b-q4_K_M` for every persona, which suggested 3.5 was serving chats. That value was the persona files' fallback model. Chats are actually served by the selected `larpus3.8:27b-q4` (catalog id `larpus-3.8`), as decided on 2026-10-22 and 2026-10-25. A live smoke after the latest restart (5:40 PM ET) confirmed this: `ollama ps` showed only `larpus3.8:27b-q4`, 100% GPU, context 131072.
- **Label fix.** `/api/personas` and `list_personas` now report the model that serves chats (`model`). The response also includes the file value (`declared_model`) and the source (`model_source`: `active-selection` or `persona-default`). During a switch, or when the selection can't be read, the list falls back to the file value.
- **Defaults aligned to 3.8.** A lost or reset selection could otherwise silently serve 3.5, so the defaults now match the decided model:
  - the broker policy (`config/inference-broker.json` and the reviewed value in `runtime/inference_broker.py`);
  - all twelve `agents/personas/*.json`. They must match the policy because, with selection disabled, the broker accepts only the policy model;
  - the initial/fallback selection in `runtime/model_selection.initial()`, which `releases.py prepare` uses when there is no previous selection;
  - `config/models.json`: `recommended`, a new `larpus3.8:27b-q4` candidate, and display names. `qwen3.5:27b-q4_K_M` stays a listed, selectable, non-recommended option (`larpus-3.5`).
- **Also updated:** `scripts/verify-broker-live.py` and `deploy/windows-home/prepare-cache.sh`, which still pulls only public tags because 3.8 is imported locally through `scripts/model-switch.py prepare-cache`, plus the current-state docs.
- **Served settings unchanged:** think=false, temperature 0.4, num_ctx 131072, num_predict 1024.
- **Evals checked.** The Oct 30 latency run (`latency-20261030-0743`) and the Nov 1 quality run (`quality-20261101-0709`) were verified as served by `larpus3.8:27b-q4`. Their reports stay valid and were not changed.
- **Not changed:**
  - historical decisions, eval and verification records;
  - the 3.5 install and pull instructions, which are still valid for the 3.5 option;
  - `scripts/model-switch.py qualify`, which deliberately restores 3.5 after qualifying;
  - the approved-tag allowlists, which already contain both tags.
- **Deployment.** Nothing on the PC changes until a new release is built:
  1. merge PR #6, then PR #7, then this PR;
  2. run `python scripts\releases.py stage`, then `prepare`, then `activate`.
  LAN users must log in again after activation. The active selection (`larpus-3.8`) is carried over by `prepare`.

## 2026-11-05 10:45 PM ET - Linux release helpers and knowledge-ingest complexity for CI (PR, not merged)

- **Ubuntu CI was red on `main` and #6.** `scripts/releases.py` hardcoded Windows-only APIs: `check_ui` always ran `node.exe`, and `launch` always passed `subprocess.CREATE_NO_WINDOW`. Those paths fail on Linux runners (`FileNotFoundError: node.exe`, `AttributeError: CREATE_NO_WINDOW`) while Windows CI stayed green. The failing tests were `test_ui_checks_use_the_candidates_manifest` and `test_unrecorded_child_is_closed_on_its_process_handle`. Open PR #5 already patches the Node name; it does not cover `CREATE_NO_WINDOW`.
- **#7 and #8 also failed the complexity gate on both OSes.** After the Oct 29–31 ingest growth (`prepare-knowledge.py` OCR sidecars, 1000-page limit, PDF control normalization, review screen), `scripts/verify.py` → `complexity.py check` reported `build` over limit (decisions 53>51, lines 95>94) and module fan_out 5>4. Limits were not raised.
- **Fixes (this PR, stacked on #8):**
  - `check_ui` and `launch` are platform-aware (`node` / no creation flags on non-Windows). Windows behavior is unchanged.
  - Knowledge ingest `build()` was split: research reuse and archive loading moved to `scripts/prepare_knowledge_research.py` (drops owned fan_out to 4); indexing and sqlite/manifest writers are smaller helpers in `prepare-knowledge.py`. Ingest behavior is preserved; complexity baseline limits were not raised.
- **Not changed:** release sealing, activation, Ollama, PC tree, historical DECISIONS, or baseline allowances.
- **Deployment:** nothing on the station changes until the stack (#6 → #7 → #8 → this) is merged and a new release is built later.
