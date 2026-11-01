# LARPUS large-baseline accuracy review and improvement roadmap

Review date: 2026-10-26 EDT. System under test: live release
`14911af1e4c249e7b125ad7441524f70`, `larpus3.8:27b-q4`, original persona
prompts, normal retrieval and 140,166 derived study notes. The protocol is
`data/evals/baseline/baseline-large-20261025-2135/PROTOCOL.md` (sealed SHA-256
`668264a5debac28eeb147365e0a543690aa421acd3c4c3f4d5e3714b205424bd`).
This review used a fixed, hash-recorded copy of 2,022 completed response records taken
at 10:14 EDT, SHA-256
`7ff8be1aa235d839de5f13ee2e48cd16af1631dc5ba7666549dac12bc254c653`,
under `data/evals/baseline-review-20261026-1015/`. The active runner was left
alone. At snapshot time 156 of 2,178 planned jobs remained; all 477 Phase A
jobs (dev, smoke and other personas) had completed three samples each. The
train split had 1,545/1,701 responses and is not held out. No locked set or
blinded human score exists yet. The baseline's own `baseline-report.md` was
older than this snapshot, so its displayed counts must not be used as final.

## Assessment

**Accuracy is not yet quantified.** The automatic checks detect phrasing,
length and number overlap; they do not prove technical correctness or citation
support. The independently recomputed, response-weighted dev checks show
25/123 direct-answer passes, 8/24 one-hint passes, and 98/102 false-premise
*cue* passes. Mean all-checks-pass across the 48 dev families is 61.3%. A
false-premise cue can pass even when the underlying correction is wrong. Target
number recall was 0.848 across applicable dev responses, but number overlap
also does not establish correctness.

The completed dev split had **91/366 (24.9%)** replies at the 1,024-token
output limit; smoke had 4/36. Of 366 dev replies, 261 emitted no citation,
102 had only recognized IDs, and 3 emitted an unrecognized ID. **46 dev replies
said “source-supported” while emitting no citation.** These are observable
format and grounding problems, not a 46-case proof of unsupported factual
claims. The gateway's citation check verifies identifier membership, not that
the passage supports the sentence. Other-persona cases are mostly mechanical
companion checks: 70/75 obeyed their under-120-word limit and none was
truncated, but those checks are not an accuracy certificate. Dev median client
completion time in the snapshot was 24.3 s; first text was 7.0 s.

### Manually inspected examples

| Case | Observation | Assessment |
| --- | --- | --- |
| `dev/grok-r1-opt-05/d`, samples 1–3 | All answer a general gradient-descent step-size question with smooth/strongly-convex advice but omit the bounded-below distinction and the `f(x)=-x²` counterexample. Sample 1 calls `1/L` theoretically optimal for the strongly convex case, which is not a general optimal-step claim. | High confidence: an essential condition is missing. For `f=-x²`, `L=2` and step `1/2` gives `x_(k+1)=2x_k`. A cited passage concerns *projected* gradient descent on a compact set, narrower than the answer's general claim. |
| `dev/grok-r1-pert-15/a`, samples 1–3 | Sample 1 opens by saying RWA is useless and predicts zero excitation, then derives the nonzero RWA formula before truncating. Sample 2 opens with the correct qualitative answer but prints conflicting derivation steps and truncates. Sample 3 truncates before a usable conclusion. | High confidence: sample 1's headline is false; all three are unreliable as delivered. Here `Ω/ω₀=0.02` and the resonant RWA gives `sin²(Ωt/2)` from the ground state. |
| `dev/grok-r1-ent-05/a` and `dev/grok-r1-open-20/a`, sample 1 | Long self-corrections reach 1,024 tokens before giving the requested partial-transpose spectrum or idle-gate infidelity. | High confidence: output limit made an otherwise answerable question unusable. |
| `smoke/quantum-mechanics-professor-expertise`, samples 1–2 | Both claim mixed states occupy the interior of state space; sample 1 abbreviates two citation IDs that the gateway cannot resolve. | High confidence: a rank-deficient mixed state such as `diag(1/2,1/2,0)` lies on the boundary. Full IDs in sample 2 resolve, but resolution does not validate that geometric claim. |
| `other/psychologist-expertise`, samples 1–2 | A clinical screening explanation cites a paper about selecting participants for a reverse-engineering study. | High confidence: the citation exists but is irrelevant to clinical diagnosis. The mechanical companion check does not catch this. |
| `dev/grok-r1-meas-05/a`, sample 1 | The Hadamard algebra is correct, but returned sources include algebraic topology and crash-safe file systems; the reply claims “source-supported” without citing a source. | High confidence: retrieval relevance and verification wording need attention even when the calculation is right. |
| `dev/grok-r1-lim-05/a` and `dev/grok-r1-fa-20/b`, sample 1 | Correctly treats ratio-test limit 1 as inconclusive and proves the proposed correlation matrix invalid via determinant `-0.62`. | High confidence: the baseline can produce concise, correct core reasoning in some cases; improvements should preserve that. |

These were targeted inspections, selected partly because they looked suspicious.
They are not a random sample or a measured technical-error rate. The reviewed
targets are useful comparators but were not treated as independent proof.

## Roadmap, in order

### 0. Finish and judge the baseline

Let the remaining jobs finish and record the final `eval-receipt.json`,
`env-end.json`, residency checks and any retries/holds. Run the predeclared
scorer only on the completed run. Have a reviewer use its independently drawn,
blinded 60-item sheet to rate technical correctness, citation support,
usefulness and critical errors. Audit the targeted cases above separately;
do not add them to the blinded estimate after seeing them. Keep dev, train,
smoke and other-persona denominators separate. No accuracy percentage or
release approval follows from the current heuristic score.

### 1. Trial a concise prompt before changing weights

Put the direct answer or decisive condition first. For practice requests,
give one hint without solving. Remove stock “boss,” decorative assumptions,
unasked questions, and verification boilerplate unless the prompt needs them.
Do not print abandoned derivations or claim a calculation was independently
verified when only mental algebra was used. A previously prepared prompt-only
v2 arm cut dev truncations from about 33 to 9 per 122 items and raised its
automatic direct-answer rate from about 25% to 69%, but its target-number
recall fell from 0.840 to 0.805 and it still missed `opt-05/d`'s bounded-below
condition and counterexample. Those earlier measurements are not a matched
comparison to this newer active release. Re-run the same completed Phase A
families, three samples each, on a prepared candidate with the *same* notes,
retrieval, model settings and safety controls. Judge correctness by review,
not output length alone. Keep the current active release until the candidate
passes its release gates.

### 2. Separate retrieval errors from reasoning errors

Build a fixed-evidence test arm outside the live chat path while preserving
authentication, Stegdetect, DLP, broker limits and GPU-residency checks. Compare
the original retrieval, corrected evidence/ranking, and concise-prompt arms on
the same families. Label evidence-in-user-prompt plus normal RAG as such; it is
not a no-retrieval arm. Review top passages for relevance by persona and task.
In particular, investigate unrelated top results for Hadamard, RWA and
clinical screening, and the mathematical notation corruption visible in some
PDF previews. Test whether notes, source-type priors or reranking cause each
error before changing the index. When no passage supports a claim, a
self-contained proof can be labeled as a derivation; it must not be called
“source-supported.”

### 3. Enforce citation validity and test claim support

The gateway already identifies unknown bracketed IDs but still releases those
answers. First make model-visible citation instructions use real IDs rather
than the literal `[source-id]` example that appears in `runtime/knowledge.py`;
the Zeeman reply copied that placeholder. Add a narrowly scoped response
check or bounded regeneration for unknown IDs, without bypassing DLP or
exhausting the broker budget. Do not treat a matching ID as supported: have
reviewers compare each cited sentence with its exact returned original
passage, including derived-note provenance. Test abbreviated IDs, copied
placeholders, irrelevant passages, and cited claims broader than the passage.

### 4. Add proof/calculation regressions for verified failures

Independently verify targets and retain counterexamples, not just expected
phrases: `-x²` and the missing lower bound for step size; the resonant RWA
formula and ratio `0.02`; Bell-state partial-transpose eigenvalues
`{1/2,1/2,1/2,-1/2}`; amplitude-damping idle infidelity near `1.67e-4`;
and a rank-deficient mixed state on the state-space boundary. Score the final
answer as delivered, including truncation and contradictory intermediate
steps. Use these known failures as regression tests; write new locked families
independently of the team that authored fixes. Include the other personas'
domain correctness, not merely their word counts.

### 5. Consider an adapter only after the above comparisons

If a behavior error persists with concise prompting and correct fixed
evidence, use independently verified, rights-cleared local examples to test
a small adapter. The existing pilot1 is not an evaluated candidate, and the
recorded xAI/Grok-output terms issue blocks assuming its Grok-derived targets
are available for training. Compare exported Q4 against prompt-only and
corrected-retrieval baselines on locked families. No privacy/DLP regression,
unsupported-citation increase, excessive caution, persona regression, GPU
residency loss or unacceptable latency/memory increase is acceptable.

## Release decision

No activation is recommended from this review. The next reviewable decision
is a prepared, concise-prompt candidate evaluated on matched Phase A and
independently written locked cases, with human correctness and citation labels.
The predeclared persona rule is a 3-point drop *and* a paired bootstrap CI below
zero; any safety failure is a regression. Keep the active release and rollback
path unchanged until that evidence is available and the owner approves a
cutover. Numeric latency and memory budgets still need to be set by the owner.

Primary local evidence: `data/evals/baseline/baseline-large-20261025-2135/`
(`PROTOCOL.md`, `items.jsonl`, `responses.jsonl`, `score.py`, `progress.json`),
`data/evals/baseline-review-20261026-1015/` (copied response hash and
read-only metrics scripts), and
`data/evals/tuning/prompt-control-r2-20261022-1754/summary.md`.
