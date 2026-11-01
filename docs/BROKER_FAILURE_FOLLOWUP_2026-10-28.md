# Broker refusal and local speech follow-up - 2026-10-28

## Assessment and current evidence

The owner reported: "Local inference is busy or held by the broker. Retry
shortly; no direct fallback is used."

That exact message comes from `runtime/inference.py` handling `BrokerRejected`.
It maps several different refusal codes to one display message. The gateway
preserves a structured code in ordinary HTTP failures and streamed error events,
but the HUD's old `failureText` displayed only the generic text. The reported
message alone does not identify queue contention, a budget limit, a model switch,
a cancellation-fence failure, or a policy refusal. Root cause remains unknown;
no contemporaneous refusal code or broker snapshot was supplied.

Fresh checks after the report found:

- Active release: `1022de11b0df4ce6be2915f49f1286ba`, previous
  `882c959c3d4540a5ba4b4b89f1596b17`.
- Served JavaScript includes the one-line speech completion fix and no faulty
  `children.at(-1)` lookup. This confirms deployment of that fix.
- Local streaming chat released 40 characters and a done event in 12.0 seconds.
  No broker refusal or output hold occurred in that one request.
- Health reported the selected model online and GPU resident, and voice, input
  filtering, output DLP, MCP surface and egress checks passed. Overall health
  remained degraded for the existing scanner-evidence warning. Health is a
  periodic monitor, not a guarantee for every subsequent request.

Confidence: High for the deployed DOM fix, successful single-request observation
and ambiguous UI error handling. Low for a cause assigned to the earlier broker
refusal; that cause has not been established.

## Targeted correction

The HUD now displays the allowlisted broker code and distinct instructions:

| Broker code | Meaning and operator response |
| --- | --- |
| inference_budget | Per-lane rolling request/token reservation limit; wait for the budget window and retry once. |
| queue_full | Two waiting chat slots are already occupied; let current work finish. |
| admission_timeout | Waiting for the generation slot expired; inspect active work before retrying. |
| cancellation_unconfirmed | Readiness/cancellation fence was not confirmed; inspect broker state. Repeated retries may not recover a faulted broker. |
| inference_deadline | Generation exceeded its bounded lifetime; inspect broker state before retrying. |
| model_switching | A model switch is in progress; wait for it to finish. |
| broker_held | Another broker refusal was intentionally generalized by inference; investigate rather than assuming a transient queue. |

Unknown codes retain the existing error text. Correlation IDs remain restricted to
16 lowercase hexadecimal characters. No automatic retry, direct model fallback,
new HTTP route, extra MCP tool, model change, larger quota, weaker fence or reduced
DLP/isolation check is introduced. Held or partial replies remain excluded from
history and speech is cancelled on failure.

This corrects ambiguous failure presentation. It is not a claim to fix an
unreproduced scheduler/model fault. The new UI diagnostic is a repository change;
it needs a separately prepared/activated release before appearing in production.

## Read-only incident diagnosis

From ordinary owner PowerShell in the project, run:

```powershell
python scripts/broker-status.py
```

The command selects the active release's agent, uses its existing private status
socket through WSL/Podman, and prints admission metadata only. It submits no chat,
does not change model state, clear faults, restart services or inspect reply text.
It rejects invalid release/container identities and oversized or malformed status.
A WSL denial, unavailable socket or timeout returns failure rather than success.
The restricted Codex Windows token cannot perform this live WSL check here.

Preserve the displayed broker code, request time and this snapshot before another
attempt. `active`, `waiting_chat`, `faulted`, preemption and confirmed-recovery
counts distinguish normal contention from a generation fault. A later healthy
snapshot cannot retroactively prove the cause of an earlier refusal.

If `faulted` is true, do not blindly retry or clear the flag. First confirm no
active generation, whether an owner notes writer is still using an old release,
model residency and the selected broker/container identities. A scoped owner
recovery may restart only the selected pinned broker after those checks, retaining
the mandatory readiness/cancellation fence. No such recovery was performed during
this investigation because the fresh chat succeeded and the fault was not shown.

## Other failures kept distinct

1. Browser speech cutoff: HTMLCollection has no `.at`; the active release now
   uses `lastElementChild`. A stricter mocked DOM regression reproduces the
   original failure and verifies successful completion/history/speech behavior.
2. Repair-bundle newline conversion: an earlier whole-file comparison failed.
   The corrected bundle's safety check passed in the owner run.
3. Provenance stage failure: isolated source lacked `research/catalog.json`.
   Adding the matching reviewed input restored exact provenance equality without
   rebuilding or losing metadata. See the [speech repair report](SPEECH_CUTOFF_REPAIR_BLOCKER_2026-10-28.md).
4. Output DLP: the latest inspected incident matched the application root.
   `/app` substring matching also flags a synthetic `/application-notes` string.
   This establishes a possible false-positive mechanism, not that the owner's
   specific held reply was harmless. No DLP rule or quarantined record was changed.
5. Broker refusal: the report lacked a specific code; a fresh chat completed.
   Do not attribute it to MCP skill discovery or declare a persistent broker
   outage from the generic message alone.

## Verification and remaining limits

Focused diagnostic formatting tests cover every allowlisted broker code, unknown
and prototype-like names, valid and invalid correlation IDs. The streamed-chat
regression covers a coded broker refusal after partial text, no saved partial
history, stopped speech and no automatic replay. All configured Node UI suites
are run on the candidate files. The owner status-command tests mock WSL and cover
active-release selection, read-only command construction, malformed identities,
malformed/oversized responses and process failure.

Live owner WSL status, physical audio playback, a reproduced original broker
refusal and deployment of the new diagnostic UI remain unverified. No full
security-audit or sustained availability claim follows from these checks.
