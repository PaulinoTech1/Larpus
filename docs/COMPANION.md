# Companion controls and evaluation

These improvements cover voice, owner-controlled memory, reference retrieval,
local evaluations and chat usability. They add no action tools or network access.

## Chats and remembered notes

LOCAL CHATS is opt-in browser localStorage, scoped to the exact browser origin.
Loopback HTTP and LAN HTTPS do not share history. Saving is off initially. Up to
eight conversations contain completed user/assistant pairs only, with the existing
38-message context limit. Loading restores role and approved skill; changing roles
or skills retains the current chat. NEW CHAT saves the completed conversation when
enabled and starts another. Delete, delete all and JSON export are explicit controls.
Turning saving off retains existing saved chats. Quota or invalid-storage errors
are shown without silently replacing stored data. Delete invalid storage explicitly.

Up to five dated owner-entered notes (180 characters each) can be saved or deleted.
Only these explicitly remembered notes accompany the latest question, labelled as
reference data rather than instructions. There is no inferred memory, server chat
archive, synchronization or encryption of browser storage by LARPUS. Browser profile
access grants access to these saved records; exports are ordinary private files.

## References and conversation controls

The existing offline FTS index now ranks passage coverage and can add one screened,
bounded continuation from the exact same document section. The three-source and
serialized character limits remain. Microsoft 365 terminology no longer becomes a
spurious numeric version requirement. The HUD shows expandable source cards with
snapshot dates, locators, links and screened excerpt previews. Links are references,
not automatic requests. A preview can be withheld independently by output DLP.

Bracketed citation identifiers are checked against selected source IDs. This does
not verify that a claim follows from a passage, that a document remains current,
or that an uncited statement is correct. Old snapshots are labelled accordingly.

Skill search, a larger conversation area and explicit pipeline stages reduce
navigation. STOP aborts the browser request and stops queued speech; model work
may continue until the transport notices disconnection. Partial replies are not
added to saved conversation context. See VOICE_INTEGRATION.md for voice controls.

## Local evaluation

`python scripts/evaluate-companion.py` validates 29 authored scenarios across all
12 roles and the five Microsoft skills. `--live` runs them sequentially through
the existing local MCP/model boundary; `--limit N` selects the first N. Run live
checks from a prepared release with its normal isolation environment, not from an
unsealed checkout. Reports are private ignored `data/evals/companion-*.json` files.

Each scenario supplies a factual, practical and personality review rubric. Live
reports include answer, sources, identifier status, duration and limited mechanical
checks. Manual scores remain unset. A passing catalog or word-count check does not
certify expertise. Wrong-premise scenarios test useful pushback; witty phrasing
should remain subordinate to accurate, respectful answers.

## Validation scope

Automated regression checks cover existing auth, isolation, retrieval, streaming,
DLP and voice contracts, plus bounded speech IPC and browser storage corruption,
quota, opt-in and deletion behavior. Physical microphone/speaker and rendered
browser acceptance remain separate from these automated checks. Release preparation
also runs the existing complete local skills/MCP scanner gates before activation.

## Initial measured results (2026-10-09)

The first candidate completed all 29 local-model scenarios with released answers.
Seven exceeded the requested 120-word limit. Qualitative review found irrelevant
citations in ordinary planning, an ineffective mathematical counterexample,
overdramatic roleplay pushback and implementation guidance needing exact vendor
verification. The private companion-review.json preserves these findings; manual
scores remain unset. This is a baseline for improvement, not a certification.

For one short sentence, TTS request latency was 2.344 seconds cold and 1.000 second
warm (worker 1.778 / 0.416 seconds). Synthetic speech transcribed correctly twice:
3.640 / 1.750 seconds request latency, 3.025 / 1.190 seconds worker latency.
Digital silence returned no transcript. These are single-sentence smoke checks,
not representative microphone accuracy or sustained latency benchmarks.

## Activation receipt (2026-10-09)

Active runtime: `74bbaa7883bd4fe2807fb0aa5ec7e61a`; prior runtime
`0aa208337b6e479ebfdf97af0554213e` retained for rollback. The final payload
passed 113 Python tests, four Node suites, six isolation probes and the complete
70-target scanner gate. All skills passed; the MCP report retained its eight
existing warnings. Overall station health remains degraded for that scan warning;
all functional readiness checks pass.

After activation, local HTTP returned the HUD, memory module and persona API;
CA-validated LAN HTTPS rejected the unauthenticated persona request with 401.
A live warmed voice request returned a WAV in 1.219 seconds (worker 0.713 seconds).
A streamed chat delivered five text events followed by completion with context
counts, identifier status and three preview-bearing source cards; first checked
text arrived at 4.88 seconds and completion at 7.25 seconds for that smoke question.
These single-request measurements are not sustained performance guarantees.

The working-checkout owner restart tool subsequently passed its 12-test focused
suite, including selecting the active release's persistent voice container. Owner
tooling runs from the checkout, not the frozen runtime copy. No actual system
reboot, rendered browser check or physical room-audio acceptance was performed.
Changes have been left uncommitted.


## Teaching adaptation (working checkout, 2026-10-10)

See [Teaching profiles and experiments](TEACHING.md) for exact-role/skill profiles,
owner-approved three-reply trials, feedback journals and version restoration.
These optional browser-local controls change teaching preferences, not model
weights or permissions. Not activated by editing the checkout.
