# larpus

Owner tooling candidate: [verification, status, encrypted synthetic restores,
quality evidence and timing](docs/OWNER_OPERATIONS.md). Run
`python scripts/verify.py` for the shared offline verification pipeline.
This checkout/worktree is distinct from the active frozen release.

## TL;DR

A local-first home AI station: voice-driven home assistant with an MCP agent pipeline, DLP output filtering, and local inference on commodity GPU hardware. Goal: a private AI assistant that never sends your data to the cloud.

**LARP: Larp, Always Ready Prep.** LARPs all the way down.

A private home AI station and eccentric, Jarvis-inspired LARP companion for
research, study, scenario preparation and professional roleplay. Personas and
skills are configurable. Single box, single owner; no OS action tools.

Inference, retrieval and speech run locally. The deployed agents have no internet
access, cloud fallback, telemetry or external account requirement. Initial setup
and owner-approved reference downloads need internet; GitHub archive preparation
may use the owner's existing credentials, which never enter the agent runtime.

The visual identity is a rotating torus beneath $\iiint_T dV = 2\pi^2 Rr^2$.
Its repeating fill and forming percentage are decorative, not inference progress.
Reduced motion shows a static torus. R = 2 and r = 0.8 give a volume of about 25.266.

## Deployed station

See the dated [operational status](docs/STATUS.md) for the selected release, validation boundaries and later checks.

See the [performance baseline](docs/PERFORMANCE_BASELINE_2026_10_17.md) for measured
response times and quality findings, and the [test-suite guide](docs/PERFORMANCE_SUITE.md) to repeat the measurements.

Vetted references bridge gaps after the model's training period. Refresh priority
depends on the persona: product pricing, security guidance and platform behavior
change faster than foundational mathematics. See the [research refresh policy and
persona priorities](docs/RESEARCH_2025_2026.md). Downloads and prepared queues are
not live knowledge until admitted and integrated. The checkout includes
[offline freshness detection](docs/SOURCE_FRESHNESS.md); age-based review warnings
and scoped lifecycle signals do not certify current accuracy.

Verified against the owner's active frozen release on **2026-10-11**. Counts and
settings below describe that deployment; a fresh clone does not include its
private models, credentials, downloaded corpus or prepared runtime.

| Component | Current deployment |
| --- | --- |
| Host | Windows 11 Home; Ryzen 9 5900X, 64 GB RAM, RTX 3090 Ti with 24 GB VRAM |
| Isolation | Dedicated WSL2 distro, rootless Podman; separate offline agent and model namespaces connected through a private inference broker; separate offline CPU voice container |
| Model | `qwen3.5:27b-q4_K_M`, GPU inference, non-thinking replies |
| Context | **131,072 tokens configured**; 1,024-token normal reply ceiling. The requested 262,144-token target is not the active setting. |
| Personas and skills | 12 personas; 69 locally authored, hash-checked prompt skills |
| Approved library | 404 documents / 76,660 indexed passages; all personas can retrieve across roles |
| Local access | **http://127.0.0.1:8080**, password-free |
| Home LAN access | **https://192.168.1.2:8080**, password, rate limits and subnet checks; local CA trust required |

LAN address and subnet are this owner's deployment settings, not universal defaults.
Ollama listens on `127.0.0.1:11434` **inside the isolated pod**, with no published
inference port. The agent reaches only the [private inference broker](docs/INFERENCE_BROKER.md)
over a Unix socket; raw Ollama TCP and model administration are denied. MCP uses
stdio; neither the broker nor voice adds a host listening port.

The [version2 broker](docs/BROKER_HARDENING.md) separates chat and notes socket
capabilities, pins approved system templates, limits request/output budgets and
cancels background generation for chat with a confirmed runner fence. Cancellation
failure closes inference; it is not a guarantee against prompt injection or all
denial of service. Reproducible local synthetic/live checks distinguish what ran
from what remains unverified. Owner-approved [public-only GitHub CI](docs/CI.md) is separate from the fully local runtime.

Current health reports functional checks passing, with overall status **degraded**
for the security-scan warning. A passing health probe is not a full security audit,
answer-quality certification or proof of physical GPU-memory residency.

## What works

- [Configurable personas](docs/PERSONAS.md) and [local skills](docs/SKILLS.md),
  including 60 role-specific skills, four original shared skills and five
  [Microsoft implementation skills](docs/MICROSOFT_IMPLEMENTATION.md).
  Switching role or skill preserves the conversation; these are prompt
  specializations of the same model, not separately trained experts.
- [Approved local knowledge](docs/APPROVED_KNOWLEDGE.md), with role preferences,
  bounded reference passages and source cards. CPU semantic retrieval and
  reranking supplement keyword search, with keyword fallback if that tier is
  unavailable. Downloaded content remains untrusted reference data.
- [Screened owner GitHub archives](docs/GITHUB_ARCHIVES.md), including the
  owner's 22-repository collection and ownership attribution. Raw mirrors and
  credentials stay outside the agent; only approved text enters its index.
- [Sentence streaming](docs/STREAMING.md), with inspected text displayed and
  queued for CPU speech while GPU generation continues.
- [British English voice](docs/VOICE_INTEGRATION.md): microphone selection,
  push-to-talk, optional hands-free capture, transcript review, playback speed,
  pause/resume and reply replay. Wit comes from persona wording. VoiceStudio's
  ASR adapter and Piper TTS are used; full VoiceStudio, cloning and wake-word
  detection are not deployed.
- [Companion controls](docs/COMPANION.md): optional browser-local saved chats,
  explicit remembered notes and source previews. Local HTTP and LAN HTTPS have
  separate browser storage. Saving is opt-in; no cross-device synchronization.
- Context usage reporting and validated compression/handoff protocol support in
  the active runtime. Summaries are lossy conversation data, never permissions;
  they do not establish reliable recall across a filled context window.

## Start, update and recover

For the **already provisioned** station, run owner commands from this checkout:

```powershell
python scripts/releases.py start
python scripts/releases.py status
```

Production uses the frozen release selected by `data/releases/active.json`, not
this working tree. Editing source does not deploy it. For an application update:

```powershell
python scripts/releases.py stage
python scripts/releases.py prepare ID
# After preparation succeeds:
python scripts/releases.py activate ID
```

Replace `ID` with the staged release ID. Preparation keeps the active gateway,
model and CPU voice available. Activation drains requests and briefly rebinds the
same ports; failed readiness restores the previous release. LAN sessions require
another login after a gateway process change. Use `python scripts/releases.py
rollback` for an explicit return. See [update boundaries](docs/UPDATES.md).

For a fresh installation, use the [Windows Home isolation guide](docs/WINDOWS-HOME-ISOLATION.md)
and [deployment/rebuild guide](docs/DEPLOYMENT.md), including cached dependencies,
images, model files, GPU mounts and verification gates. Set the LAN password
locally with `python -m runtime.auth`; see [authentication](docs/AUTH.md),
[LAN setup](docs/LAN.md) and [CA trust](docs/HTTPS.md). Preserve owner credentials,
TLS material, model caches and quarantine when rebuilding.

## Security boundaries and limits

The [sealed local MCP server](docs/MCP.md) exposes three fixed operations with no
direct-inference fallback. Network isolation comes from the deployed Podman
boundary, not from MCP itself. Code, configurations and model mounts are read-only;
the agent receives no owner home, Windows drives, GitHub credentials or container
socket. The model cannot read the private DLP quarantine.

[Unicode and instruction filters](docs/TEXT_FILTER.md) screen inputs.
[Output DLP](docs/OUTPUT-DLP.md) screens generated output and holds flagged replies
for owner-side investigation outside web access. These defenses can have false
positives and false negatives; they do not guarantee prevention of prompt injection
or sensitive-data disclosure. Keep secrets out of model context.

[Local health monitoring](docs/HEALTH.md) checks runtime boundaries, model/voice
availability, policy probes and exact MCP tool schemas. Local SkillSpector static
scan evidence is checked separately; retained findings remain warnings rather
than being described as a clean security result.

OpenShell remains an unimplemented target layer. The current deployment uses
WSL2/rootless Podman without it. See [architecture](docs/ARCHITECTURE.md) and the
[decision record](docs/DECISIONS.md).

## Research and nightly study notes

Six [research archives](research/CATALOG.md) cover cryptography, IT/cybersecurity,
continuous mathematics, statistics, enterprise systems administration and quantum
physics. The documented archive build contains 150 student PDFs: each role has
10 undergraduate dissertations/capstone reports, eight master's theses and seven
doctoral theses. Eight supplementary cryptography references cover primitives
and implementation constraints. See [verification and rebuild details](docs/RESEARCH_ARCHIVES.md).

Original PDFs and archive packages remain in ignored `data/research/`; they are
not served by the HUD. Git tracks source catalogs and authored briefs, not
downloaded originals, raw repository mirrors, model weights, corpus databases,
embedding arrays or SQLite working files. Owner preparation extracts and screens approved text into
the read-only knowledge index. The runtime does not open arbitrary archive PDFs
or follow instructions inside downloaded documents.

The owner-side [study-note builder](docs/NOTES_THROUGHPUT.md) resumes saved windows
and targets 8?15 source-quoted facts for substantive passages, permitting fewer
when the source supports fewer. Notes are derived aids, not lossless replacements
for original passages. Building or publishing new notes does not update the
active frozen release. Background generation shares GPU inference with chat and
can increase response latency. Updated chat and note generation coordinate admission
so a waiting chat gets the next slot; an in-flight passage is not preempted.
The Sunday extension through October 12 at 10 AM
Eastern is a one-time local scheduling exception, not the normal nightly policy.

See the [persona/model strategy](docs/MODEL_STRATEGY.md) for when specialist
models would justify their loading, memory and evaluation costs.

## Work in progress and validation

The checkout includes [MTRAGEval-inspired local RAG evaluation probes](docs/MTRAGEVAL_LOCAL.md)
for retrieval, fixed-evidence generation, and end-to-end checked responses.
The runner and five synthetic smoke fixtures are committed as a working
evaluation capability. Model-backed runs and latency comparisons are deferred
until the Grok Bot fine-tuning work finishes; the probes have not been validated
against the active frozen release or promoted to production.

The active release includes optional [teaching-profile controls](docs/TEACHING.md).
The [paired capability comparison tooling](docs/CAPABILITY_TRIALS.md) is available,
but its live comparisons have not been run.
Live capability comparisons are deferred until notes for the current source
collection finish. More documents, skills or context capacity do not establish
subject-matter expertise: the [companion evaluation](docs/COMPANION.md) records
citation, correctness and style weaknesses in its initial 29-scenario baseline.
Physical microphone, room-noise and rendered-browser acceptance remain separate
from automated checks.

To run the checkout's Python tests in a temporary copy without private documents
or credentials:

```powershell
python scripts/test-local.py
# Browser-logic suites use Node.js, for example:
node tests/voice-ui.cjs
node tests/chat-stream-ui.cjs
node tests/memory-ui.cjs
```

These checks do not activate a release or replace preparation gates. Historical
receipts are scoped to their recorded source and deployment; they do not certify
the entire current working tree. See [verification](docs/VERIFICATION.md).

## Explicit host development alternative

This mode runs outside the deployed container boundary. Do not launch it over the
production listeners or apply the isolated deployment's security claims to it.
Python 3.10+, Node 22+ for local assets, GPU drivers and a separate local Ollama
installation are prerequisites. Prepare downloads with internet access:

```powershell
npm.cmd ci --ignore-scripts
npm.cmd run vendor
python -m pip install -r requirements.txt
ollama pull qwen3.5:27b-q4_K_M
```

Start Ollama with cloud features disabled and use an explicit host-mode gateway;
see [development instructions](docs/DEPLOYMENT.md). A loopback address alone does
not enforce egress denial. Optional retrieval and corpus preparation have separate
dependencies and artifacts. The isolated installation has its own Ollama service;
it does not require starting another Windows Ollama instance.

## Licensing

Larpus-authored source retains the [MIT license](LICENSE). Dependencies and model
weights retain their own terms. The private voice image includes VoiceStudio ASR
adapter source under AGPL-3.0-only and Piper under GPL-3.0. Distribution and
network use of modified covered software can carry source and notice obligations;
a sidecar boundary does not automatically resolve copyleft obligations. Review
the exact combination before redistribution. See [third-party notices](LICENSE-NOTICE.md)
and [voice integration licensing](docs/VOICE_INTEGRATION.md).

No public service, multi-user accounts, mobile app or autonomous OS actions are
part of the deployed station.

Source dates, corrections and document authors: [source provenance](docs/SOURCE_PROVENANCE.md).

Complexity and failure tracking: [component value, interactions, regression gate and owner diagnostics](docs/COMPLEXITY.md).

Owner troubleshooting: [verbose errors and diagnostic-ID lookup](docs/VERBOSE_ERRORS.md).

[Detection-rate, false-positive/negative and coverage tracking](docs/STEGDETECT_EVALUATION.md) separates synthetic evidence from production claims.

Public checkout CI: [scope and reproduction instructions](docs/CI.md). Historical validation entries are receipts, not current deployment assertions.
