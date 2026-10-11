# Facts-first nightly notes

Future `scripts/study-notes.py generate` runs target 8-15 distinct quoted facts
per substantive passage, preserving assumptions, exceptions, uncertainty, scope,
competing findings and important examples or proof steps. Sparse passages may
yield fewer than eight: unsupported padding is forbidden. The retention cap is 15.
New summaries and prepared Q&A are omitted from this pass.
`answers` remains a separate owner action; it is not automatically scheduled here.
Completed windows and existing summaries/Q&A are retained without regeneration.

Only byte-identical passage text from the same source is deduplicated. A repeated
window receives its own notes at its own locator. Different sources are never
merged, even when their words match. Source IDs, titles, URLs, exact supporting
quotes and surrounding context remain in the existing note schema. Retrieval
continues to attach author citations from `knowledge/authors.json` using source ID;
the original source, rather than the derived note, is cited. Missing author metadata
is not invented. No original source files or approved index entries are removed.

Malformed model JSON remains retryable instead of being recorded as completed.
Grounding still checks quote presence, not semantic entailment: a matching quote
does not independently prove that the claim accurately represents it. Concision
can omit nuance or secondary facts; original passage retrieval remains essential.

## Speed expectations and measurements

The read-only inventory on 2026-10-10 found 13,105 total windows, 12,095 pending,
and 46 pending same-source exact duplicates (0.38%). Deduplication alone therefore
saves little work on this collection. Remaining windows averaged 4,343 characters.
The preceding 100 completion intervals had a median of 21.5 seconds; that is a
wall-clock baseline, not a measured separation of prompt and output processing.

The earlier 20-40% time-saving estimate applied to the superseded five-fact pass.
It and the associated October 13-15 completion projection are no longer reliable
with the owner's preference for 8-15 nuanced facts. No new speed estimate is
validated until ordinary nightly timing arrives. The same 27B model still reads
every distinct passage. No smaller model, reduced context, GPU concurrency or
separate benchmark is introduced. Generation now permits up to 6,000 output tokens
for notes (other worker uses retain 2,400); this is a ceiling, not a required length.
Responses reporting an output-length stop are left retryable, not marked complete.
More facts improve intended coverage but do not guarantee every nuance is retained.

Each future request logs elapsed seconds, input characters and Ollama token counts,
prompt evaluation, generation, load and total durations (nanoseconds), plus stop
reason when supplied. Compare representative source types and retained facts per
unit time; do not compare only total note count across the two output formats.
Timing arrives during ordinary nightly work; capability trials remain deferred.

## Availability

This changes the owner-side checkout script, which the existing nightly launcher
invokes. The next invocation loads the new code; an already-running Python process
keeps its old code. No writer was started or stopped, no schedule was changed,
and no active release or published note database was modified by this update.
The existing launcher still publishes the checkout note database after generation;
that does not activate those notes in production. Production adoption remains a
separate staged-release update.

## One-time Sunday extension (2026-10-11)

The owner-authorized exception in ignored data/study-notes-exception.json keeps the
nightly launcher resuming saved progress through Monday 2026-10-12 10:00 Eastern
(EDT, UTC-04:00). The active worker was restarted with about 28.67 hours remaining.
The scheduler ceiling is temporarily 40 hours; the launcher restores its normal
14-hour ceiling on completion. IgnoreNew prevents the regular Sunday 20:00 trigger
from starting a second writer. The exception expires by its absolute timestamp.
An in-flight passage may finish after 10:00 before publication; its model timeout
is 900 seconds. Chat/voice containers and the active release were not restarted.


## Worker recovery (2026-10-11)

The owner generator now retries transport/worker-exit/protocol failures and
HTTP/timeout/connection errors at most three attempts for the same passage,
with 2- and 4-second backoff. Exhaustion ends the pass without marking that
window complete. The Sunday launcher can resume the pass within its existing
deadline. Invalid generated note JSON and length-truncated answers remain
retryable source windows; they are not transport retries or completed notes.
Worker stderr is retained in ignored data/study-notes-worker.log. No original
passage or generated answer is added to retry diagnostics.

Owner generate/answers/publish CLI operations share an OS-released writer lock;
status remains read-only. This prevents concurrent updated CLI writers, not
arbitrary external SQLite writes or processes that loaded older script versions.
An already-running generator must restart to adopt these changes. Model requests
retain their 900-second timeout; a hung WSL transport is not independently timed
out by the owner pipe reader. This is bounded worker-failure recovery, not a
complete service supervisor or inference scheduler. Chat/background priority
still requires a separately prepared gateway integration.

## Read-only progress report

Run `python scripts/notes-health.py` from the owner checkout. It reads the build
SQLite database in read-only mode and at most the last 2 MB / 200 parsed log
events. It reports committed windows, retained notes, age of the newest saved
window, successful-request median, and recent worker errors/retries. It does
not print original passages, generated notes or answers, call Ollama, publish
notes or alter the active release.

`recent_progress` means a saved window is less than three minutes old;
`needs_check` means progress is older or missing, not that a worker is proven
stalled. A newest error/retry produces `recovery_or_failure` until a saved-window
event follows. `unknown` means no build database, and read/schema errors report
`unavailable`. This is not a live process/GPU check. Timing covers only successful
requests in a bounded log tail; it is not an ETA, retention-quality score or
comparison against the superseded five-fact format.

## Cooperative chat priority

The gateway chat and compression routes and the owner generator share OS locks
in ignored data/inference-admission. A waiting interactive request reserves
priority; the generator cannot begin another passage ahead of it. One admitted
request holds inference until completion or failure. Process death releases OS
locks; no stale-file deletion is required. Existing auth, input filtering, MCP
routing and output DLP remain in place. No new model tools, ports or mounts.

An in-flight passage is not preempted. The gateway waits up to 60 seconds for
admission, then returns HTTP 503 with Retry-After: 5 and keeps browser conversation
state. STOP/disconnection does not immediately cancel an admission wait. Continuous
chat can starve background work. This coordinates updated gateway chat/compression
and generate only, not arbitrary Ollama clients, owner probes or the separate
answers CLI. Both the gateway release and restarted generator must adopt it;
a source edit alone does not change an existing process.
