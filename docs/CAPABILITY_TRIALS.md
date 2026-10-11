# Capability comparisons: prepare now, execute after study notes

This owner-only CLI compares two teaching profiles on the same authored questions.
It does not modify model weights, approve teaching profiles or measure the owner's
learning. No live trials or scheduled jobs were launched during this build.

The starter bank is linear algebra: four practice cases and four held-out cases.
Rubrics cover correctness, reasoning, teaching and grounding, each scored 0-2.
Problems and expected answers are authored; arithmetic was checked locally and
the conceptual references point to the approved Interactive Linear Algebra source.
This is not an independently validated benchmark. Review the bank before use.

## Offline preparation

From the checkout:

```powershell
python scripts/capability-trials.py validate
python scripts/capability-trials.py prepare --output data/evals/my-comparison.json
python scripts/capability-trials.py compare data/evals/my-comparison.json
```

Preparation defaults to v0's standard style versus the same settings with the
worked-example method. It writes an explicitly **deferred** artifact with no model
calls. Existing outputs are never overwritten by prepare. The initial artifact is
`data/evals/capability-linear-algebra-deferred-20261010.json`.

To use real profile versions, export the browser teaching journal, then prepare
with `--journal PATH --baseline v1 --candidate trial:2`. Versions and trial IDs
must belong to the bank's exact role/skill scope. The starter bank is scoped to
`mathematician|` (persona only). Other choices include `v0` and
`method:direct`, `method:socratic` or `method:worked-example`.

## Live execution is deferred

Wait until note generation for the **current source collection is finished**, not
merely until one night's task exits. Review the questions and scoring criteria.
Then prepare a frozen release containing the current code, corpus, embeddings
and published notes using UPDATES.md. Do not alter an existing frozen release.

The future owner-run command is:

```powershell
python data/releases/PREPARED_ID/scripts/capability-trials.py run data/evals/my-comparison.json --notes-finished --bank-reviewed
```

Both flags are explicit owner attestations. The tool cannot establish that every
source window was covered by the note builder. It additionally refuses execution
during 8 PM-10 AM Eastern (including DST), while the scheduled notes task runs,
or while a Python study-note generate/answers/publish process exists. An unknown
task/process state fails closed. It probes before every model call. A job could
still start after a probe; this is cooperative scheduling, not an exclusive GPU
lock or preemption. A call already running is not forcibly interrupted.

Live runs must use the existing sealed MCP route from a prepared release with an
unchanged payload. No direct Ollama fallback. Reports pin the frozen release,
source fingerprint, model configuration, approved library, embeddings and notes
manifests. A resumed comparison refuses different runtime/source pins. Preparation
does not activate a release or schedule a future run.

Each question starts a fresh conversation. Baseline/candidate order alternates
AB/BA. Rubrics, expected answers, references and other model answers are excluded
from the model prompt. The ordinary retrieval pipeline can still retrieve approved
sources. Progress is saved atomically after each response; process-local failure
leaves completed responses available. Re-running resumes missing responses, not
failed/held ones. Prepare a separate repeat to retry failures or finished runs.

## Manual review

Read answers and source previews from the private artifact. Score each arm against
the case's rubric, not against whether you personally prefer its style:

```powershell
python scripts/capability-trials.py score data/evals/my-comparison.json --case independence --arm baseline --scores 2 2 1 2 --reviewer boss --note "Correct relation; follow-up was too easy"
python scripts/capability-trials.py compare data/evals/my-comparison.json
```

The score order is correctness, reasoning, teaching, grounding. Reviewer and an
evidence note are required. Failed/held or empty responses cannot receive scores.
Existing reviews are retained rather than silently replaced. Results separately
show practice and held-out matched pairs, failed/held response counts, and mean
candidate-minus-baseline scores. Missing scores do not count as zero or as a win.

Small manual comparisons are descriptive observations. They are not blinded,
statistical significance tests, expertise certification or learning measurements.
Latency is retained per response, but GPU load can confound it. A capability gain
needs repeat trials, unfamiliar problems and owner review of tradeoffs.

Keep held-out cases out of study-note generation, tuning examples and prompt
iteration. They are outside the source catalog and skill files; existing note
generation does not consume this bank. Exposure of this starter bank means it is
not a secret test set. Add fresh cases for stronger future evaluation.

## Privacy and availability

Artifacts live in ignored `data/evals`; answers may include private source text.
Do not publish or commit artifacts. The versioned bank contains original problems,
rubrics and public source metadata, not downloaded source passages. No new source
hosts, downloads, dependencies, network tools or model permissions are added.
The CLI uses an owner-side per-artifact lock; it does not share a lock with notes.
No production bindings, active releases or note-generation jobs are changed.
