# Fine-tuning drafts (Grok Bot teacher loop, round zero)

**DRAFT. Pending independent review. Not admitted or usable as training data.**
Authored 2026-10-22 (ET) by Grok Bot for the first bounded action in
[`docs/GROK_TEACHER_TUNING_LOOP.md`](../GROK_TEACHER_TUNING_LOOP.md): 12 synthetic
training families, one per topic lane in [`docs/TEACHER_STUDENT_PILOT.md`](../TEACHER_STUDENT_PILOT.md).

| File | Purpose |
| --- | --- |
| `grok-round0-families.draft.json` | 12 families (6 Mathematician, 6 Quantum), 29 variants: problem, synthetic student attempt, teacher critique, draft target, verification record, provenance, review and packet manifest |
| `verify_round0_families.py` | Executable sympy/numpy/scipy checks behind every target (one per family). Re-run owner-side: `python docs/finetune/verify_round0_families.py` |
| `verification-results.json` | Hosted-box run of those checks (tool versions inside) |
| `build_round0_families.py` | Regenerates the JSON from source text |

Location: the plan gives no path for teacher drafts. Its private run records go in
the ignored `data/evals/tuning/<run-id>/`. These drafts contain no private material,
so they are here. Admitted examples should be copied into that run's `data-manifest.json`.

Rules carried from the plan:
- Every `student_answer` is a synthetic stand-in. Replace it with a real
  round-zero student attempt before teacher review.
- All families are training split. No development or locked-test material exists here.
- `license`, `training_use` and `external_sharing_approval` are `null` until the
  owner decides. Check the current Grok/xAI terms for output and training rights first.
- Executed checks test the stated results. They are not general proofs.
  Families M6 and Q6 rest partly on hand arguments or model assumptions.
- Grok Bot's agreement is not independent review. Record reviewer, date,
  admit/reject reason and review minutes for each family.

## Round 1: dataset built to 28x (2026-10-22 ET)

**Still DRAFT. Pending independent review. Not admitted or usable as training data.**
Known content defect awaiting review: `grok-r1-opt-05/d` says a step size
`0 < alpha < 2/L` avoids divergence "on quadratics" without requiring a
lower-bounded/convex objective. That claim is false for an indefinite quadratic.
Do not admit this variant until its scope and target are corrected and rechecked.
Owner instruction relayed at 05:21 ET: "Stop the training and build out the data set... 28 times the current data set size."
The 12 round-0 families above are unchanged. They are now the first train family of each lane.

Target: 12 x 28 = **336 families**. The split follows the plan's per-lane rule (13/3/4 of 20, rounded to 18/4/6 of 28 per lane):

| split | families | written here | variants |
| --- | --- | --- | --- |
| train | 216 | 12 round-0 + 204 new (`families-train.draft.json`) | 29 + 538 |
| dev | 48 | 48 new (`families-dev.draft.json`) | 122 |
| locked test | 72 | **none: gap**, see `locked-test-spec.md` | — |

Each of the 12 plan lanes has 1 round-0 + 17 new train families, 4 dev and 6 reserved test slots.
| File | Purpose |
| --- | --- |
| `split-register.json` | Every slot's split, planned subtopic and status. Splits were fixed at 05:26 ET, before any new variant was written |
| `families-train.draft.json` / `families-dev.draft.json` | New families, same record schema as round 0. `reviewed_target: null`, review status `draft-pending-independent-review`, license, training_use and external_sharing_approval `null`, synthetic student attempts labelled as not LARPUS output, and a per-family `packet_manifest.family_sha256` |
| `verify_families.py` | One script with all 264 checks (the 12 round-0 checks plus 252 new). `python verify_families.py --json verification-results-round1.json` runs them. `python verify_families.py --data .` also cross-checks the JSON files: status, recomputed family hashes, and no test split |
| `verification-results-round1.json` | Box run (named so the round-0 `verification-results.json` is not overwritten): 262 pass, 2 hand-proof-only (`grok-r1-fa-13`, `grok-r1-open-16`, with proof sketches), 0 fail. Tool versions are recorded in the family files |
| `dedupe-audit.json` | Prompt-similarity audit (difflib >= 0.80 or 3-shingle Jaccard >= 0.5, against round 0 too) and core-problem audit. 6 template-only flags and 1 related core pair were adjudicated as distinct. Nothing removed |
| `locked-test-spec.md` | Spec for the independent author of the 72 sealed test families. Grok Bot must not write them |

Behaviour mix over the 660 new variants:
- false premise 177
- missing assumption 110 (16.7%)
- evidence qualification 111 (16.8%)
- practice hint 52
- direct answer 210 (tags)

Difficulty runs from intro to graduate. Kind `evidence_qualification` is new relative to round 0. It marks prompts that come with a clearly labelled synthetic excerpt whose qualifications must be preserved. New topics (linear algebra, probability, complex analysis, Fourier, proof technique, oscillator and scattering, angular-momentum addition, Born approximation, quantum information) were placed inside the existing plan lanes. Number theory has no plan lane and was left out, apart from induction as proof technique.

Same rules as round 0 apply: synthetic student answers must be replaced with real round-zero attempts, rights decisions are pending, and Grok Bot's agreement is not independent review.
