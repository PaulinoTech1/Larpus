# Updates while Larpus remains usable

## 2026-10-21 Habit-source release activated after broker-check fix

Activated `346773e17fd54b7784fd3148b07a4b0e` at 3:47:06 PM ET; previous
`03959f0891764772a962726bea4309d7` is retained as the rollback target. The
gateway (pid 23796) runs from the new release folder and
`http://127.0.0.1:8080` returns 200. Retrieval inside the live agent container
returns the Singh et al. (2024) habit article first for the psychologist and
home-assistant roles. Receipt: `data/broker-live-346773e1-activated-20261021.json`
(pass; running note preempted, chat 2.078 s after preemption, resumed note
completed). Cutover rebinds the port; LAN tabs need a fresh login.

The 2:34 PM failure ("Synthetic note finished before cancellation could be
exercised") was not a fast note: a full synthetic note takes 21-32 s. The broker
counter afterwards showed one confirmed recovery without a preemption, which
fits the note being refused straight after cutover by the broker's first-use
idle fence, before it generated anything. The old check discarded that result.
`scripts/verify-broker-live.py` now does a readiness handshake first: one chat
must complete on an idle, unfaulted broker; only an unconfirmed fence is waited
out (90 s bound), any other refusal or a fault fails. It still requires the note
to be observed generating before chat is sent, and still fails if the note ends
first, is not preempted, or the broker records no confirmed recovery. The
receipt now includes readiness attempts, the note outcome code (never its text)
and the failure message. The fix is checkout-only: the check runs from the
checkout and the release's notes worker and broker are unchanged, so
`346773e1` was activated as prepared. Before cutover the fixed check passed 5/5
on `03959f08` (`data/broker-check-20261021/03959f08-run1..5.json`).

## 2026-10-21 Textbook catalog status fixed; activation rolled back

Cause: `scripts/prepare-knowledge.py` treated every catalog document as a cached
web snapshot. The two owner-supplied textbooks,
`chicone-ordinary-differential-equations` and
`salsa-partial-differential-equations`, are admitted through
`config/reference-reviews.json`, not this builder, and have no cached original,
so the habit-source rebuild relabelled them `unavailable`. They were added to the
committed catalog on 2026-10-18 (`1efdf79`) as `owner-reviewed-local-reference`;
the active `03959f08` corpus predates that and lists neither.

Fix: the builder now leaves `owner-reviewed-local-reference` entries untouched
and never fetches them (`load_documents`, with a regression test). Both catalog
entries were restored byte-for-byte to their committed values. No text, source
or passage was added. The rebuilt index and vectors were reused unchanged.

Prepared `346773e17fd54b7784fd3148b07a4b0e` at 2:33 PM ET. Its payload differs
from `8203e538` only in `knowledge/sources.json`, `scripts/prepare-knowledge.py`
and `tests/test_knowledge_preparation.py`. Against `03959f08` the index adds 124
role rows (62 passages), all from the habit article, and removes none. Checks
passed; 69 scan targets pass and `mcp` keeps the known reviewed warning.

Activated at 2:33:58 PM ET. The gateway ran from the new release directory and
`http://127.0.0.1:8080` returned 200. `scripts/verify-broker-live.py` then failed
(`data/broker-live-346773e1-20261021.json`: "Synthetic note finished before
cancellation could be exercised"), so the release was rolled back to `03959f08`
at 2:35:07 PM ET as instructed. Afterwards the same check passed on `03959f08`
(`data/broker-live-03959f08-baseline-20261021.json`) and on the still-prepared
`346773e1` (`data/broker-live-346773e1-prepared-retry-20261021.json`, 2.25 s
chat after preemption). Host-side retrieval on the `346773e1` corpus returns the
habit article first for both roles. `346773e1` remains prepared and is the
recorded rollback target; re-activation needs the boss's go-ahead.

## 2026-10-21 Habit-formation source — prepared, not activated

Prepared `8203e5380a1b4dbea18c9c9084edecf9` at 1:55 PM ET. It is the active
`03959f0891764772a962726bea4309d7` payload plus only the Singh et al. (2024)
habit-formation systematic review: Europe PMC JATS XML, CC BY 4.0, SHA-256
`d60c91f1a33822dbd5733f0beb64f0f402761ff5f6bdd9b5cccaabd0a27aaa46`, 62 passages
for the psychologist and home-assistant roles (124 role rows). Index rows go
from 76,726 to 76,850. Vectors go from 74,709 to 74,771: the 74,709 existing
vectors were reused after hash verification against the active release and
only the 62 new passages were embedded. The payload also carries the XML
source rule, the incremental `--reuse-index-from` indexing option and their
tests. Complexity, the isolated suite, UI checks, isolation and the scan passed;
69 scan targets pass and `mcp` keeps the existing source-pinned warning. The
earlier `9ce4ddd7929940f39bfdb85f9515cc89` attempt stopped at the complexity
gate and is not a candidate.

Active is still `03959f08`; activation needs the boss's approval. Before that,
review one catalog difference: the candidate's `sources.json` marks
`chicone-ordinary-differential-equations` and
`salsa-partial-differential-equations` as `unavailable` (cached snapshot
missing during the rebuild), where the committed checkout catalog lists them as
`owner-reviewed-local-reference` (correction: the active release has no entries
for them at all). Neither release's index has rows for them, so
retrieval is unchanged, but the catalog status changes. The checkout's own
`knowledge/` database and vectors are a broader local rebuild, are not the
candidate's and were not shipped. Do not pool timing runs taken during this
source work into the latency receipts.

## 2026-10-21 Verified timing spans — activated

Activated `03959f0891764772a962726bea4309d7`; previous
`b6dffca22d244953acb3a8574c232e69` is retained. The candidate uses the current
checkout code and that previous release's knowledge corpus. The checkout corpus
was not shipped: its embedding index did not match the approved database.
Ultra Fast does not collect the new preflight, retrieval, or child-import
spans. Verified and Diagnostic do. This is not a measured latency improvement
and does not meet the 5.9 s / 6.8 s first-text target.

Preparation passed pipeline switching, the frozen suite, UI checks, isolation,
and complexity at 941 functions / 117 modules. The scan kept the prior warnings
except the static `isolation.py` subprocess count, which is 5 rather than 6
because the distro probe is submitted to the existing read pool. That count
change is source-pinned in `config/mcp-scan-reviewed.json`. It is not a clean
scan. `security_scan` remains a warning. Fresh local health checks otherwise
pass. The gateway process is pid 27656. Cutover rebinds the port and LAN tabs
need a fresh login. Two earlier snapshots, `eb3bee8407624c349680ae5a6050df92`
and `ee739ab5a5cf44e697bae7cdef1ae8ec`, were not activated.

## 2026-10-21 Recovery and owner tools — activated

Activated `b6dffca22d244953acb3a8574c232e69`; previous
`042f91c0a1454887a694c945f49237ad` is retained. Fresh readiness, broker and
prepared-pin checks pass. Model/CPU voice images and start times are unchanged.
The same 11 reviewed MCP warnings remain visible. Recovery stays disabled,
backups synthetic-only; execution profiles/MCP Skills remain excluded.
Whole-command time was 29.016 seconds; an unsupported sampler URL prevents a
reliable interruption measurement. LAN tabs need a fresh login. See the
[activation record](RECOVERY_ACTIVATION_2026_10_21.md) for retained evidence and
the gates that still prevent expanding scope. Earlier entries are historical.

## 2026-10-21 Recovery and owner tools — prepared, not activated

Prepared `b6dffca22d244953acb3a8574c232e69` from a scoped variant of the active
payload. Frozen tests, ten UI suites, complexity, isolation and prepared pins
passed. Fresh scans completed all 70 targets with the same 11 reviewed MCP
warnings. One rejected frozen candidate and its fixture correction are retained.
Selected release remains `042f91c0a1454887a694c945f49237ad`; gateway identity,
active payload hashes and model/voice images and start times stayed unchanged.
Execution profiles/MCP Skills were excluded. Recovery remains disabled and
backups synthetic-only. No activation or push occurred. See the
[preparation record](RECOVERY_PREPARATION_2026_10_21.md) for exact scope and limits.

## 2026-10-20 Six improvements — worktree candidate only

The recovery worktree closes independent review of final death-count handling,
adds encrypted synthetic SQLite restores, hash-bound quality review accounting,
a read-only owner snapshot, one shared verification command and separate timing
clock groups with offline quality-gated admission. No latency optimization, live
quality comparison, owner-data backup, production observation, arming or activation
is claimed. Backup destination is D: with three-calendar-month retention, remaining
synthetic-only until key custody is decided. See
[implementation evidence](SIX_IMPROVEMENTS_2026_10_20.md) and
[owner commands and limits](OWNER_OPERATIONS.md).

## 2026-10-20 Independent recovery - implementation candidate

The isolated `feat/recovery-supervisor` worktree adds an owner-side supervisor,
durable attempt journal, generation-bound health receipts and disposable failure
drills. It is disabled by default. No supervisor installation, production
observation window, arming or release activation accompanies this implementation.
See [RECOVERY_SUPERVISOR.md](RECOVERY_SUPERVISOR.md) for commands, evidence scope
and the separate observation/rollout proposal. Existing production release files,
pins, scan receipts, model and CPU voice are not modified by this work.

## 2026-10-20 Failure isolation - activated

Activated `042f91c0a1454887a694c945f49237ad`; previous
`7df2e957751642d6ace4630fa047fe94` is retained for rollback. This is a scoped
source variant of that production release, retaining its corpus, prompts,
configuration and transport. Execution profiles and MCP Skills remain
unpromoted. Frozen preparation passed the 321-test suite, ten UI suites,
companion contracts, scorer switching, isolation and all 70 scan targets, with
69 clean skills and the same 11 reviewed MCP warnings. Complexity limits were
unchanged. Two rejected preparations and their reasons are retained.

Live synthetic broker preemption/recovery, chat, completed streaming, CPU speech,
full GPU placement and CA-validated unauthenticated LAN rejection passed. Model
and voice images/start times stayed unchanged. Activation's whole command took
30.374 seconds; catalog sampling bracketed its two failed requests between
successes 3.729 seconds apart. This was a brief gateway rebind, not zero downtime.
LAN tabs need a fresh login. No rollback was required; rendered HUD, physical
microphone and second-device acceptance remain unverified. See the
[deployment record and two-minute owner pass](FAILURE_ISOLATION_RELEASE_2026_10_20.md)
for the exact source delta, validation limits, retained failures and receipts.

## 2026-10-20 Verified overlap screen - prepared, not promoted

Prepared `306986ac3d954e7791b2b7a3028838e2` and did not activate it. Selected
release remains `7df2e957751642d6ace4630fa047fe94`. The only scan-count change
is the distro probe, still a fresh `subprocess.run`, now submitted to the
existing three-worker read pool; the scanner reports five isolation call sites
instead of six. One eight-case round kept a Verified `home-uncertainty` failure.
Ultra Fast first-text mean/p95 were 4.845/6.391 seconds. The five-second tail
was not met, and answers were not rubric-reviewed. The station was returned to
stopped, including Larpus WSL. See [the screen](VERIFIED_LATENCY_2026_10_20.md).

## 2026-10-20 Secure execution profiles - prepared, not accepted

Candidate `dc74ddc8315d4fdaa6349c72fc40bc46` adds strict request-local profiles,
independent integrity hashing, bounded diagnostics and fresh batched observation
collection without reducing mandatory security. It excludes unrelated inactive
checkout features. Preparation completed 70 scan targets with the same 11
reviewed warnings. Final checkout validation: 457 tests, four skips, 11 UI suites.

The 300-attempt owner-loopback comparison measured Ultra Fast first-approved
mean/p95 5.718/7.980s versus Verified 6.703/9.045s. Pacing passed, but the
five-second target failed and agent answer review did not establish quality
parity. Five attempts failed; all 295 successful answers received blind rubric
review. This candidate was not activated. Selected release remains
`7df2e957751642d6ace4630fa047fe94`; the temporary station was stopped afterward,
including model/voice and Larpus WSL, with notes still Disabled. No commit/push.
See [acceptance, retained failures and limits](EXECUTION_PROFILES_PERFORMANCE_2026_10_20.md).


## 2026-10-19 MCP Skills - prepared, not activated

Candidate `c7a16c1c9fbc408199b1d05a57d15244` adds read-only standard Skills
list/get and resource reads for the 69 reviewed local skills. The three tools,
explicit persona selection, instruction bytes, model/voice pins and security
boundaries remain unchanged. Main integration passed 398 tests (four skips),
all ten UI suites and prompt pins; sealed Linux protocol/resource checks passed
13 tests without skips. Preparation completed 70 scan targets, retaining the
same 11 reviewed MCP findings.

Focused timings were mixed: initial Home first-text median +11.8%; the registered
confirmation showed Home -3.1% but math +11.9%, with pacing variation. AI answer
review also found existing and candidate arithmetic/attribution issues, and
reference selection varied. This does not establish stable performance or
unchanged answer quality. No optimization C or automatic activation was adopted.
The eight-case comparison and its single confirmation also remained mixed;
all 244 benchmark calls delivered replies and 192 measured answers received AI
rubric review. Successful delivery is not factual correctness.
The station still selects `7df2e957751642d6ace4630fa047fe94`.
See [acceptance](MCP_SKILLS_ACCEPTANCE_2026_10_19.md) and
[measurements](MCP_SKILLS_PERFORMANCE_2026_10_19.md) for receipts and limits.

Owner startup also avoids whole-pod start, which revived retained historical
containers during the controlled restart check. It starts only the model and
selected services, retaining broker/model readiness before gateway admission.
See [startup evidence](BROKER_COLD_START_RECOVERY_2026_10_19.md).


## 2026-10-19 Response consistency experiment - not promoted

Prepared `ddf716bcc1f04df891de7545f2052b64` with a single fresh WSL security collector. First-text median/p95 improved about 13.4 percent in 24 paired cases, with unchanged evidence and all frozen gates passing. However, a separate pacing confirmation failed the registered median chunk-gap criterion. The candidate was not activated, and the checkout default was restored to the existing preflight. Current release `7df2e957751642d6ace4630fa047fe94` remains selected. All results, including the failed criterion, are retained in [the consistency report](RESPONSE_CONSISTENCY_2026_10_19.md). No security checks were removed or cached.

## 2026-10-19 Response latency

Activated `7df2e957751642d6ace4630fa047fe94` after clean paired checks and frozen preparation. Reuse of verified request-local SQLite connections, bounded read-only mapping and batched fresh OCI reads reduce first approved text from 5.869 to 5.457 seconds in the 16-pair sample. Evidence matched in every pair; model, prompts and budgets stayed unchanged. Assembly optimized is selected. Existing quality limitations remain. Live health and streaming passed; the temporary test station is stopped, including all LARPUS containers and WSL. See [measurement scope and retained evidence](RESPONSE_LATENCY_2026_10_19.md).

## 2026-10-19 Assembly optimized candidate

Assembly optimized is a separate selectable module: the tested four-worker pool,
the unchanged half-precision kernel, and a huge-page-backed aligned matrix.
Assembly original and NumPy stay selectable. Loading or scoring failure uses
NumPy. A stopped-station repeat measured about 35% lower warm scoring time than
NumPy and a 56 MiB huge-page reservation. See the
[module check](ASSEMBLY_OPTIMIZED_2026_10_19.md).

Prepared `341de68e12974563ab8da85c370542cc` and did not activate it. The active
release remains `f08b98ea2f34407cb77dc79aa7d7866a`. This candidate ships the
scoring module with that release's consistent knowledge index. The checkout's
newer catalog stays in the working tree; its embedding manifest does not match
its database, so it was not included. Frozen preparation passed pipeline
switching, the local suite, UI checks, isolation, and all 70 scan targets with
the same 11 reviewed MCP findings. The gateway stayed down. The shared model
ran only for the isolation check and was stopped afterward, along with voice
and the candidate containers. Earlier snapshots
`1d36d849aa1d401d80c5a3e69708d437` and `46248d8a37ec424ca39dfc748314f1c0` were
not prepared.

## 2026-10-18 Assembly dispatch/cache follow-up

Activated `f08b98ea2f34407cb77dc79aa7d7866a` with cached immutable matrix partitions and
safe joining after partial task submission failure. Pressure/post-embedding
scoring medians improve by tens of microseconds; other results are mixed and
no overall chat latency gain is established. The native kernel and model/voice
settings are unchanged. Local suite: 320 tests, two skips. Frozen preparation
completed all 70 scan targets with the same 11 reviewed MCP findings. Live
switching, reply, functional health and LAN authentication checks passed;
model/voice IDs, images and start times stayed unchanged. Activation succeeded
without rollback; 25.837 seconds is whole command
time, not measured port downtime. See the
[cache tuning report](ASSEMBLY_CACHE_TUNING_2026_10_18.md).

## 2026-10-18 Conversation progress and tuning follow-up

Activated `b029d94bfc9b43f8a3ab30c38ddad78a` after prompt-only repetition
attempts were rejected. Ordinary chat now has bounded broker-owned repetition
controls and shared continuity guidance; persona humour is optional. The tested
follow-up avoided the copied closing, while broader tone/grounding limitations
remain documented. The local suite passed 317 tests with two skips; the candidate
passed its frozen checks and all 70 scan targets with the same 11 reviewed MCP
findings. Model and CPU voice IDs, images and start times stayed unchanged.
Activation succeeded without rollback; the 25.079-second whole command is not
measured port downtime. See [conversation progress](CONVERSATION_PROGRESS_2026_10_18.md).

Further hardware experiments yielded only 1.5â€“4.2% incremental scoring savings
over deployed Assembly in direct runs. Those native changes were rejected and
the existing Assembly implementation retained. See the
[5900X tuning follow-up](CPU_TUNING_FOLLOWUP_2026_10_18.md).

## 2026-10-18 Assembly pipeline

Activated `d604dfcd7ebd4c0199cdec395b6c61cf` after the owner approved near-tie
reordering. Assembly is the startup default, with a station-wide HUD switch to
NumPy and automatic fallback. Two Linux runs measured approximately 31% less
scoring time (about 1 ms); an overall chat latency gain is not established.
All 70 scan targets completed with the same 11 reviewed MCP warnings. Model and
CPU voice IDs, images and start times stayed unchanged through activation;
live reply, switching, functional health and LAN authentication checks passed.
The activation command took 26.167 seconds including drain/readiness/pruning,
not measured port downtime, and no rollback was needed. See
[Assembly pipeline](ASSEMBLY_PIPELINE.md) for policy, measurements and receipts.

## 2026-10-17 CPU timing and scoped WSL maintenance

Activated `690d8bcbedcd4ff2a0f710b8fedaaa83` after Python/UI/isolation checks and
70 complete scan targets, retaining the same 11 reviewed MCP issues. Preparation
kept production available; app activation briefly rebound ports while model and
voice start times stayed unchanged. The separately approved WSL restart then
applied `processors=20`, preserving the 48 GB memory limit and existing image
pins. Recovery from the drained gateway took 139.891 seconds; this was an
interruption, not zero downtime. 3.8 full GPU/context, synthetic voice audio,
functional health and CA-validated LAN authentication were verified afterward.
The superseded first candidate's scan was cancelled and never activated.
See [CPU tuning](CPU_TUNING.md) for measurements, limitations and rollback files.

The running gateway now uses a frozen source, HUD and knowledge-index snapshot
under `data/releases/<32-hex-ID>`. Editing this checkout does not change its
fingerprint, static files or selected agent. Preparation runs beside production;
only activation briefly interrupts the gateway listeners.

## Owner workflow

From the Windows project directory:

```powershell
python scripts/releases.py status
# Edit code/personas/knowledge and prepare reviewed data in the checkout.
python scripts/releases.py stage
# Use the ID printed by stage:
python scripts/releases.py prepare ID
# After preparation succeeds, apply the update:
python scripts/releases.py activate ID
```

Preparation does not activate. It snapshots fixed public source directories plus
the private approved index, pins every payload file including HUD assets, checks
that the checkout did not change during copying, and builds a separate rootless
agent with `--pull=never --network=none`. The existing GPU model and CPU voice
stay running; a second GPU model is not loaded. Linux runtime wheels come from
`/home/larpus/build/vendor/runtime-wheels`, with SHA256SUMS checked. The cached
Python image is resolved to its local immutable image ID before the build.

Broker-enabled candidates also build a minimal offline broker in the existing
model pod and a release-specific private socket volume. The candidate agent uses
its own network-disabled namespace and mounts only that socket volume read-only
alongside its existing quarantine. Model and voice are not replaced. Restart the
owner nightly writer around activation so it selects the new agent. After a
broker cutover, retained pre-broker agents are stopped; rollback can restart them
and deliberately restores their weaker raw model boundary. See
[inference broker](INFERENCE_BROKER.md) for exact policy and maintenance scope.

Version2 also builds a minimal `larpus-notes-ID` service with only the separate
notes socket mounted read-only. Chat and notes share one broker-owned generation
slot. Preparation checks `python scripts/broker-prompts.py --check`; intentional
persona/skill/system-template changes require regeneration before staging. It
inspects the existing model's `OLLAMA_NUM_PARALLEL=1`, without replacing it.
Run the explicit local live preemption harness with the owner writer paused,
then activate and restart that writer. Retained execution services are stopped
after version2 cutover and remain restartable for owner rollback. This avoids
an old broker continuing outside the selected scheduler.

The candidate must pass Python tests, voice/chat UI tests, isolation probes,
exact approved MCP discovery and complete static scans. Skills must be clean.
The MCP finding inventory must match the previously reviewed category/pattern/
severity/file counts; a changed inventory blocks release for review. This is
regression screening, not a security guarantee or suppression of warnings.
An intentional inventory transition can be recorded in
`config/mcp-scan-reviewed.json`: exact previous/approved counts, rationale and
SHA256s of the reviewed public sources. Any extra/missing finding, source drift,
incomplete scan or skill warning still rejects preparation. The warnings remain
in the actual scan and health report; this is a reviewed transition, not a clean
scan or blanket severity exception.
Preparation failures leave the current gateway untouched. Fix the checkout and
stage a new ID; failed snapshots/containers remain available for investigation.

Activation checks payload hashes, deployment and scan receipt pins and live
isolation again before touching production. The owner-only drain marker refuses
new inference/voice work with a short retry response while existing gateway
requests finish. Listeners close, the prepared gateway binds the same local/LAN
addresses, and functional health must pass within 60 seconds. A failed candidate
is stopped and the previous release restarted automatically. The active pointer
is replaced only after readiness succeeds. No update-control HTTP/MCP tool exists.

## Rollback and restart

```powershell
python scripts/releases.py rollback
python scripts/releases.py start
python scripts/releases.py status
```

`start` recovers a recorded interrupted cutover to the previous release (or keeps
an already committed/restored healthy gateway recorded in the active pointer), starts
the existing offline pod/voice/selected agent after reboot, and starts the frozen
gateway. Existing `start-lan.ps1` and `run-isolated.ps1` prefer this active release.
Process creation identity is checked before signalling; reused PIDs are not killed.
Owner update operations use an exclusive Windows file lock; status is read-only.
If a drain cannot finish within 180 seconds, the updater refuses forced termination.
An OS/owner-process failure at the instant of launching before recording a PID,
or a stuck process/occupied port, can still need owner investigation. The journal
and per-release gateway logs remain under `data/releases`.

## State, ports and limits

- Local HTTP stays `127.0.0.1:8080`, password-free; home LAN HTTPS stays
  `192.168.1.2:8080`, with the existing password, certificate and subnet rules.
- Release `data` junctions refer to the same existing owner data. Password hashes,
  TLS keys, voice deployment profile, recordings and original-document caches
  are neither copied into release payloads nor rolled back. Release `vendor`
  junctions use the existing owner preparation/scanner dependencies.
- Each release has its own `deployment.json`, agent image/container pin and
  `release-state/security` and `release-state/health`. Its agent is named
  `larpus-agent-<ID>` in its own `network=none` namespace, with quarantine and
  read-only chat socket mounts and no new ports/devices. The broker shares only
  the existing model pod network; the minimal notes service has its own disabled
  network and only its read-only notes socket. Prior containers/images/snapshots
  are retained. Pruning stops idle execution services; it never deletes models.
- The first legacy frozen release uses `larpus-agent` and the previous scan/data
  paths. Its gateway predates graceful draining; the one-time transition requires
  a quiet chat/voice period. Subsequent releases use the drain watcher.
- Port rebinding is a brief interruption, not zero downtime. Browser history stays
  in its existing tab; there is no forced reload. LAN login sessions are held in
  process memory, so another login is needed after switching gateway processes.
- Shared Python/scanner dependencies, model/voice replacement, CUDA drivers,
  Windows/WSL and incompatible data migrations need separate maintenance and
  rollback plans. Do not replace shared dependencies while production uses them.
  Never recursively back up through release `data`/`vendor` junctions: select
  payload files and owner state separately to avoid traversal cycles.

The update manager is an owner Windows CLI, not an agent skill or model tool.
Use it from this working checkout; frozen release copies are execution payloads,
not the place to edit or upgrade the owner tooling. Source-tree integrity failures
remain fail-closed within each release rather than being disabled for availability.

## Persistent voice rollout

Voice worker code updates now build a separate CPU-only, network-disabled container
from the cached pinned image. Preparation checks the release-local profile and
worker readiness without replacing the active voice service or global legacy
profile. The new profile is checksum-pinned in the prepared release receipt.
Unchanged persistent worker hashes reuse the prior persistent container; changed
hashes get a new per-release container. Retain earlier voice containers for rollback.
No new ports or host-writable voice mounts are added. Model/dependency/driver changes
still require their own maintenance plan.

The working-checkout `start` command selects the active release's voice container
from its local profile, falling back to the legacy profile for old releases. Its
restart regression uses mocked process/container operations; it does not simulate
an actual Windows/WSL reboot. Always invoke owner tooling from this checkout.

## Idle container cleanup

`python scripts/releases.py prune` stops (never removes) every running
`larpus-agent*`/`larpus-voice*` container except those used by the active and
previous releases, leaving the pod infra and `larpus-model` alone. `start` and
`activate` run it automatically, because `podman pod start` revives every retained
release. Stopped releases keep their images and snapshots; start one manually
before rolling back further than the previous release.

## Activation readiness depends on a loaded GPU model

`activate`/`start` readiness reads `/api/station-health`, which is a monitor
file (refreshed about every 60 seconds), not a live Ollama probe. After WSL
restarts or model-container swaps the model may be unloaded, so `model_gpu`
stays `warning` and cutover/rollback both fail even when the candidate is fine.
Load the model once (send a chat, or a sealed `/api/chat` with the configured
`num_ctx`) and wait for `model_gpu: pass` before activating. See the 2026-10-09
decision entry for the full incident, the prune interaction, and recovery steps.

## Cooperative admission activation ? 2026-10-11

Activated 8ab6f5664f874fbc9b5a7a4f8a1e12ac; retained
3cb9d1eea7424d929209ecf9cc549f59 for rollback. Preparation passed the Python
suite, five configured Node suites, six isolation probes and all 70 static
scan targets. All 69 skills were clean; the MCP inventory matched eight reviewed
warnings. Functional readiness passed; overall health remains degraded for the
scan warning. No model/voice images, ports, authentication or shared dependencies
were replaced. The gateway cutover briefly rebound listeners; it was not zero
downtime. CPU voice and the model service stayed running.

The first snapshot was rejected because changing note-builder WAL/SHM files
entered its payload inventory. Those transient files are now excluded consistently
from copying and hashing. The rejected snapshot remains for investigation;
production was not stopped or modified to bypass the rejection.

An initial owner background-admission probe expired under continuous competing
background work. The controlled live probe then reserved the gateway's interactive
priority, held the inference slot, and verified HTTP 200 after release. Separate
live checks confirmed the updated generator yielded at a passage boundary and
saved another window after release (2549 -> 2550 committed windows). This establishes
cooperative admission, not preemption, fairness between background callers, or a
latency benchmark. Private numeric receipt: data/chat-priority-live.json.

The generator alone was restarted to adopt the coordination code; committed
progress and the Monday 10 AM Eastern exception remain intact. LAN unauthenticated
API access remained 401 with CA validation. Served JavaScript contains the requested
LARP 3.5 27B Limitless LARP label. Refresh existing tabs to load updated UI code;
LAN sessions need another login. Physical microphone/rendered-browser acceptance
was not performed.

The snapshot also adopts the prepared 404-document / 76660-passage approved library,
whose embedding/library hash binding matches, and the optional teaching controls
already present in the checkout. Live capability comparisons remain deferred.
No current changes were committed or pushed during this activation.

## 2026-10-11 source chronology and provenance update

See [source provenance](SOURCE_PROVENANCE.md) for the reason, metadata policy,
non-destructive audit and validation. The candidate `43afda5d3e184b249420caca0f8d043e`
was staged only at that review. Its source queue preserves completed keys and distinguishes
publication/revision dates from retrieval dates. Document authorship uses reviewed
metadata rather than bibliography names; corrections require explicit scope and
evidence. At that review, model/nightly restart and activation were pending crash recovery. The later activation below includes the provenance changes; the nightly workload remains stopped.
The Windows bugcheck is not established as a LARPUS application defect; the
private dump and incident logs remain outside Git.

## 2026-10-11 diagnostic update preparation review

Candidate `9573bf3d691444dc90ed206063f98339` passed application/UI/isolation checks and all 70 static scan targets, but preparation rejected its MCP inventory transition from 10 to 11 warnings. The extra LOW finding is diagnostics `getattr(current,name,None)` with names restricted to the literal `errno`, `winerror`, `returncode` tuple and exact-int output. The reviewed transition now pins the relevant public sources and retains every warning. The rejected snapshot/receipts are untouched; a new snapshot must be independently prepared before activation. No independent audit or clean-scan claim.

Post-reboot recovery also observed `cancellation_unconfirmed` while the GPU model was cold. The retained gateway failed its initial readiness check; after owner-local model warm-up and restart of only the faulted broker, HTTP chat succeeded and required health checks passed. Pod start revived retained execution containers; ordinary pruning stopped obsolete agents/brokers without stopping the model or selected voice. The nightly workload was not restarted. These are application recovery observations, not an explanation of the earlier Windows bugcheck.

Activated `9d76eed753ad4ec9901c8b988e961248`; retained `fb20ec0c6bc0419dbc6a3b298116820d` for rollback. Replacement preparation passed application/HUD/isolation checks and all 70 static targets, with 69 clean skills and the exact reviewed 11-warning MCP inventory. The synthetic live broker test completed chat 3.156 seconds after preemption and resumed notes successfully. A candidate notes-worker invalid-job probe produced an exact reviewed message and correlated ID with protocol-only stdout.

After activation, HTTP chat returned 200 (8.922 seconds), streaming completed without error (5.656 seconds), and CPU speech synthesis returned audio (1.953-second gateway timing). Local HTTP persona access returned 200 without a password; home-LAN HTTPS validated the existing CA and returned 401 without authentication. Required health checks all passed, including full GPU placement, voice and egress enforcement. Overall health remains degraded only for static scan warnings. Model and voice image pins are unchanged.

The gateway drained/rebound its listeners; this is not zero downtime. LAN sessions need a fresh login. Prior execution services were stopped but their images/snapshots remain restartable for rollback. Private numeric receipts: `data/production-broker-live-9d76.json`, `data/production-diagnostic-smoke.json`, `data/production-activation-9d76.json`; no private source content was recorded. Physical microphone/second-device acceptance and sustained nightly workload were not tested or restarted. The earlier Windows bugcheck remains unresolved.

### Process followed for this activation

1. Read this update policy and checked `python scripts/releases.py status`. The selected retained release was stopped after the reboot; no interrupted-cutover journal was present.
2. Ran `python scripts/releases.py start`. Its initial functional-readiness check failed with the model unloaded. An owner-local short warm-up used the existing model container, followed by restart of only the faulted broker. A subsequent HTTP chat and required health checks passed. No model/voice image or shared dependency was replaced. This recovery is not a fix for the Windows crash; do not reset a broker during active work without checking its state.
3. Ran `python scripts/releases.py stage`, then `python scripts/releases.py prepare 9573bf3d691444dc90ed206063f98339`. Complete scans found a changed MCP inventory, and preparation refused it. The serving gateway stayed running.
4. Reviewed the added warning in source and recorded the exact previous/approved inventories, rationale and public source hashes in `config/mcp-scan-reviewed.json`. No frozen file or scan receipt was edited. Stopped the rejected candidate's unused execution containers and retained its artifacts.
5. Staged again and ran `python scripts/releases.py prepare 9d76eed753ad4ec9901c8b988e961248`. This independently repeated builds, tests, discovery, isolation and all static scans; it did not reuse the rejected preparation as approval.
6. Ran `python scripts/verify-broker-live.py 9d76eed753ad4ec9901c8b988e961248 --output data/production-broker-live-9d76.json` with the owner writer stopped. Synthetic preemption and resumption passed. The invalid-job diagnostic probe also passed.
7. Verified the snapshot was prepared, then ran `python scripts/releases.py activate 9d76eed753ad4ec9901c8b988e961248`. Drain, readiness and pointer replacement succeeded; ordinary pruning stopped retained inactive execution services. Rollback remains `python scripts/releases.py rollback`; restart/recovery remains `python scripts/releases.py start`.
8. Checked active/previous IDs, required health checks, HTTP chat, NDJSON completion, synthetic CPU speech, local password bypass and CA-validated LAN authentication rejection. Kept numeric receipts in ignored owner data and recorded limitations above. No nightly training restart or second-device/physical-microphone acceptance was performed.

These IDs document this completed operation; future updates must use their newly staged ID. Documentation and source-review commits do not themselves activate another snapshot. Private scan reports, logs, corpus data and credentials remain outside Git.
