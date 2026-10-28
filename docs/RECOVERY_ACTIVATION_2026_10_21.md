# Recovery and owner tools activation — 2026-10-21

Owner requested progress to production and a check for reasons not to proceed.
Fresh prepared-pin, model-selection and serving-health checks found no blocking
failure for the scoped candidate. Retained static warnings were disclosed before
activation. This authorization does not arm recovery or enable owner-data backups.

## Result

Activated `b6dffca22d244953acb3a8574c232e69` through
`python scripts/releases.py activate b6dffca22d244953acb3a8574c232e69`.
The command exited 0 in 29.016 seconds; no rollback was required.
Previous `042f91c0a1454887a694c945f49237ad` is retained for rollback.
Gateway PID is 48508 and no pending cutover remains.

Fresh post-cutover checks verified frozen payload/deployment/voice/scan pins,
all required readiness checks, generation-bound health receipt, idle broker
readiness and a successful HTTP 200 `/api/personas` response. The old payload's
hashes and model/CPU voice images and start times match the pre-update snapshot;
both dependencies remain running. Authentication, isolation and DLP readiness
checks pass. This is not new rendered-HUD, physical microphone, second-device,
live answer-quality or comprehensive security acceptance.

The scanner retains the same 11 reviewed MCP warnings (HIGH, score 66), with
69 clean skills across 70 completed targets. Station health remains degraded
because of that retained warning. The warning is not a restart instruction.

## Availability evidence limitation

The sampler used unsupported `/api/catalog`, producing 66 HTTP 404 responses,
43 startup HTTP 503 responses and two connection failures across 111 observations.
It had no successful baseline/final HTTP 200 sample, so it cannot establish the
service interruption duration. The 29.016 seconds is whole-command time, not
downtime. This was a gateway replacement with brief rebinding, not zero downtime.
LAN tabs need a fresh login; their saved conversation state is preserved by the
existing session design, not independently browser-verified during this rollout.

Private logs and receipts are under `data/recovery-production-20261021`:
`activation-before.json`, `activation.log`, `activation-result.json`, and
`activation-verified.json`. Preparation failures and scan evidence remain retained;
see the [prepared source scope](RECOVERY_PREPARATION_2026_10_21.md).

## Reasons to hold further expansion

- Automatic recovery remains disabled; production observation and arming gates
  have not been completed. No supervisor was started or installed.
- Backup key custody is undecided. Backups remain synthetic-only, with the chosen
  D: destination and three-calendar-month retention plan.
- Human claim-support review and live quality/latency comparisons are incomplete.
  No answer-quality or latency improvement is claimed.
- Execution profiles and MCP Skills remain excluded from this active payload.

Source was committed locally as `6a53304`, merged into main as `b6201f2`.
No GitHub push was performed as part of this activation.
