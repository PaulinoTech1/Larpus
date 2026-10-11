# Reliability first
Goal: unattended notes recover bounded transport failures and prevent duplicate writers.
Constraints: preserve source quotes/progress, active gateway/model/voice and Sunday deadline;
no model changes, downloads, commits or live benchmarks during notes.
Inputs: existing owner notes CLI, nightly scheduled task and committed SQLite windows.
Outputs: recoverable worker, stderr diagnostics, writer lock, tests and scoped docs.
Done when: recovery/limit/lock tests pass, existing notes tests pass, active station stays up.
Approaches: launcher-only restart is small but loses diagnostics and may repeat systemic errors;
owner worker retries + lock (~100 lines, stdlib) keeps exact pending window and bounded retries;
full queue service adds deployment/migration complexity. Choose owner worker + lock.
Chat priority is next: shared gateway/background admission, no claim of preemption.
Model policy: retain one general model; evaluate specialist weights only on held-out tasks.
