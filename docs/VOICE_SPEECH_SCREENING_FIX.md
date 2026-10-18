# Speech stopping early and replay failing - 2026-10-18

## Symptoms

The owner reported that (1) LARPUS stopped reading a reply aloud before the end and
(2) REPLAY REPLY did not read the passage again. Active release
`b029d94bfc9b43f8a3ab30c38ddad78a` already contained the 2026-10-16 empty-chunk and
replay-admission fixes; checkout and release files were hash-identical, so this was
not a release mismatch. No server diagnostic appeared because the voice route's
422/429 responses were not logged.

## Root cause

`/api/voice` synthesis ran `inspect_message` (the inbound prompt-injection filter) on
assistant text. Its patterns (`bypass|disable|remove ... security|filters`,
`ignore ... all|previous ... rules|instructions`, line-start `System:`) match normal
security prose that output DLP allows. Measured with the release's own functions:
"Never disable your security updates" and "If you ignore all the firewall rules"
were held by the input filter and allowed by output DLP.

* Streaming: one held sentence returned 422; `pumpSpeech` cleared the remaining
  queue, so speech stopped mid-reply.
* Replay: the whole passage (up to 2000 characters per part) was screened; one
  phrase, even across a sentence boundary, failed the part and `repeat()` stopped.

Contributing: all POSTs shared 30 requests/60 s per client, while speech is one
request per sentence (about 14.6 characters of audio per second, so short sentences at
higher speeds can exceed 30/min); a stream error left REPLAY REPLY disabled and
`lastText` stale; speech requests carried the chat AbortController.

## Change

* F1 `runtime/voice_routes.py`: speech text uses `hidden_format` (Cc/Cf, ZWNJ/ZWJ
  allowed) plus `inspect_output` with every persona's system prompt. Inbound
  `filter_messages` is unchanged. Voice route moved out of `Handler.do_POST`.
* F2 `web/voice.js`: skip-and-continue in `pumpSpeech` and `repeat()`, with skipped
  counts in the notice; 429/503 retried once after Retry-After capped at 5 s.
* F3 `runtime/gateway.py` `Handler.limited`: `('voice', ip)` at 120/60 s, chat and
  other API calls stay at `('api', ip)` 30/60 s; Retry-After is the real remaining
  window (`Auth.retry_after`).
* F4 `web/app.js`: a partial (errored) reply keeps REPLAY REPLY enabled and updates
  `lastText`; `api(path, body, {abortable:false})` keeps speech off the chat signal.
* F5 `runtime/diagnostics.py`: `LARP-VOICE-HELD` and `LARP-RATE-LIMITED`, with an
  optional sanitized `reasons` list of code names; no text is logged.

## Tests

`tests/test_voice_speech_screening.py`: security prose synthesizes; the same prose is
still held inbound; credentials, tokens, system-prompt lines, soft hyphen,
zero-width and control characters are still held without reaching the worker; held
logs contain only reason codes; the voice bucket allows 120 and refuses the 121st
with a bounded Retry-After while chat keeps its 30; an exhausted chat bucket does not
block speech; busy worker returns Retry-After 2. `tests/voice-ui.cjs`: a held 2nd
of 4 sentences is skipped and 3-4 still synthesize; 429 is retried once with a 5 s
cap; 503 twice is skipped and the next sentence plays; replay skips a held part and
plays the rest. `tests/chat-stream-ui.cjs`: partial replies keep replay and update the
replay target; speech fetches carry no abort signal and expose status/Retry-After.

Physical speaker playback and a live owner-browser session were not tested here.
Deployment follows the normal `scripts/releases.py` stage/prepare/activate flow.
