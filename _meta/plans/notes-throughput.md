Goal: faster future nightly coverage while retaining original author citations.
Owner revision: prioritize nuance over speed; target 8-15 distinct facts per
substantive passage, fewer only where evidence is sparse. Keep citations and
deduplication; increase note-only output ceiling and leave truncation retryable.
Constraints: no GPU trials, no active release edits/restart, no second note writer,
no deletion of existing notes, no model/context/dependency changes or commit.
Inputs: approved source windows and resumable build database.
Outputs: concise quoted facts, same-source exact duplicate reuse at each locator,
and per-request Ollama timing/token measurements.
Done when: mocked and offline tests cover duplicate attribution, nonduplicates,
legacy notes and errors; configured isolated tests pass.
Choice: retain window keys and database schema; reuse identical same-source windows
by copying existing grounded records with the current locator. No fuzzy filtering.
Alternative: paragraph rewriting/filtering risks removing qualifications.
Alternative: smaller model/context needs live benchmarks and maintenance planning.
Facts-first omits new summaries and prepared Q&A; originals remain retrievable.
Do not rerun completed windows. Future scheduled checkout invocation picks this up;
an already-running process retains its loaded code. Existing launcher publication
is retained; publication does not activate a production release.
AgentDB is unavailable; local plan records the contract.

Validation: 159 isolated tests passed, one skipped; four focused tests passed again
after enforcing facts-only retention. No live GPU requests were made. Offline
inventory: 12,095 pending windows, 46 exact duplicates (0.38%).
