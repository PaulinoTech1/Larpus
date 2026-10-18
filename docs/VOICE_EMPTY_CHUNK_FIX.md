# Speech interruption on empty synthesis - 2026-10-16

The owner reported speech stopping partway through a displayed reply. Active
release `af32daffa60946ddbfc84f4377805f7d` logged diagnostic
`b54e2528af2942a7`: the voice client received the persistent worker's generic error
response, rather than a stopped-container or isolation-preflight error. A later
short HTTP synthesis test returned audio successfully. The exact failed speech
chunk was not retained, so its trigger has not been established conclusively.

The subsequently supplied reply contains a question ending in `stay close?`
followed by a citation and period. The inference sentence boundary can release
the citation separately. Existing speech cleanup removes that citation, leaving
`. `, which reproduces the same old-worker WAV error. The prepared worker returns
a valid silent chunk for that exact cleaned fragment, and the HUD queue test with
the citation fragment inserted also passes. Private receipt:
`data/voice-citation-fragment.json`. The original wire frames were not retained.

## Reproduction and bounded fix

Using the existing pinned Piper model in a separate process in the serving voice
container, `...` and `---` each yielded no audio chunks. The old worker then closed
an uninitialized WAV and raised `wave.Error: # channels not specified`. The HUD
abandons the remaining speech queue after that response. Normal sentences worked.
This reproduces a matching interruption mechanism without modifying serving files.

The new HUD excludes speech chunks with no Unicode letters or numbers after its
existing markdown/citation cleanup. Displayed reply text remains intact.

The worker also handles empty synthesis for already-open older HUDs: it returns
a valid mono PCM16 WAV containing 50 ms of silence, with `no_speech: true`, so
their existing audio FIFO can continue to the next sentence. Actual synthesis
exceptions still propagate to the worker's existing failure response. Empty
audio chunks do not count as spoken audio. No model, dependency, GPU placement,
voice pace or noise setting is changed.

## Evidence and deployment plan

Regression tests first reproduced the WAV failure and unwanted punctuation-only
HUD requests. They pass with the fix. Existing microphone/review, speech queue,
pause/resume, replay, interruption and cancellation UI checks pass as well.

A live probe of the changed worker source, executed only in a separate process
with the existing voice model, produced normal speech, valid silent ellipsis and
separator WAVs (1,102 frames at 22,050 Hz), then normal speech again. All outputs
were mono and nonempty. Private numeric receipt: `data/voice-empty-chunk-live.json`.
This verifies WAV structure and continued synthesis, not physical speaker output.

Candidate `efea1da7e01346feb44b1a151c470f0a` is based on the active frozen payload
plus only `runtime/voice_worker.py`, `web/voice.js`, `tests/test_voice.py` and
`tests/voice-ui.cjs`. The candidate passes the existing complexity gate. Unrelated
checkout changes are preserved. Preparation builds a separate CPU voice worker
from the existing cached pinned voice base, using the same read-only voice models
and dependencies; the active worker, gateway and GPU model stay running.

Prepared-worker live tests passed the normal/ellipsis/separator/normal sequence
through its full pinned voice profile. The model loaded once, punctuation returned
valid silent WAVs, and subsequent text still produced speech. Private receipt:
`data/voice-empty-chunk-candidate.json`. Application, HUD and isolation preparation
checks passed. Complete static scans passed the release gate: all 70 targets
completed, 69 skills were clean, and the exact existing 11-warning MCP inventory
was retained. This is regression screening, not an independent audit or clean MCP
scan. Activation and health results will be recorded after the live broker check.
The worker fix is compatible with old HUDs; reloading a tab is only needed for
the new frontend filtering.

The live broker check passed synthetic preemption and notes resumption; chat
completed 7.500 seconds after preemption. Private receipt:
`data/voice-empty-chunk-broker-live.json`.

Activated `efea1da7e01346feb44b1a151c470f0a`, retaining
`af32daffa60946ddbfc84f4377805f7d` for rollback. The gateway briefly drained and
rebound its listeners; this was not zero downtime. LAN sessions need a fresh login.
The model and prior voice worker remained running throughout preparation and
activation; the previous worker is retained for rollback. The selected voice
worker is now the separately prepared worker with the same voice models and
dependencies. The owner notes writer was already stopped and was not restarted.

Post-activation serving HTTP tests returned 200 with valid mono WAVs for normal
speech, the exact cleaned citation period, ellipsis, then further normal speech.
Punctuation WAVs had 1,102 frames at 22,050 Hz and `no_speech: true`; the later
sentence returned real speech audio, demonstrating continued synthesis. All
required station-health checks passed. Overall health remains degraded for the
retained static warnings. CA-verified unauthenticated LAN access returned 401.
Private receipt: `data/voice-empty-chunk-production.json`.

Physical speaker/microphone playback, the original wire-frame sequence and an
actual rollback were not tested. Rollback remains
`python scripts/releases.py rollback`. No commit or push occurred.
