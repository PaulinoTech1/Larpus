# Interaction consequences and event review

Reviewed 2026-10-11. This is a code-backed consequence analysis, not a claim that every scenario occurred. First order means the immediate effect; second and third order mean effects propagated through another boundary or operating practice. The complexity ledger explains what each boundary costs; this document explains how those costs combine.

## Propagation chains

| Trigger / first-order effect | Second-order consequence | Third-order consequence | Evidence and status |
| --- | --- | --- | --- |
| Chat arrives while notes inference is active; broker cancels the notes socket. | The current notes window remains pending and generation may be repeated. Cancelled requests retain their reserved output budget. | Frequent chat can reduce notes progress and cause budget yields; estimates based only on raw tokens/second become misleading. | `runtime/broker_scheduler.py:Scheduler.slot/charge`; `scripts/study-notes.py:NotesWorker.request`. Mechanism confirmed in code; sustained starvation not measured. |
| An interrupted request cannot pass the bounded single-runner idle fence. | Scheduler becomes faulted; subsequent inference is refused rather than overlapping uncertain model work. | Chat and notes lose availability together, requiring owner investigation/recovery; blind retries cannot clear the fault. | Scheduler `faulted`, `verify_idle` and `cancellation_unconfirmed`. Intentional safety/availability tradeoff; no automatic reset claimed. |
| A notes response hits its output length limit. | The response is not saved as a completed window; later attempts can regenerate it. | A repeatedly difficult window can consume GPU time without increasing saved coverage, affecting completion estimates. | `scripts/study-notes.py:generate`, `done_reason == length`; observed truncation on Oct 11, but repeat-window frequency not quantified. |
| CPU semantic retrieval fails or misses its deadline. | `_hybrid` returns the original lexical ordering. | Chat may remain healthy while evidence selection changes; service uptime alone can hide a quality regression. | `runtime/knowledge.py:_hybrid`; fallback tests exist. Current fallback catches broadly and does not emit the new diagnostic ID. Follow-up: report degradation without exposing question/passages. |
| Context budget is consumed by conversation plus selected evidence. | Evidence selection is constrained, or context pressure asks the owner to compress. | A validated but lossy summary may omit nuance; missing evidence can change answer confidence despite a large nominal context window. | `runtime/knowledge.py:augment`, `runtime/context.py`, `runtime/inference.py:chat`. Original browser transcript is retained; summary is not permission or source truth. |
| DLP or GPU placement checks reject a streamed response after some checked text was emitted. | The client receives an error and marks the reply incomplete; it does not add a successful assistant turn. | Previously displayed or spoken checked text cannot be recalled; the owner can have heard an incomplete argument. | `runtime/inference.py:chat`, `web/app.js`, `tests/chat-stream-ui.cjs`. Incremental screening is not a guarantee about the semantics of an unfinished answer. |
| A new snapshot fails preparation/readiness or cutover. | Preparation leaves the old snapshot intact; failed cutover attempts restore the prior gateway. | Port rebinding and new gateway sessions still interrupt LAN access; owner may need to log in again even after rollback. | `scripts/releases.py:prepare/cutover/start`, `docs/UPDATES.md`. Rollback is application recovery, not recovery from host/driver failure. |
| Authored complexity baseline permits existing large functions. | Gate catches growth beyond allowances, but does not prove a component earns its keep or catch all difficult interactions. | Treating a green gate as design approval can preserve expensive debt indefinitely. | `scripts/complexity.py:regressions`, `config/complexity-baseline.json`. Review value, failure evidence and operational cost separately; do not reset allowances mechanically. |
| Diagnostic cause chains reach a working owner stderr sink. | Failures become correlatable without raw exception messages. | Operator diagnosis improves, but omitted message details and broken sinks can still leave uncertainty; logs are not a durable host crash recorder. | `runtime/diagnostics.py`, focused privacy/protocol tests. Bounded frames and IDs only; no new persistent event service. |
| Windows stops during GPU-backed notes processing. | Gateway, WSL, model and voice can all become unavailable; in-flight generation has no completed-window receipt. | Application rollback cannot restore host state; progress estimates must distinguish saved coverage from time spent on discarded work. | Incident below. Whole-host common cause is confirmed; GPU causation is unproven. |

## What to measure next

Use existing notes/broker logs and saved receipts before introducing another monitoring service. Track completed windows per wall-clock hour, truncation/retry counts, preemptions, cancellation-fence failures and retrieval degradation alongside chat latency. Compare foreground responsiveness against background completion time. Mark missing observations as unknown, not zero. No new counters for retrieval degradation or a durable event timeline are implemented in this documentation change.

Review routing and retrieval first: their branching crosses admission, evidence, context, filtering and streaming. Keep tests at those contracts while extracting clearer responsibilities; deleting security checks merely to reduce complexity is not a valid improvement. CPU voice and CPU retrieval also share host resources with WSL/inference; CPU core isolation and voice latency under sustained load remain measurement questions, not inferred guarantees.

## Recorded Windows shutdown during GPU workload

The following is a sanitized transcription of the owner-local incident review captured earlier on Oct 11. It has not been independently reconstructed from the inaccessible dump. Raw logs, minidump and private corpus remain ignored and are not published.

| Recorded event | Evidence / interpretation |
| --- | --- |
| 16:18 Eastern: notes generation reached the 6000-token output limit. | Length-truncated output was refused and left retryable. This is an application event, not evidence it caused the later bugcheck. |
| 16:39:07 Eastern: Event 6008 reports the previous unexpected shutdown. | Conflicts with later notes timestamps. Do not use this alone as the exact crash instant. |
| 16:57:02.951 Eastern: last saved note receipt in the captured review. | A committed result predates the reboot; generation after that may not have been saved. |
| Notes launcher retries through 17:15:40 Eastern. | Earlier generic OSError obscured transport detail. These records make the shutdown timestamp uncertain; clock/buffering explanations are hypotheses. |
| 17:17:07 Eastern: boot recorded after bugcheck 0x3B, first parameter c0000005. | Confirms a Windows kernel crash/access violation, not a model-only exception. |
| WER System event 1019 names Ntfs.sys as possibly related. | Driver attribution is preliminary. The dump stack is required before identifying a responsible driver or root cause. |
| Post-boot review: gateway stopped, WSL stopped, scheduled task Ready. | Ready does not mean the workload is executing. No automatic restart was performed during review. |
| Saved database: 3184 done-window rows, 30568 notes; read-only SQLite quick_check returned ok. | Checks the examined database structure, not losslessness, every filesystem or all owner data. At that review 3147 completed keys matched the 13105-window queue; 9958 remained. Historical snapshot, not current progress. |

The reported local minidump could not be opened by the review process; no permissions were changed and no dump was uploaded. Reviewed six-hour System events did not show WHEA, storage/display or resource-exhaustion evidence supporting a particular cause. Absence in that bounded review does not exclude hardware, GPU, RAM, storage or filter-driver faults. Boot NTFS health reports for the examined volumes were healthy; this is not a full disk test.

Hypotheses remain distinct: kernel/storage/filter-driver involvement is plausible from the preliminary Ntfs mention; RAM/hardware instability remains unresolved; application transport failures were observed but have no established causal link to the bugcheck. Neither out-of-memory nor GPU failure nor disk corruption is established.

Next incident work: preserve the original dump, obtain authorized local elevated debugger analysis, correlate its stack/time with Windows and WSL/container records, and capture resource observations for any owner-authorized sustained restart. Do not run repair tools or reset the model merely to test a guess. The new diagnostics were added after the event and cannot retroactively supply its missing cause chain.

## Validation and release status

The complexity implementation committed as `89df1b5` had an isolated suite of 205 tests OK (two skips), plus HUD checks. This consequence review is static analysis and documentation. No new failure scenario, workload restart, prepared scan receipt or production activation is claimed. Private incident evidence remains in owner-local data. At this review the commits were local. They were subsequently pushed; the implementation was later activated. See [STATUS.md](STATUS.md) and [UPDATES.md](UPDATES.md) for current dated state and later live evidence.
