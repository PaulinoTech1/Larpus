# Cooperative interactive inference priority
Goal: background notes yield between passages when chat waits.
Constraints: one GPU model; no new ports/tools/mounts/dependencies; retain deadline,
source grounding and progress. Keep production during tests/scans; staged activation.
Inputs: validated gateway chat/compression and owner NotesWorker requests.
Outputs: owner-host admission locks, concurrency tests, docs, prepared release.
Done when: cross-process ordering, timeout, crash release and exception release pass;
release gates pass; live gateway and updated nightly writer share admission.
Options: delay-only polling races; full queue service adds dependencies; two OS locks
coordinate current paths with bounded foreground wait. Choose two locks (stdlib).
Foreground holds priority while waiting for inference; background takes priority
briefly while acquiring inference, releases it for generation. No cancellation or
preemption of an in-flight passage; timeout returns retryable HTTP 503.
Scope: cooperating gateway chat/compression and generate only. Owner raw probes,
answers and unrelated model clients are not coordinated. No fairness guarantee
under continuous foreground demand. STOP during admission wait is not immediate.

Result: concurrency tests and complete preparation passed; activated 8ab6f566...;
live gateway priority, successful reply, LAN 401 and generator yield/resume verified.
Prior release retained, eight scan warnings retained; no physical browser QA.
