# Owner notes observability
Goal: inspect committed progress and bounded timing/error logs without inference.
Constraints: keep nightly work/chat/voice running; preserve privacy; no activation/commit.
Inputs: read-only build database and bounded local log tail.
Outputs: owner notes-health CLI, scoped docs, regression tests.
Done when: missing database, successful timing, stale progress and error recovery tested;
real report returns committed counts without changing the running release.
Choice: stdlib read-only CLI rather than a new HUD/API or service dependency.
Result: three tests pass; live report returned recent progress; no GPU requests.
Next: gateway/background cooperative admission with interactive priority; separately
stage, prepare and activate. In-flight requests cannot be promised instant preemption.
