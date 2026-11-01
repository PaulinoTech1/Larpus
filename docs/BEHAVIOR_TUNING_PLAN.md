# Post-workload behavioral improvement plan

Status: proposed experiment, not training started. Initial scope: Mathematician
and Quantum Mechanics Professor on the shared local Qwen3.5 27B model.
Document knowledge remains in retrieval. Generated study notes are not automatically
training examples, answer keys or verified proofs. Preserve the single-model design.

The [teacher–student pilot](TEACHER_STUDENT_PILOT.md) maps the owner-selected Codex
teacher to separate mathematics/quantum topic lanes and reviewed feedback. Its
balanced 156/36/48 family split supersedes the initial 160/40/40 proposal below.
The later [Grok Bot teacher loop](GROK_TEACHER_TUNING_LOOP.md) changes the proposed
teacher for the next experiment and defines its execution receipts and gates.

## Desired behavior

| Target | Desired response | Failure to measure |
| --- | --- | --- |
| Missing assumptions | Identify the decisive missing domain, regularity, state, boundary condition or convention; ask only when needed, otherwise make an explicit conditional assumption | Silent assumptions or needless clarification for a complete problem |
| Applicability | Check the theorem hypotheses or approximation regime before applying the result | Correct-looking calculation using an inapplicable theorem or zero-denominator approximation |
| False premises | Identify the false step and provide a correction, counterexample or useful alternative | Agreeing with a plausible but invalid conclusion |
| Checks | Use relevant dimensions, normalization, limiting/boundary cases, substitution or differentiation; state the checks actually performed | Irrelevant checklists, fabricated tool execution or treating a numerical check as proof |
| Verification status | Separate sourced explanation, attempted derivation, reasoning checks and unresolved steps | Unsupported certainty, invented confidence percentages or blanket uncertainty on settled results |
| Evidence qualifications | Retain assumptions, version scope, exceptions and correction status from retrieved passages | Dropping conditions, mixing authors or presenting an older scoped result as universally current |

## 1. Finish and freeze a baseline

After the continuous notes workload ends, verify pending keys are zero and that
publication succeeded. Preserve build notes and originals. Supplemental originals
need separate retrieval admission; publishing their notes alone is not enough.
Validate source identities, quotes, provenance and index bindings before preparing
a candidate release. See UPDATES.md; never edit active frozen files.

Record exact model artifact/hash, quantization, runtime, context size, prompt hashes,
retriever/index hashes and sampling settings. Start with the current untuned model
and the precision prompts. Run the eight existing cases in evals/companion.json
as a smoke test; their public exposure means they cannot be a clean held-out test.

## 2. Diagnose before collecting training data

Separate missing/wrong retrieval, incorrect extracted equations, reasoning errors,
lost qualifications and response-format failures. Check PDF equation extraction
against originals: training cannot repair corrupted input. Improve retrieval or
prompts first for defects they explain. Measure both fixed supplied evidence and
end-to-end RAG so retrieval changes do not masquerade as model improvements.

## 3. Create a small reviewed behavior dataset

Proposed pilot: 240 distinct problem families, 120 per persona, balanced across
the six targets. Split families before generating variations: 160 training,
40 development and 40 locked test families, evenly divided between personas.
Include complete valid problems, missing-assumption cases and false-premise cases.
Do not train the model to reject every question or request assumptions unnecessarily.

Author concise input/evidence/answer examples with an explicit explanation of the
decisive step and actual checks, not long imitation thinking traces. Each record
needs an ID, persona, target, family ID, difficulty, evidence and its qualifications,
expected correction, review status, reviewer/date and source/license provenance.
Keep answer keys separate from prompts and candidate responses. Synthetic examples
must be checked; the same model's agreement is not independent review.

Use independently checked references, hand-verifiable examples or genuinely executed
local symbolic/numerical checks where appropriate. Retain check scripts/results and
their limits. Advanced proof items without adequate independent review stay excluded.
Never infer authorship from bibliographies or import library-loan content without
appropriate permission. Keep private examples and reports ignored by Git.

Split by mathematical construction, theorem/application and physical setup, not
random paraphrase. Hold out parameter changes and problem templates with their
families. Corpus overlap with source explanations is acceptable for grounded tasks;
overlap with held-out questions or answer keys is leakage and must be reported.

## 4. Compare prompting against a bounded tuning pilot

First score the untuned baseline and an improved-prompt baseline. Train only if a
recurring behavioral weakness remains and the reviewed examples target it. Prefer
a small supervised adapter experiment before more complex preference/reward training.
Start with one candidate and a fixed development budget; use development results
to choose settings without repeatedly consulting the locked test set.

The served Q4 artifact is not assumed to be directly trainable. Validate compatible
base weights, tokenizer, model license, adapter support and eventual inference/export
format separately. Owner previously verified a fitting 4-bit approach, but no local
training throughput or production-ready toolchain is established by this plan.
Run a short measured pilot before estimating duration; reserve CPU capacity for
voice, avoid swap dependence, and do not replace the active model as a side effect.

## 5. Evaluate the candidate honestly

Compare baseline, prompt-only and tuned candidate with identical supplied evidence,
retrieval snapshots and inference settings. Also compare the actual exported Q4
candidate: an unquantized training checkpoint's score is not deployed acceptance.
Use three responses per held-out family to expose variability; report family counts
and repeated outputs separately, never treating repeats as independent questions.

Review assumptions/applicability, technical correctness, premise handling, checks
and verification honesty, and evidence qualification retention. Score each 0-2;
report each target and persona separately, with concrete failures. Blind model
identity where feasible. Automated labels can check formatting and simple calculations,
but an LLM judge alone cannot establish proof correctness.

Proposed promotion gates, to be reviewed before test execution:

- At least 10 percentage points improvement in satisfactory behavior across
  held-out families over the stronger baseline; show paired outcomes and uncertainty.
  This is a pilot decision threshold, not a universal benchmark.
- No observed fabricated verification/tool-use claims and no new critical wrong
  derivation presented as verified. Zero observed failures is not proof of zero risk.
- No observed regression on ordinary valid questions, source qualifications or
  historical/corrected-source cases; expand evaluation where a small sample is ambiguous.
- Run a separate held-out regression set for the other personas, including useful
  direct answers, voice-friendly responses and eccentric-but-respectful pushback.
- Record latency, output length and memory costs. Longer explanations do not count
  as stronger reasoning; improvements must justify their operating cost.

If the result is ambiguous, keep the baseline and improve data/evaluation. Once a
test set informs further training decisions, retire it as a locked test and create
a fresh one. Do not tune against failures then claim an independent test improvement.

## 6. Release only a candidate that earns its keep

Retain the original model, adapter, dataset manifest and evaluation receipts.
Model replacement requires its own scoped maintenance plan; ordinary application
activation does not guarantee uninterrupted GPU replacement. Prepare compatible
application/prompt updates through stage/prepare/activate, preserve open HUD chat
contracts, perform owner acceptance and retain rollback. No training, installation,
model replacement, deployment or commit is authorized merely by this plan document.

Success means more reliable measured behavior while keeping traceable knowledge in
RAG. It does not establish general theorem-proving ability or mathematical expertise.
