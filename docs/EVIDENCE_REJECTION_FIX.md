# Optional study-note screening failure - 2026-10-16

Diagnostic `90dab2ce63d64c98` came from release
`5e8e07aab85b4484855be3af26c24b20`, at 21:31 Eastern on October 16. Its cause was
`TextHeld` in `knowledge.study_notes`, not `ContextPressure`. The generic error
incorrectly suggested shortening the question despite the separate context-budget
handler already providing its own response.

An owner-local sealed-agent retrieval probe reproduced the failure with the
owner's topology-learning question. A 610-character note field failed a completed
Unicode screening pass (`unicode_carrier_or_incomplete_scan`, scanner available,
`scan_complete=True`). This does not establish that the text was malicious; it
establishes that it was ineligible for the existing screened inference path.
The rejected field was retrieved evidence, not the user's prompt.

## Change

Screen optional derived notes individually. Exclude a note whose question, derived
text or original passage is rejected, log the fixed
`LARP-EVIDENCE-NOTE-EXCLUDED` diagnostic without source text, and continue selecting
eligible evidence. Preserve every original database and archived note.

Scanner unavailability and incomplete scans still raise. Missing or mismatched
database/manifest/provenance bindings still raise. User-message screening and
required original-source screening are unchanged. Context pressure still has its
separate 413 response; the general evidence error now describes library availability
or screening and no longer blames context size.

The unrelated reference-review work in the checkout also retains incomplete-scan
metadata rather than accidentally converting it into an ordinary rejection. Its
focused regression passes; that not-yet-active reference-review module is excluded
from this production candidate.

## Validation and rollout

The regression reproduced failure before the fix for all three note fields, then
passed with exclusion. It also checks scanner outage, incomplete scan, and database
integrity failures continue to propagate. The existing text-filter and diagnostics
tests pass. The separate candidate source passes its existing complexity gate;
unrelated study-notes complexity failures in the main checkout remain untouched.

Candidate `af32daffa60946ddbfc84f4377805f7d` contains only changes to
`runtime/knowledge.py`, `runtime/text_filter.py`, `runtime/diagnostics.py`,
`runtime/inference.py`, and the new note-rejection regression test relative to the
active release. It retains the preceding latency change and the same model, CPU
voice, approved library, bindings, authentication and shared dependencies.

The candidate's live sealed MCP test of the exact owner question returned status
200 with four references, including one eligible derived note, and an observed
note-exclusion diagnostic. Final model counts were 3,315 input tokens out of
131,072 capacity, 219 output tokens, and zero omitted messages. The initial test
reached first checked text in 20.100 seconds; a later instrumented direct-agent
probe reached it in 3.989 seconds. Those different timings do not establish a
latency improvement from this fix. The direct-agent probe excludes host MCP/HTTP.

Preparation passed application/HUD/isolation checks, exact MCP discovery and all
70 complete static-scan targets. The 69 skills were clean; the MCP inventory
retained the same 11 reviewed warnings. This is regression screening, not an
independent audit or a clean MCP scan.

The prepared-release live broker check passed: synthetic notes were preempted,
chat completed after preemption in 6.437 seconds, and notes resumed. Private
receipt: `data/evidence-rejection-broker-live.json`.

Activated `af32daffa60946ddbfc84f4377805f7d`, retaining
`5e8e07aab85b4484855be3af26c24b20` for rollback. No automatic rollback was needed.
The gateway drained and briefly rebound listeners; this was not zero downtime.
LAN sessions require a fresh login. The model and CPU voice retained five-day
uptimes and were neither replaced nor stopped. The already-stopped owner notes
writer was not restarted by this work.

After activation, the exact question succeeded through local HTTP streaming:
HTTP 200, completed stream, no error events, four references, 3,315 input tokens,
235 output tokens and zero omitted messages. First checked text arrived in 8.081
seconds and completion in 14.061 seconds; this is not a speed guarantee. Rejected
optional evidence was recorded separately as diagnostic `07e8011bb1be46d9`.

All required station-health checks passed. Overall health remains degraded for
the retained static warnings. CA-verified unauthenticated LAN API access returned
401. Private health/uptime receipt: `data/evidence-rejection-health.json`.
Physical-browser/second-device acceptance and an actual rollback were not tested.
Rollback remains `python scripts/releases.py rollback`. No commit or push occurred.
Private numeric receipt: `data/evidence-rejection-repro.json`; prompts and retrieved
text are omitted. No commit or push is requested.
