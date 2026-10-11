# Broker scheduling, capabilities and reproducible checks

This supersedes the version 1 cooperative-admission and single-socket limits in
INFERENCE_BROKER.md. Prepared release activation is required for enforcement;
checkout edits alone do not change production.

## Scheduling and cancellation

The broker owns one generation slot across its chat and notes sockets. A valid
chat request interrupts an active note request by shutting down its upstream
connection, including a stalled read. It retains the slot until the pinned
single-slot runner completes a bounded one-token fence. Closing a connection or
releasing a host lock alone is never treated as confirmed cancellation. A failed
fence faults generation closed; health reports the failed boundary. An owner
broker restart can recover only after a new successful fence, not by bypass.

The model's existing OLLAMA_NUM_PARALLEL=1 is mandatory and inspected before use.
The fence establishes that this serial runner served a request after interruption;
it is not a global GPU-idle measurement. Owner raw probes, old-release brokers or
other model consumers outside the selected broker can still compete. Stop retained
execution services at cutover; never manually run old brokers alongside production.
Official cancellation context reference: [Ollama v0.40.0 chat handler](https://github.com/ollama/ollama/blob/v0.40.0/server/routes.go).

Generation lifetime is 180 seconds per lane, enforced by socket-shutdown timers;
upstream connect is bounded 5 seconds. A fence has a 2-second connect bound and an
8-second shutdown timer. Chat admission waits at most 20 seconds with two waiting
chat slots; model/unconfirmed cancellation failures can still return 503. Slow or
disconnected streaming clients can take up to 5 seconds to release their write.
These are bounded failure behavior, not a promise of instant chat or hard realtime.
Interrupted notes return 409 and stay pending; partial JSON is never saved. The
owner retries the same window after yielding. Notes retain 6000 output tokens and
the existing 8-15 fact fidelity rules. CPU voice and the loaded GPU model are not
replaced. The old host lock still serializes interactive requests and legacy
workers, but version 2 notes do not hold it and cannot hide chat from the broker.

## Capabilities and instruction scope

No caller-supplied header, token or priority flag selects a lane. Each listener
assigns its lane from the Unix socket on which the connection arrived. Both
sockets use UID1000/mode 0600 inside separate mode 0700 named volumes:

| Service | Socket mounts | Other mounts/resources |
| --- | --- | --- |
| Broker, model pod | chat and notes volumes RW | No corpus, model files, GPU, quarantine or credentials; 1 CPU,256MiB,64 PIDs; 16MiB tmpfs |
| MCP agent, own network=none | chat volume RO | Existing quarantine RW, no GPU/notes volume |
| Notes worker, own network=none | notes volume RO | No chat volume, corpus, quarantine, GPU or owner paths; 1 CPU,128MiB,32 PIDs; 16MiB tmpfs |

Chat volume: larpus-broker-ID -> /run/larpus-broker.
Notes volume: larpus-broker-ID-notes -> /run/larpus-notes.
Worker: larpus-notes-ID, immutable minimal stdlib image. No new host ports.
All socket mounts remain noexec/nosuid/nodev; root filesystems read-only,
capabilities dropped and no-new-privileges enforced. Model mounts stay unchanged.

The broker independently hash-checks exact approved system templates against
config/broker-prompts.json. Chat accepts owner-authored persona/allowed skill
variants and the fixed compression template. Notes accept fixed note/question/
answer templates and require exactly system+user, nonstreaming JSON. Tools,
images, unknown system prompts and cross-lane template/output escalation are
rejected. Regenerate with python scripts/broker-prompts.py after intentional
persona/skill/template changes; --check fails preparation on drift. The broker
contains hashes, not the corpus or the agent's source archives.

| Per-minute budget | Chat | Notes |
| --- | --- | --- |
| Requests | 12 | 6 |
| Reserved output tokens | 12288 | 36000 |
| Per-request output | 1024 | 6000 |

Reservations charge requested output, including cancellation/contended attempts;
they are conservative ceilings, not actual tokenizer accounting. Health/status
has a separate 120-request/minute budget. Fixed GET /api/tags and /api/ps remain;
GET /broker/state returns only lane, queue, fault and recovery counters, never
prompts or owner data. It is internal readiness, not a new MCP/model tool. Existing
body/frame/response size limits and fixed upstream remain enforced.

A compromised agent can consume its chat budget, select any approved template,
submit malicious user text and see allowed model output. It cannot obtain the
notes capability by changing environment or headers, invent system messages or
request larger output. This is scoped resource/instruction-template enforcement,
not semantic prompt-injection immunity. DLP remains trusted mediation in the agent;
a compromised guard can bypass its own DLP. Host/WSL/broker compromise remains out
of scope. Separate sockets do not identify individual code inside one capability.

## Reproduce evidence locally

No GitHub Actions/cloud execution is enabled by default. Public synthetic tests
need only Python stdlib and a fresh checkout, no models or owner data:

    python scripts/verify-broker.py --output data/broker-synthetic.json

On Linux require the real Unix-socket suite, rather than accepting its explicit
Windows skip:

    python 3 scripts/verify-broker.py --require-unix --output /tmp/broker-synthetic.json

The harness copies an explicit public file list into a disposable workspace,
tests request bounds, system/lane restrictions, budgets, stalled-connection
cancellation, failure closure, deadline shutdown and resumption. Receipts record
file SHA256s, baseline commit/dirty state when available, platform, exact test
output and limitations. They are not signed independent attestations. Review or
rerun them against identical file hashes; a baseline commit alone does not bind
uncommitted edits. Windows receipts explicitly mark Unix verification not checked.

For a prepared owner deployment, pause only the nightly writer with its identity
verified, retain the deadline, and run the explicit GPU test before activation:

    python scripts/verify-broker-live.py ID --output data/broker-live-v 2.json

This tool refuses a running note-generation process, never stops a service itself,
and sends only authored synthetic data. It observes active streamed notes, requests
chat, records preemption and confirmed recovery, and verifies note resumption.
It also runs actual OCI/namespace/volume probes. Restart the writer against the
new active notes service after activation and verify committed windows advance.
Full Python/UI/catalog/discovery/static scans remain release gates. Keep known
scan findings visible; do not call static regression screening a full audit.
A Windows reboot, actual rollback and physical browser/LAN-device acceptance
remain separate tests. Owner-local reports are evidence, not independently
reproduced certification. Public sanitized receipts may live in docs/verification;
private logs, release state and downloaded sources stay ignored under data/.

## Local deployment evidence - 2026-10-11

Active frozen release: `fb20ec0c6bc0419dbc6a3b298116820d`; previous
`fc4f6e6f7b33447c915afb2e9e0b9c92` retained. Frozen payload validation and
checkout payload comparison passed after activation. Model and CPU voice
container identities, images and start times were unchanged. The gateway drained
and rebound; the interruption interval was not measured, so no zero-downtime
claim is made. Existing LAN sessions require login again.

- Full Python, HUD contract, catalog/discovery and namespace checks passed in
  preparation. All 70 static targets completed. Ten MCP warnings remain visible
  (eight previous warnings plus two reviewed probe-related warnings). The exact
  source-pinned transition is in `config/mcp-scan-reviewed.json`; extra findings,
  changed sources or failed skill scans still reject preparation. Overall station
  health is degraded for these warnings; functional checks pass.
- [Windows synthetic receipt](verification/broker-synthetic-windows.json) and
  [Linux synthetic receipt](verification/broker-synthetic-linux.json) have matching
  source hashes. Linux exercised actual Unix sockets; Windows marks that skip.
- [Real model receipt](verification/broker-live-v2.json): synthetic active notes
  were interrupted, chat completed in 3.219 seconds, confirmed recovery increased,
  and the same notes request completed on retry. This is one controlled run,
  not a general latency benchmark.
- [Live HUD receipt](verification/broker-hud-v2.json): normal and streaming chat
  returned 200 in 10.172 and 9.812 seconds while the owner writer was active.
  Preemptions and confirmed recoveries advanced from one to three. Responses
  included five sources, streaming completed with two text events, and
  certificate-validated unauthenticated LAN API access returned 401.
- The writer resumed through the notes-only container. Saved windows advanced
  from 2749 to 2750, retaining 14 facts in the first committed window. Interrupted
  attempts remained pending and a rate-budget cooldown occurred; the first saved
  window took 102.5 seconds including yielding, while its final inference took
  32.28 seconds. The Sunday exception remains Monday 2026-10-12 10 AM Eastern.

An initial candidate preparation was stopped before activation to fix broker
refusal status mapping (429 for budgets, 503 for held/unavailable inference).
It remains retained for investigation; production kept running during preparation.
No GitHub Actions run or independent external reproduction is claimed. Reboot,
actual rollback and physical browser/device acceptance remain untested here.
