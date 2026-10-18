# Precision and uncertainty for mathematics and quantum mechanics

See [the post-workload behavior plan](BEHAVIOR_TUNING_PLAN.md) for baseline
evaluation, reviewed examples, held-out tests and conditional fine-tuning gates.

The Mathematician and Quantum Mechanics Professor base prompts now require
relevant assumptions, explicit separation of published explanation from attempted
derivation, and a concise verification status for substantive calculations/proofs.
This remains active across skill changes without changing conversation history.
Simple conceptual answers need not become lengthy checklists.

Status labels are source-supported, reasoned checks only, partially checked and
unresolved. Each must name the checks actually performed and what remains missing.
Source support is not proof verification. Model-written confidence percentages,
fabricated tool use and claims of independent verification by another pass of the
same model are prohibited by the prompt. This is behavioral guidance, not a
guarantee of correctness or a mechanical output enforcement layer.

Mathematics emphasizes regularity, quantifiers, convergence, boundary conditions,
existence versus uniqueness and local versus global conclusions. Quantum reasoning
emphasizes states, operators, units, conventions, approximation regimes and the
distinction between theoretical/simulation results and experimental evidence.

Eight cases extend `evals/companion.json`: discontinuous pointwise limits, ODE
nonuniqueness, incorrect integration, unsupported limit/interchange certification,
unnormalized probabilities, evolution-sign errors, degenerate perturbation theory
and exaggerated experimental claims. Each includes expected correction and an
uncertainty/verification rubric. `python scripts/evaluate-companion.py` validates
the catalog; `--live` collects model responses for manual scoring and consumes
inference. No live GPU evaluation was run during the continuous notes workload.
Catalog/configuration tests do not establish that the model catches these errors.

For manual assessment score assumption identification, technical correctness,
premise correction, verification honesty and useful next steps from 0 to 2 each.
Record failures separately; an invented verification claim is a critical failure
regardless of total score. Do not reward verbosity or generic uncertainty language.
The existing under-120-word mechanical check is informational, not a passing gate
for these derivations. Local symbolic/numerical verification tools remain future work.

Broker prompt hashes were regenerated in the working checkout. Active frozen
prompts, release receipts and model/voice settings are unchanged. This feature
requires release preparation and activation before it affects the deployed personas.
