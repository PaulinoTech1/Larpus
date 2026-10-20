# Conversation repetition investigation, 2026-10-18

The owner supplied five consecutive replies that copied the same closing
paragraphs, repeated advice after corrections, substituted list-price assumptions
for a stated promotion, and made unsupported interpretations of feelings. The
inspected HUD submit path appends each completed turn once. The inference path
preserves alternating history and attaches retrieval data only to the latest
question. No duplicate-submit or repeated-history insertion defect was found in
those inspected paths; this is not proof covering every browser state.

## Corrections

- Shared system guidance prioritises the latest update, treats old assistant
  replies as context rather than a writing template, honours corrections and
  ruled-out advice, and permits requested repetition or recaps.
- All twelve personas make humour optional, removing the instruction to add a
  deadpan remark most of the time. Constructive factual pushback remains; mocking
  feelings or dismissing learning goals is discouraged.
- Ordinary chat uses broker-owned `repeat_last_n=4096` and
  `repeat_penalty=1.1`. Notes and summary templates retain their existing sampling.
  These options are added after strict client/lane validation; the model and HUD
  cannot supply arbitrary inference options. Bodies/options are copied rather
  than mutated. Model files and GPU placement are unchanged.
- The generated broker prompt hashes include the shared guidance and revised
  persona templates. The prompt allowlist and client schemas remain enforced.

The [official Ollama parameter reference](https://docs.ollama.com/modelfile#valid-parameters-and-values)
documents the repetition window and penalty controls. The selected values are
an experiment validated locally, not a guarantee against semantic repetition.
They influence generation rather than deleting or rewriting output paragraphs.

## Evidence and rejected candidates

The small norms continuation probe advanced exercises before this change. It
did not reproduce the owner's longer loop. A bounded fixture extracted from the
reported conversation seeds repeated advice/closing paragraphs and the owner's
latest constraints; it is not the full original transcript.

The first prompt-only candidate stopped the copied closing but still scolded the
owner. The second revised-persona replay copied the dishwasher ending again.
Both were rejected for activation. A further release check rejected the second
candidate because an existing test required the phrase “Challenge flawed
assumptions”; the final wording preserves that contract without restoring the
cutting-wit instruction. Partial evidence remains unchanged on disk.

Candidate `df8ac524f6dc4306be3f1865223ced85` preparation descendants were
identity-checked before cancellation; production was untouched. Candidate
`d25fbc04405b4d928f3e94aa83628ee1` failed preparation and was never activated.
Two intermediate staged-only sampling candidates were not prepared or activated.

The final candidate is `b029d94bfc9b43f8a3ab30c38ddad78a`. The local isolated
suite passed 317 tests with two skips and an explicit zero exit status. Candidate
preparation passed its narrower frozen-payload suite, UI and isolation checks.
Scoped review found no blocker in persona changes, prompt hashes or sampling.

Four owner-only candidate inference probes completed through the approved broker:

| Probe | Observed result |
|---|---|
| Extracted reported-loop fixture | Copied dishwasher and token-friction closing paragraphs absent. Still challenged the stated promotional price and offered more tasks; broader answer quality remains imperfect. |
| Follow-up explicitly declining more tasks | Three relevant sentences about unused capacity and reduced effort, no new task list or joke, no copied closing. |
| Euclidean norm of (3,4), two-sentence limit | Correct value 5 in two sentences. Citation identifier was present; entailment was not independently audited. |
| Explicit verbatim repeat request | Repeated `The Euclidean norm of (3, 4) is 5.` exactly, without extra words. |

These are a small behavioral sample, not a guarantee against future copied
phrasing or semantic repetition. The initial result also demonstrates that the
change does not resolve every source-grounding or conversational-quality issue.
The final streamed follow-up after activation also avoided both copied endings
and stayed within three sentences. It still characterised the feeling as a
psychological artifact of sunk-cost bias. That unsupported interpretation is a
remaining quality issue; the update should not be described as solving all tone
or grounding problems.

## Activation and availability

Release `b029d94bfc9b43f8a3ab30c38ddad78a` completed all 70 scan targets,
retaining the same 11 reviewed MCP findings and no skill warnings. It was
activated successfully without rollback. The whole activation command took
25.079 seconds, including validation, drain, readiness and pruning; this is not
measured listener downtime or a zero-downtime claim.

Post-activation checks verified both pipeline switches, Assembly selected and
used by the live reply, CA-validated unauthenticated LAN controls returning 401,
and passing functional station health. Overall health remains degraded solely by
the retained scan warning. GPU model and CPU voice container IDs, images and
start times matched the pre-update receipt. Bindings, authentication, model and
voice images, dependencies and owner data were unchanged. LAN sessions need a
fresh login after the gateway change; the existing HUD preserves the transcript
and draft. These are backend changes and do not require refreshing the HUD.

Availability evidence is in `progress-availability-before.json`,
`progress-availability-after.json`, `progress-activation.json`,
`progress-v3-prepare.log`, and `progress-live-followup.json` under
`data/assembly-linux-build/`.

Owner-local receipts are under `data/assembly-linux-build/`:

- `repetition-before.json`: simple norms continuation.
- `reported-loop-before.json`: bounded extracted baseline fixture.
- `reported-loop-candidate.json` and `reported-loop-candidate-v2.json`: rejected
  prompt-only behavior.
- `repetition_case.py`: private fixture definition.
- `superseded-progress-prepare-processes.json`: cancellation identity evidence.
- `progress-v2-prepare.log`: preserved release rejection.
- `progress-source-receipt-v3.json`: scoped overlay inventory, based on the frozen
  active payload with unrelated checkout changes excluded.
- `reported-loop-candidate-v3.json`: final candidate extracted-loop result.
- `progress-regression-probe.json`: follow-up, factual and requested-repeat probes.
- `progress-final-v3-tests.log`: final local suite with return code captured by
  the owner harness.
