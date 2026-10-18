# Replay collision with unfinished synthesis - 2026-10-16

The serving release `efea1da7e01346feb44b1a151c470f0a` logged voice-worker-busy
diagnostics `2a95c2b64ef54968` and `db68ce3b771d439c` when replay was reported not
working. This differs from the previously fixed empty-synthesis WAV failure.

Stopping browser playback discards queued audio but cannot stop an already
submitted offline synthesis request. Replay immediately submitted another request,
and the host voice lock rejected it rather than waiting. Repeated clicks could
also submit several superseded requests.

## Change and limits

The HUD serializes synthesis promises. A replay waits for the existing synthesis
promise, and queued requests whose playback token has been superseded are skipped
before reaching the API. Stale replay errors cannot overwrite the current notice.
Microphone/review behavior, normal speech cleanup, audio speed and synthesis
settings are unchanged.

For older open HUDs and other concurrent callers, the host voice lock now waits
up to 30 seconds before reporting busy. Actual worker operations remain serial,
with their existing 120-second subprocess deadline. This is bounded admission,
not guaranteed fairness or an unlimited queue. Gateway timing includes admission
wait. No authentication, isolation, model or worker-image policy is relaxed.

## Evidence and rollout

Before the fix, the Python regression showed replay finishing immediately with a
busy error while a first synthesis was still held. The HUD regression showed both
superseded and latest replays reaching the API before prior synthesis resolved.
Both pass with the fix, along with the existing speech/microphone UI contracts.

Two simultaneous live candidate-profile synthesis calls both returned valid audio
instead of one failing busy. The existing worker was reused; no model was loaded
on the GPU for this test. Private numeric receipt:
`data/replay-admission-candidate.json`.

Candidate `b5a6e9fc6b5f40b4af7d89870d784369` differs from the active frozen payload
only in `runtime/voice.py`, `web/voice.js`, `tests/test_voice_admission.py` and
`tests/voice-ui.cjs`. It passes the existing complexity gate. Unrelated checkout
study-notes complexity failures remain untouched. The current voice worker, GPU
model, gateway and owner data stay available during preparation.

Preparation passed application/HUD/isolation checks, exact MCP discovery and all
70 complete static targets. The 69 skills were clean and the same 11 reviewed MCP
warnings remain. This is regression screening, not an independent audit or clean
MCP scan. The live broker check passed synthetic notes preemption and resumption;
chat completed 2.546 seconds after preemption. Private receipt:
`data/replay-admission-broker-live.json`.

Activated `b5a6e9fc6b5f40b4af7d89870d784369`, retaining
`efea1da7e01346feb44b1a151c470f0a` for rollback. The gateway drained and briefly
rebound listeners; this was not zero downtime. LAN sessions need a fresh login.
The model and selected voice worker were reused without restart. Ordinary pruning
stopped the older, unselected legacy voice container; its image remains retained.
The already-stopped owner notes writer was not restarted.

Two simultaneous serving HTTP synthesis requests both returned 200 with valid
audio, completing in 1.272 and 2.288 seconds. All required health checks passed;
overall health remains degraded for the retained static warnings. CA-verified
unauthenticated LAN API access returned 401. Private receipt:
`data/replay-admission-production.json`.

The server admission change supports already-open HUDs; a refresh is needed only
to load the new client queue. Physical browser/speaker acceptance and an actual
rollback were not tested. Rollback remains `python scripts/releases.py rollback`.
No commit or push occurred.
