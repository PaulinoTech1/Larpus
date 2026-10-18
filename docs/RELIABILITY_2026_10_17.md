# Reliability followups - 2026-10-17

Implements the first four approved recommendations in PROJECT_REVIEW_2026_10_17.md.

## Conversation-preserving sign-in

Newly loaded HUD tabs show an in-page password form when an API request returns 401. Transcript, unsent prompt and compression record remain in the same page memory. Signing in clears the password field and refreshes status; it never resends a chat, compression or model-switch request automatically. The owner reviews the retained draft and submits explicitly. Saving chats remains opt-in, with no new server or browser persistence.

Initial login and explicit Lock Station retain their existing navigation. Password verification, cookie settings, rate limits, local bypass, TLS and network bindings are unchanged. Sign-in also refreshes the model-connection header after a partial boot.

Already-open tabs retain their previously loaded JavaScript. An old LAN tab can still redirect on 401 during this first update. Preserve any unsaved conversation before activation; use the new HUD after that. Local HTTP retains its existing password-free behavior.

## Verification gate

The notes builder now separates note processing from its bounded owner transport/retry adapter. Retry, background yield, truncation, append windows and per-result producer attribution are retained. No complexity allowance was increased. The checkout's canonical isolated test entrypoint now reaches and runs unit discovery.

`scripts/ui_checks.py` is the single nine-suite list consumed by public CI and owner release preparation. It includes model switching, session recovery, diagnostics and speech normalization alongside the existing voice/chat/context/memory/teaching checks. Any suite failure stops the pipeline. Hosted CI execution remains unverified until separately requested commit/push and an actual run.

## Model recovery

Failed model operations write a bounded correlation record containing phase, operation ID, fixed active/target model IDs and a safe error category. The shared diagnostic stream retains reviewed literals, exception types and numeric subprocess return codes while omitting arbitrary command output, prompts and secrets. The HUD's recovery error includes the diagnostic ID. A failure to save the additional diagnostic file cannot stop restoration.

The owner recovery command prints final state and returns nonzero if recovery did not succeed. Successful restoration of a previous model remains distinguishable from loading the requested model. No model/voice image or runtime dependency was replaced.

## Scope and evidence

The release candidate starts from the active frozen payload and includes only these fixes plus the owner note-helper dependencies and their tests. Unrelated knowledge/persona changes and the checkout's owner screening-exception configuration are excluded. The added reference helper has no exception configuration in this candidate and retains strict rejection without it.

The fresh code reviewer found one minor header-refresh issue, which was reproduced and corrected. Checkout tests initially passed 283 cases with two existing skips; a further diagnostic-storage regression was then added and passed. All nine Node suites and prompt-hash approvals passed. Staged preparation and live delivery evidence will be appended after they run. Mocked recovery failures do not establish live GPU fault recovery. No rendered browser or physical microphone acceptance has been performed.

## Delivery result

Activated release `a4b76072c191467b86de8dac5eced963`; previous `c67982159d99487d8635f362ae673407` is retained. The owner confirmed the full LAN conversation was saved/exported before activation.

Final checkout verification passed 284 Python tests with two existing skips. The candidate passed its isolated Python suite, all nine Node suites, isolation probes and 70 complete scan targets, retaining the same 11 MCP warnings. The real temporary HTTP fixture verified new HTML/script delivery, expired-session rejection and restored access after login. The owner live broker preemption/chat/resume harness passed on 3.8.

The first snapshot `f179fad026074b7bb84b3faa51e80941` must not be activated: an additional HTTP check caught a missing template panel after standard preparation. Source was corrected with explicit UTF-8 handling and a required-element/script-order regression; the corrected snapshot was prepared afresh. Frozen payloads and scan receipts were not edited. Rejected execution containers were stopped by normal post-activation pruning and retained on disk for diagnosis.

Post-activation checks confirmed serving HTTP 200 for the new panel and script, CA-validated LAN unauthenticated rejection (401), ready 3.8 with full GPU placement, and only the retained security-scan health warning. Model and CPU voice image IDs/start times remained unchanged. Gateway listeners briefly rebound and old LAN sessions need a new login; this was not zero downtime. Existing saved chats remain in their origin's local storage and can be loaded explicitly.

No commit/push, physical browser acceptance, live GPU failure injection or factual-answer/latency comparison was performed. The last two review recommendations remain subsequent work.
