# Updates while Larpus remains usable

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
is staged only. Its source queue preserves completed keys and distinguishes
publication/revision dates from retrieval dates. Document authorship uses reviewed
metadata rather than bibliography names; corrections require explicit scope and
evidence. Model/nightly restart and activation remain pending crash recovery.
The Windows bugcheck is not established as a LARPUS application defect; the
private dump and incident logs remain outside Git.
