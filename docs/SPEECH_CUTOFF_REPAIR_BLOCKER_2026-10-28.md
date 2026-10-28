# Speech cutoff repair and provenance staging blocker ? 2026-10-28

## Update: speech repair activated; broker refusal remains under investigation

Verified later on 2026-10-28:

- Active release is `1022de11b0df4ce6be2915f49f1286ba`; previous release is
  `882c959c3d4540a5ba4b4b89f1596b17`. The active pointer was updated at
  14:24:14 Eastern. A fresh localhost request serves `lastElementChild` and
  no longer contains the faulty `children.at(-1)` lookup.
- Supplying `research/catalog.json` to the isolated source made provenance
  regeneration match the existing reviewed file exactly: 421 entries,
  310 dated, zero metadata changes, SHA256
  `21cd3d9873b5ec1e769fb2bac25b228151b65378ae0a1a973ac8fec32caec852`.
  The original provenance check passed. No metadata was rebuilt to weaken it.
- Version 3 retained a content pin on that catalog, ran the normal stage,
  prepare and activation flow, and excluded unrelated checkout edits. The
  general omission of provenance build inputs from release-source copies
  still warrants a separate release-contract correction.
- The owner subsequently reported the generic broker-held/busy message.
  A fresh streamed localhost greeting completed with text and done in
  12.0 seconds. This does not establish the earlier refusal's exact cause
  or prove sustained availability. See [broker failure follow-up](BROKER_FAILURE_FOLLOWUP_2026-10-28.md).

The remaining sections record the earlier failed repair attempts; their
pre-activation status statements are historical. Physical multi-sentence
speaker playback has not been verified by the engineering agent.

## Original goal and pre-activation state

Fix the browser error `$(...).children.at is not a function` and the resulting
mid-sentence speech cancellation. Deliver the fix through the normal frozen-release
stage, prepare and activate workflow. Preserve local-only operation, input/output
filtering, source provenance, isolation and unrelated checkout changes.

The owner ran `Repair-Larpus-Speech-v2.py`. Its application safety check and all
five focused Node UI suites passed. The script applied the two-file patch to the
checkout, then failed during staging. No candidate was activated. The selected
release remains `882c959c3d4540a5ba4b4b89f1596b17`; refreshing the HUD cannot
install a checkout-only fix. The currently selected frozen app still contains
the invalid lookup.

## Confirmed browser defect (High confidence)

`web/app.js`, function `attachSources`, calls:

```javascript
const host=$('messages').children.at(-1);
```

`children` is a DOM HTMLCollection, which does not provide Array.at. This is a
browser DOM failure, not evidence of an MCP child-process or skill-extension
failure. The done-event handler calls attachSources; its exception reaches the
chat catch handler, which stops voice playback and marks the reply incomplete.
The normal completion/history-save path is not reached.

The targeted fix is:

```javascript
const host=$('messages').lastElementChild;
```

`tests/chat-stream-ui.cjs` now models a messages collection without `.at` and
provides `lastElementChild`. It verifies that successful completion preserves
speech, saves history and renders references, while held/truncated streams retain
their failure behavior. Earlier tests used an Array for children and missed this
browser contract mismatch.

## Repair attempts and evidence

The original repair bundle had a Windows newline conversion error that caused its
whole-file safety comparison to reject the active app. The bundle was corrected.
Version 2 pins normalized reviewed application content, checks for exactly one
faulty lookup, and runs that check before copying the source or changing project
files. Its check passed in both a local check-only run and the owner's execution.

Owner v2 output reported these passes:

- Chat UI: incremental text/speech, successful history, held/truncated streams.
- Voice UI: mic selection, silence/review gates, pause/resume, speed, replay,
  cancellation and FIFO queue behavior.
- Speech text: Markdown, citations and author credits stripped.
- Execution controls: defaults, independent interaction and Diagnostic base.
- Diagnostic UI: valid correlation IDs shown; invalid IDs withheld.

These are mocked browser-state tests, not physical microphone/speaker acceptance.
Earlier live localhost checks returned a completed streamed chat (HTTP 200,
19.064 seconds) and a valid synthesized WAV (HTTP 200, 22050 Hz mono,
122099 frames / 5.537 seconds, 1.681-second request). They establish local backend
operation at that time, not successful playback or activation of the browser fix.

## Current blocker (verified)

The prepared source is:

`C:\Users\PS5Killer\AppData\Local\Temp\larpus-speech-repair-source-ehzd4c5b`

Owner execution stopped at `manager.stage(source)`, in
`scripts/releases.py`, before a new release ID was created. The stage method runs:

```text
python scripts/source-provenance.py check
Provenance drift; rebuild reviewed metadata before release
```

The check is functioning as a protective gate. It must remain enabled.

Read-only regeneration with `build(scratch_source)` found:

| Comparison | Result |
| --- | --- |
| Stored / regenerated entry count | 421 / 421 |
| Added / removed entries | 0 / 0 |
| Entries with changed metadata | 300 |
| Changed author / author-status fields | 300 / 300 |
| Changed metadata basis / evidence URL fields | 300 / 300 |
| Changed retrieval / snapshot fields | 297 / 299 |
| Index SHA256 binding | Identical |
| Scratch research/catalog.json | Missing |
| Checkout research/catalog.json | Present |

Both index bindings are
`88a7266477dd1bdd2e09f5e4e53405dfb7c6f8e8a041cedef3da6fe78e900388`.

## Leading explanation and next investigation

High confidence: the provenance builder reads `research/catalog.json` to populate
reviewed research metadata, but the release manager's fixed payload directory list
omits `research`. The repair deliberately copied the active payload to exclude
unrelated checkout changes, so its scratch source also lacks this input. Without
that catalog the builder can fall back to approved-index identities, producing
different metadata despite the same entry count and index binding. This explains
why a browser-only repair encounters an unrelated provenance check.

Unknown: whether adding a verified, historically matching research catalog alone
eliminates every difference. The current checkout catalog must not be assumed to
match the active provenance. The 300-entry comparison is not a determination that
300 production records are incorrect.

Next steps:

1. Identify and pin the reviewed catalog used to create the active provenance;
   compare it with the checkout catalog and all other builder inputs.
2. Re-run provenance generation read-only with the complete matching inputs and
   require equality with the reviewed provenance. Do not rebuild blindly from an
   incomplete payload or discard author/date metadata to obtain a passing check.
3. Decide the smallest release-contract correction so required provenance inputs
   are reproducibly available during staging/preparation. Test this contract.
4. Stage the isolated two-file speech fix with complete reviewed metadata inputs,
   prepare normally, inspect retained warnings, and activate only after success.
5. Verify that the served `/app.js` contains lastElementChild and no faulty lookup;
   refresh the HUD and complete a multi-sentence speech/references test. Check chat
   history persistence and confirm held/truncated replies still stop safely.

## Files and operational boundaries

Intended application patch: `web/app.js` and `tests/chat-stream-ui.cjs` only.
The owner run applied these checkout edits; unrelated changes remain outside the
repair candidate. No active frozen files, model settings, MCP permissions, filters,
provenance records or release checks were modified to bypass the blocker. No new
release activation or physical playback success is claimed.

The Codex session cannot write the E: project or invoke WSL with its restricted
Windows token. The owner PowerShell performed the repair attempt. This report is
staged in the existing temporary repair bundle for owner copying into docs.
