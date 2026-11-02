# Private inference broker

Version2 adds broker-owned cancellation/scheduling, separately mounted chat and
notes capabilities, pinned system-template hashes, lane budgets and reproducible
local checks. See [current policy and verification](BROKER_HARDENING.md).
The version1 policy and 2026-10-11 receipt below are historical evidence; they do
not establish version2 deployment or independent reproduction.

## Boundary

Windows gateway -> sealed stdio MCP agent in its own
network=none namespace -> private Unix HTTP socket -> minimal broker in the
existing network=none model pod -> fixed Ollama loopback 127.0.0.1:11434.
No host ports. The agent cannot reach raw model TCP; the broker has no model
files, GPU device, approved corpus, quarantine, credentials or container socket.
The broker image contains only its stdlib Python server and policy. Agent socket
volume is read-only; broker socket volume is writable, noexec/nosuid/nodev.
Both use UID1000, with mode0600 socket and mode0700 seeded socket directory.
Existing rootless, read-only, capability-drop and no-new-privileges checks apply.

## Policy and compatibility

Only GET /api/tags, GET /api/ps and POST /api/chat are accepted. Status responses
include only the approved installed model. Queries, redirects, arbitrary URLs,
model administration and other methods/routes are rejected. No upstream headers
or credentials are supplied by clients. Bodies are at most 524288 bytes and
responses at most 2 MB. Streaming caps frames and line sizes, and requires a done
frame. Duplicate keys, nonfinite numbers and ambiguous request framing are held.

The policy fixes larpus3.8:27b-q4 as the base model (model selection may route to
the other catalog entry, qwen3.5:27b-q4_K_M), 131072 context, GPU99, think=false and
keep_alive=-1. Temperature is finite 0..1. Output is 1..6000 tokens so existing
nightly facts generation remains supported; ordinary chat still requests1024.
Messages are text-only system/user/assistant, at most405 messages and64000 UTF8
bytes per message. JSON response format is optional. Tools, images, arbitrary
options and extra request fields are rejected. Policy upgrades require review.
Legacy owner benchmark/cache tools that request4K context are intentionally
not accepted through this broker; owner maintenance can operate the model through
its separately controlled executor. Explicit host developer mode remains outside
this deployment boundary; isolated Unix failure has no TCP fallback.

## Deployment and rollback

Prepare a fresh frozen release using UPDATES.md. The release manager builds the
broker offline from the cached Python image, starts it beside the existing model,
and starts a separate namespace agent with the private socket mount. Preparation
checks actual image/volume/namespace pins, raw TCP denial, broker reachability,
existing isolation, tests and scans while production stays running. No model or
voice replacement is required. Record live chat/stream/notes and deny probes before
claiming activation complete.

Pause/restart only the nightly writer around activation to bind it to the new
agent. After cutover, previous raw-access agents are stopped, not deleted. The
owner rollback path starts the retained pinned agent/broker before preflight;
rolling back to a pre-broker release deliberately restores the weaker boundary.
Images, volumes, source snapshots and previous scan evidence remain retained.
Start selects the active broker before starting the agent after reboot. Do not
manually launch old raw-access agents alongside the hardened deployment.

## Limits

The broker limits API reachability and resource controls, not prompt semantics.
A compromised trusted guard can still request allowed chat and see returned
text. DLP remains in the trusted agent path; the broker is not another DLP layer.
The Windows owner, WSL administrator, kernel and GPU driver remain trusted.
Connection limits and timeouts reduce resource abuse, not eliminate denial of
service. Full hostile-client fuzzing and physical browser acceptance are separate
from focused policy/transport and live containment tests.

## Verification on 2026-10-11

Active frozen release: `fc4f6e6f7b33447c915afb2e9e0b9c92`.
Python suites, five Node UI suites, catalog contracts, OCI/namespace inspection,
exact MCP discovery and all 70 static targets passed the release gates. All 69
skills were clean; MCP retained the same eight reviewed findings (overall health
remains degraded for this warning). This was regression screening, not a full
security audit or physical browser/device acceptance.

Real agent probes denied raw Ollama, external/LAN TCP and DNS/UDP. Private socket
chat, streaming and JSON output succeeded; administration returned403 and a
context override400. Stopping the candidate broker failed closed; restarting its
pinned container restored access. After activation, actual HUD HTTP chat returned
200 with five screened source previews, including two derived notes; streaming
returned200 and completed; unauthenticated LAN HTTPS returned401. The existing
model and CPU voice containers were not restarted. Notes resume committed windows
through the new agent, retaining the Monday10AM Eastern exception deadline.

These live checks also found an existing source-preview schema mismatch for
derived notes. The corrected path screens their original approved passage,
labels them as derived, and keeps generated interpretations out of the source
preview. Both normal and streamed replies have a focused regression test.

Private evidence lives under ignored data/: broker-live-candidate.json,
broker-restart-evidence.json, broker-full-mcp-candidate.json,
broker-active-gateway.json and each release's immutable preparation/scan state.
Rollback snapshots remain retained. Rolling back across the broker introduction
restores the older raw-access boundary; no real production rollback or Windows
reboot was performed for this change.
