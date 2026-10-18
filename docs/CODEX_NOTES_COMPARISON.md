# Matched Codex and local-model note preparation

Owner authorized a matched pilot on October 14, 2026 rather than regenerating
the entire collection. This is inference comparison, not weight training. The
deployed runtime remains isolated; the owner explicitly shared selected passages
with the Codex session. No autonomous external bridge exists in the deployed
runtime. The later full snapshot run (below) was a one-time, owner-approved
exception: on October 15, 2026 up to 833 extracted library passages plus their
provenance were sent to OpenAI-hosted Codex (`gpt-6.1-sol`, tools/web/MCP
disabled) solely for comparison with LARPUS-generated study notes. The run was
stopped by the `STOP` marker at 21:40 Eastern on October 15 (652 complete, 181
manually approved, 3 failed, 2 bibliography-only of 13,737 windows). It must not
be resumed or repeated without a new owner decision; see DECISIONS.md.

An initial four-window smoke pilot uses two distinct completed mathematics sources
and two quantum sources. It freezes the existing facts-first prompt, original
passages, source identities, provenance, text hashes and completed-window keys.
Codex responses were saved before Qwen answers were loaded for comparison. Qwen
was not rerun and its notes database was opened read-only. No GPU interruption,
corpus replacement or production activation was performed.

Private files are in `data/evals/codex-notes-pilot-2026-10-14/`: inputs, independent
Codex output, quote checks, matched Qwen output, summary and side-by-side HTML.
All 31 Codex facts passed the existing grounding/text filter. That confirms only
the implemented checks, not claim correctness or full coverage. Exact model/backend
identity of this interactive Codex session was not independently verified, so do
not label this a measured 6.1 Sol API benchmark or compare its token throughput.

Selection takes the first suitable completed window per distinct source, two per
role, with 3,500–4,800 characters and at least eight saved Qwen facts. This biases
the sample toward previously productive Qwen windows and is not a random or
representative quality benchmark. The passages include severe mathematical OCR
damage. Refusing to reconstruct damaged equations is a legitimate outcome, not
automatically lower coverage or failure to meet a fact-count target.

At workload completion, review technical support, missing qualifications, unsupported
inferences, equation honesty, attribution, duplication and useful coverage against
the original PDF. Keep source-extraction failures separate from model failures.
Fact count is descriptive, not an accuracy score. Manual scores are unset. The
side-by-side output names models; a later rigorous evaluation should use blinded
reviewers, broader stratified sampling and independently checked answer criteria.

This pilot does not authorize replacing Qwen notes with Codex output or using either
as training ground truth. Expand only after reviewing the pilot methodology and
results. Preserve the original collection and running workload.

## Owner-authorized full snapshot run

After reviewing the pilot, the owner requested independent Codex notes for all
text in the existing Qwen workload and a larger comparison when LARPUS finishes.
Prepared October 15: 13,737 unique windows across 411 source identities, including
the two admitted textbooks and supplemental research. This is the extracted queue,
not every page image or every non-admitted downloaded original. No new sources
are silently added after the snapshot is frozen.

The private owner-side runner is `data/codex-full-notes.py`; its data lives in
`data/evals/codex-full-notes-2026-10-15/`. `prepare` freezes input SQLite, source
provenance, prompt and validation-code hashes. `run` invokes the installed Codex
CLI serially with requested model `gpt-6.1-sol` and low reasoning effort; `status`
reports progress. Successful notes use the same facts-first and grounding logic
as the local writer. Bibliography-only windows are labeled/skipped consistently.
The four interactive pilot outputs are not reused as verified-model full-run results.

The run uses existing owner authentication and sends each selected extracted
passage/provenance to hosted Codex. This is an explicitly authorized external
preparation exception, not a network path for the deployed LARPUS runtime. Shell,
browsing, apps and plugins are disabled; a separate working directory is used.
The CLI may still supply its own system framing, so this is matched evidence and
task specification, not an identical inference harness or controlled model-only
benchmark. Requested model/configuration and event/usage receipts are retained.

Independent output/result storage never writes the Qwen notes database or approved
index. Atomic SQLite claims and stable keys permit resumption. Create a file named
`STOP` in the run directory to stop after the in-flight call. Failed CLI requests,
unexpected tool items stop the run for review; rejected facts are quarantined by
window and never counted complete. There is no automatic
model fallback, quota-reset retry loop, credit purchase or new API-key provisioning.
Per-call timeout is ten minutes. Completed work remains saved if a run stops.

The first clean configured request completed with seven accepted facts. Preliminary
startup attempts are retained separately; one attempt exposed unwanted plugin
startup and was excluded before the plugin-disabled run began. Startup warnings
are retained in private logs. No comparison accuracy score is inferred from success.

The run is large and may exhaust account usage limits or take longer than the local
workload. Do not promise synchronized completion or uninterrupted quota availability.
At comparison time, intersect exact window keys/text hashes, report missing/failed
windows and skip/reuse differences, and separate clean-text from OCR-damaged cases.
Record prompt/configuration mismatches across the evolving Qwen run. Assess claim
support and lost qualifications as well as quotes; counts are not an accuracy score.
Technical quality scoring remains pending and requires original-equation checks.

### Three-worker extension

The owner authorized parallel Codex instances on October 15. The initial serial
run had six completed windows and one grounding-review window. Preserve that
review case rather than retrying it until it passes. Three owner-side workers now
claim untouched keys using SQLite `INSERT OR IGNORE` under a unique primary key.
Each writes only its claimed window; independent Codex sessions use unique output
files. WAL transactions serialize result writes. Review-required, failed and running
keys are not silently reclaimed or processed again.

Transport, authentication, quota, unexpected-tool or other worker exceptions create
the shared STOP marker. Other workers finish in-flight calls and stop before their
next job; no account rotation, quota bypass or automatic credit purchase occurs.
Validation failures stay as explicit review gaps while untouched windows continue.
A dead worker's stale claim requires owner inspection before any reset. Running
workers are recorded in the private PID list; they are not deployed station services.

Parallelism shares the same account usage allowance and may not scale linearly.
Measure accepted-window throughput across all workers before revising completion
estimates. The first concurrency contract checks unique claims across three SQLite
connections; sustained throughput and provider throttling remain empirical questions.
