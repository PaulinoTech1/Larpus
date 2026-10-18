# Mathematics and quantum mechanics teacher–student pilot

Status: planning only. Owner-selected teacher: Codex 6.1 Sol. Student: the shared
local Qwen3.5 27B model. This supplements BEHAVIOR_TUNING_PLAN.md; it does not
replace RAG or authorize automatic training, external uploads or model replacement.
These personas are priorities because subtle invalid reasoning can sound convincing,
not because their difficulty relative to every other persona has been measured.

## Boundary and outcome

Target the six agreed behaviors: missing assumptions, applicability, false-premise
correction, meaningful checks, verification status and preservation of evidence
qualifications. Do not target broad factual memorization, novel research proofs,
unrestricted autonomous self-improvement or imitation of the teacher's personality.

The owner exchanges authored problems and explicitly approved reference excerpts
with hosted Codex. This is an owner-side external-processing exception, not an
internet connection for LARPUS. No automatic bridge, private corpus upload,
credentials, machine diagnostics or agent capability changes. Record what was
shared, teacher configuration/model identity where available and applicable source
permissions. No external exchange begins merely because this plan exists.

## Topic lanes

| Mathematician lane | Typical failure | Suitable verification |
| --- | --- | --- |
| Limits, continuity and convergence | Pointwise/uniform confusion; invalid interchange | Explicit counterexample and theorem hypotheses |
| Differentiation and integration | Missing domain/constants; invalid substitution | Differentiation/substitution with domain checks |
| ODEs and dynamical systems | Existence mistaken for uniqueness; local/global confusion | Substitute candidate solutions; check regularity and intervals |
| PDE boundary problems | Missing boundary conditions; nonunique solutions | Simple reference solutions, residual and boundary checks |
| Continuous optimization | Stationary point called global minimum | Feasible-domain, curvature and boundary/counterexample checks |
| Functional analysis | Operator/domain or completeness assumptions omitted | Reviewed definition/theorem applications; finite-dimensional contrasts |

| Quantum lane | Typical failure | Suitable verification |
| --- | --- | --- |
| States and measurement | Amplitudes treated as probabilities; unnormalized states | Inner products, normalization and probability sums |
| Dynamics and stationary states | Evolution sign, units or basis errors | Differentiate evolution; eigenvalue substitution |
| Spin and angular momentum | Wrong commutator, factor or convention | Small explicit matrices and stated units/basis |
| Perturbation and approximation | Nondegenerate formulas used at degeneracy | Denominator/regime checks; exact small-system comparison |
| Entanglement and reduced states | Mixed/pure confusion; exaggerated consequences | Partial trace, positivity and trace checks |
| Open systems and experiments | Unstated noise assumptions; simulation called demonstration | Physical consistency checks and scoped experimental evidence |

Start with hand-checkable problems. Graduate-level depth enters only where an
independent reference or qualified review supports it. Defer research-level proofs
and general infinite-dimensional operator claims when adequate verification is absent.

## Round zero: evidence before training

After the GPU notes workload completes, freeze the approved model/prompt/retrieval
baseline. Check equation extraction against originals. Run existing public precision
cases as smoke tests, then collect fresh student responses with identical evidence.
Label the failure layer: retrieval, extraction, applicability, calculation, evidence
interpretation or communication. Fix retrieval/extraction defects in their own layer.

## Reviewed problem-family design

Retain the proposed 240 families: 120 per persona, 20 per topic lane. Per lane,
assign 13 families to training, 3 to development and 4 to locked test; totals are
156 training, 36 development and 48 test families. This deliberately replaces the
earlier 160/40/40 allocation to balance the topic lanes. Cover all six behaviors
across lanes; do not assert that a small sample precisely estimates each combination.

Within training/development families, prepare variations for a valid fully specified
problem, a decisive missing assumption and a tempting incorrect premise where
mathematically meaningful. Test families use independently authored prompts and
answers. Keep alternate parameters, constructions and paraphrases with their family.
Never generate training variants from locked test questions or use test answers
as teacher context. Existing public evaluation cases cannot count as unseen tests.

## Teacher–student review loop

1. Student attempts the bounded problem using the selected evidence snapshot.
2. Teacher identifies the precise invalid or unsupported step and drafts a concise
   corrected answer, counterexample or justified request for missing information.
3. Independent reference/check plus owner review validates the problem, critique
   and correction. Teacher agreement alone is insufficient. Reject ambiguous items.
4. Store the reviewed target response, assumptions, decisive check, residual
   uncertainty, evidence qualifications and provenance. Keep the original student
   failure for analysis; do not indiscriminately train on incorrect answers.
5. Train only on admitted training families, evaluate on development families and
   compare the selected candidate once against locked test families.

Records retain IDs, persona, topic, behavior tags, family/split, prompt, permitted
evidence, student answer, teacher critique, reviewed target, verification artifacts,
reviewer/date and admission status. Target answers present a useful explanation,
not an imitation of hidden internal thinking or a ritual disclaimer. Correct direct
answers should remain direct. Admitting a correct result without enough evidence
is a separate failure from making an incorrect calculation.

Checks are performed owner-side in a dedicated development environment. Proposed
symbolic/numerical checks grant no new tool access to the deployed personas. Preserve
tool versions, tolerances and exact inputs. Numeric agreement can test a result but
does not establish a general proof, operator domain or physical approximation regime.

## Training and evaluation decision gates

Use one joint behavioral adapter experiment for both personas on the shared model,
with balanced examples. Do not create permanently separate persona models. Confirm
training/export compatibility and licenses before a short measured pilot. Do not
assume the served Q4 file is the training input. Schedule GPU maintenance separately;
preserve CPU voice and the original inference model/rollback.

Compare untuned, improved-prompt and tuned outputs with fixed evidence and matched
settings, including the exported quantized candidate. Evaluate fixed-evidence and
end-to-end RAG separately. Generate three outputs per locked family to examine
variation; score family-level outcomes rather than calling repeats independent tests.

Use a 0–2 rubric for each of the six behaviors, where applicable, plus a separate
technical-correctness assessment. Record not-applicable dimensions rather than
rewarding unnecessary checks. Blind candidate identity for review where feasible.
Report counts by persona/topic, critical errors, unjustified refusal and latency.
The existing public five-dimension rubric remains a smoke-test rubric; it does not
substitute for this six-behavior evaluation.

Promotion follows the parent plan's proposed improvement and regression gates.
Any fabricated execution/verification claim or new confidently incorrect derivation
blocks promotion pending review. A small observed improvement may be inconclusive;
keep the baseline if evidence is weak. Test other personas because the model is
shared. No score establishes general expert-level reasoning.

## Deliverables and sequence

1. Baseline receipt and error taxonomy after workload completion.
2. Reviewed dataset manifest, family split and verification artifacts.
3. Compatibility/rights receipt and measured short training pilot.
4. Paired baseline/prompt/tuned evaluation with a keep, revise or reject decision.
5. Separate authorized model maintenance and staged application release, with
   owner acceptance and rollback, only if the candidate earns promotion.

No honest total training-time estimate exists yet. Authoring and verification may
dominate the project; collect the first 12 training families, one per topic lane,
before estimating review effort. If those families cannot be checked reliably,
reduce scope rather than scale up teacher-generated material.
