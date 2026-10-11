# Teaching profiles and experiments

The HUD's **TEACHING STYLE & EXPERIMENTS** panel lets the owner deliberately
change how Larpus teaches. It does not update model weights, create expertise,
change sources or permissions, or prove that a teaching method improved learning.
Profiles apply to the exact selected persona and skill. Persona-only settings do
not automatically apply to a selected skill.

## Owner workflow

1. Select a persona and optionally a skill. Open the teaching panel.
2. Optionally draft a request for Larpus's suggestion, then send it through chat.
   The suggestion remains ordinary text; Larpus cannot start or approve a trial.
3. Choose pace, depth, method, hint timing and challenge. Record a rationale and
   an observable success criterion, then start a three-reply trial.
4. Ask normal questions. Only completed replies consume the trial; held, stopped
   and incomplete streams do not. Record helpful/mixed/unhelpful feedback with
   evidence using the review-note field. Feedback describes owner judgment.
5. After three completed replies, the accepted style resumes automatically. The
   trial remains in the journal awaiting review. Earlier review is also allowed.
6. Enter a review note and accept as a new version, or end without accepting.
   Acceptance requires at least one completed trial reply. No automatic promotion.
7. To undo an accepted change, choose an earlier version (v0 is the default) and
   restore with a reason. This appends a version; previous versions remain.
   Review any open trial before restoring.

Default settings are steady pace, balanced depth/challenge, mixed method and
hints on request. The model may suggest alternatives in conversation. It receives
fixed user-level preferences, not authority to edit its own prompts or journal.
Narrative rationale, feedback and review text never enters the teaching protocol.
Preference compliance and pedagogical effectiveness still require owner review.

## Storage and limits

Profiles and journals are separate from chat memory, under `larpus-teaching-v1`
in browser localStorage. Clicking START explicitly saves a trial. Local HTTP,
LAN HTTPS, browsers and devices have separate stores. Nothing is synchronized to
the server. Browser data is not encrypted by Larpus and browser cleanup may erase
it. Export JSON to retain a private record. This version exports records but does
not import exports; in-app restore operates on retained accepted versions.

Limits are 24 profile scopes, 20 versions per scope, 80 trials overall, six feedback
entries per trial, 240 characters per narrative field and 160,000 serialized
characters overall. Nothing is evicted. At capacity, export before explicitly
resetting teaching data. Reset does not delete chats or remembered notes.

Invalid saved data is retained and shown as unavailable; ordinary chat continues
without teaching preferences. Writes validate a copy and update memory only after
storage succeeds. A stale-tab check catches previously committed changes; it is
not a cross-tab transaction or distributed lock. Each request refreshes the store;
a changed trial can prevent recording progress without losing the completed chat.

## Integration and validation

New clients wrap only the current user question with `LARPUS_TEACHING_V1` and a
strict, bounded JSON object. The runtime validates the enums, presents preferences
at user level, and searches the original question rather than preference metadata.
Existing clients and chat APIs remain compatible. Raw conversation history stays
unchanged; teaching preferences are read fresh for each new request. Ordinary input
filtering and grounded evidence assembly remain in place. The sealed model gains
no filesystem, network, persistence or approval tool.

Tests cover trial expiry, acceptance/rejection/restore, exact scope isolation,
invalid enums/records, corruption, quota, stale tabs, journal capacity, held chat
streams, actual HUD bindings, input limits, filtering and retrieval-query separation.
Release preparation includes `tests/teaching-ui.cjs`. Apply the normal frozen-release
workflow in UPDATES.md; checkout edits do not change the active station.

## Checkout validation receipt (2026-10-10)

- `python scripts/test-local.py`: 147 tests, OK with one skip because published
  private notes are intentionally excluded from the isolated test workspace.
- All six `tests/*.cjs` suites passed, including real teaching-panel/chat-handler
  integration with a synthetic stream. JavaScript syntax checks passed.
- Focused teaching tests passed again after input-budget and capacity coverage
  additions: four Python tests and the teaching JavaScript suite.
- Host `python -m unittest discover -s tests`: 147 tests, one failure in the
  previously recorded `test_real_child_chat_with_mock_loopback_ollama` (502 versus
  expected 200). The preceding import pipeline had the same failure before this
  feature. It remains unresolved; the host suite is not a full pass.
- Production health endpoints returned HTTP 200; model health said online and
  station status remained degraded. Active release remained `3cb9d1ee...`.
- No activation, commit or push. No rendered browser acceptance or live-model
  teaching-quality evaluation has been performed. The active station does not
  serve these new controls until a candidate passes preparation and is activated.


## Capability comparison companion

[Capability trials](CAPABILITY_TRIALS.md) adds an owner-run question bank and
paired manual scoring for comparing these profiles. The prepared starter plan is
deferred; live trials must wait for current-source study notes to finish.
