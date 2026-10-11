# Capability trials
Goal: compare teaching profiles on pinned questions, with explicit manual scoring.
User: "trials themselves will wait until after the gpu is done taking notes at night on the current data sources."
Constraints: no live trials, downloads, activation or GPU inference in this build;
keep running station/notes untouched; preserve unrelated edits and pending commit scope.
Inputs: authored linear-algebra cases, approved local reference metadata, teaching
journal export with exact scope and selected accepted/candidate versions.
Outputs: deferred immutable comparison plan; future resumable owner-only runner;
manual rubric scoring and matched before/after summary, practice vs held-out splits.
Done when: offline catalog/plan/score/compare and scheduling refusal tests pass;
reports have provenance and no inference occurs without explicit future opt-in.
Choice: standard-library owner CLI following evaluate-companion.py, ignored local
JSON artifacts, existing sealed MCP route. No GPU auto-grader or new HUD workflow.
Alternative: HUD batch runner adds long-lived HTTP jobs and cross-session state.
Alternative: autonomous nightly runs could compete with current note generation.
Prepare needs no model; run requires --notes-finished and --bank-reviewed, daytime,
no note worker/task, and a prepared frozen release. No automatic scheduled launch.
Balanced AB/BA ordering; fresh one-turn conversations, fixed bank and runtime pins.
Rubrics/answer keys never sent to the model. Manual results are observations,
not proof of learning or certified capability. No automatic teaching promotion.
AgentDB executable was unavailable in the preceding build; local contracts used.

Validation: 155 isolated Python tests passed, one skipped (private notes excluded).
All trial inference in tests was mocked. The prepared private artifact remains
deferred with no responses or authorization. A CLI run without confirmations
was rejected before inference. No live trial, scheduling, activation or commit.
Whole-checkout whitespace check retains an unrelated research/CATALOG.md EOF
warning; capability documentation changes passed the scoped check.
