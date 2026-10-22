# Grok Bot teacher loop for LARPUS

Status: executable **plan**, not a training or deployment receipt. Proposed 2026-10-22.
The later owner decision in `DECISIONS.md` selects Qwen3.8 27B and expands the
round-1 register to 336 families. The 72 locked-test families remain unwritten;
the train/dev drafts remain unreviewed and are not admitted training data.
This specializes [behavior tuning](BEHAVIOR_TUNING_PLAN.md) and the
[teacher–student pilot](TEACHER_STUDENT_PILOT.md). The owner's new choice of
Grok Bot supersedes that pilot's Codex teacher choice for this experiment; its
review rules and math/quantum scope remain in force. The later 336-family register
supersedes the pilot's 156/36/48 split for this round.

## Identity and outcome

**Student to be fine-tuned:** the owner-selected Qwen3.8 27B trainable checkpoint,
corresponding to the shared local `larpus3.8:27b-q4` inference
model used by all 12 LARPUS personas, initially evaluated through the
Mathematician and Quantum Mechanics Professor personas. It is one model, not a
separate model per persona. The Q4 Ollama tag identifies today's inference
configuration; it does **not** identify a trainable checkpoint, an adapter or a
trained candidate. Before training, record the exact served digest and confirm
the compatible trainable base, tokenizer, license, adapter and export route.
Until those checks and a training receipt exist, **no LARPUS model has been
fine-tuned by this loop**. Browser teaching profiles, prompts, RAG and study
notes are distinct from weight updates.

**Target behavior: evidence-first adaptive tutoring.** Give a useful direct
answer for a clear request. In practice mode, elicit the learner's attempt and
ask one focused question or give a hint at a time; use a worked example when
the learner is stuck or asks for one. Identify decisive assumptions, theorem or
approximation conditions, and false premises. Preserve source scope and
exceptions. End substantive derivations with an honest verification status and
the checks actually performed. Never invent execution, citations, independent
proof, credentials or professional experience. Keep ordinary answers concise
and voice-friendly. This is a conditional behavior, **not** a rule to turn every
request into a Socratic exchange.

The six measurable targets remain missing assumptions, applicability, false
premises, meaningful checks, verification status and evidence qualifications.
Factual knowledge stays in approved retrieval; tuning must not memorize a
private corpus or compensate for missing/wrong passages.

## Assumptions and decision boundaries

| Assumption | Status | Impact if wrong | Validation |
| --- | --- | --- | --- |
| Grok Bot can work from a curated, owner-approved problem packet without receiving the private LARPUS corpus, chats or logs | Unverified for this run | Cloud disclosure or unusable teacher context | Inspect each outbound packet and record approval, destination and rights before exchange |
| The downloaded Qwen3.8 27B checkpoint can be exported into a faithful served artifact | Unverified; weights and tokenizer downloaded, export untested | Adapter cannot be served faithfully | Record base/tokenizer digests, license and one short local round-trip pilot |
| A recurring behavioral error remains after prompt/retrieval corrections | Unverified | Weight tuning adds cost without fixing the actual defect | Run the frozen baseline and label failures by layer |

Grok Bot is a hosted agent. This plan gives it **no** access to the live gateway,
Ollama, private files, credentials, raw source library, browser memory or owner
conversations. Its existing repository access does not authorize sending source
content to its model. Use authored synthetic problems and excerpts explicitly
cleared for external processing; `training_use: allowed` alone is not an
external-sharing approval. Check the current service terms for training/output
rights before importing any Grok response into a dataset. If this boundary
cannot be met, hold the teacher step and run a local-only version of the same
review loop. No automated cloud bridge or unattended upload is part of the plan.

## Grok Bot execution loop

The owner or a local operator controls the private workspace and executes
student inference, validation and training. Grok Bot performs the bounded
teacher tasks on approved packets and maintains the non-private planning record.

1. **Freeze round zero.** After the notes workload is finished, capture release
   ID, model tag and digest, quantization, runtime, context, persona/skill prompt
   hashes, retrieval/index/notes hashes, sampling settings and source catalog.
   Run the existing public precision cases only as smoke tests. Collect fresh
   student attempts with fixed supplied evidence and separately through normal
   RAG. Label each failure as retrieval, extraction, applicability, calculation,
   evidence interpretation or communication. Repair upstream defects first.
2. **Build a reviewed problem-family register.** The current round-1 register
   reserves 336 distinct families: 168 per persona, 28 per topic lane, with 18
   train, 4 development and 6 locked-test families per lane (216/48/72 total).
   Split before generating variants.
   Keep paraphrases, changed constants and the same theorem/physical setup in
   one family. Independently author test families and seal their prompts, keys
   and hashes from Grok and training. Existing public cases are not unseen tests.
3. **Send a bounded teacher packet.** For each training/development family,
   provide only approved problem text, permitted evidence excerpt and the
   student's answer. Grok returns: the precise unsupported or invalid step;
   a corrected, concise target answer; assumptions; a decisive check or
   counterexample; source qualifications; uncertainty; and behavior tags. Do
   not request hidden chain-of-thought or a generic long explanation. Record
   teacher product/model identity if available, date, prompt version and packet
   digest. Do not send locked test material.
4. **Admit or reject locally.** A reviewer compares the teacher's correction
   with an independent source, hand proof or executed check. Record exact
   commands, tool versions, inputs and limitations for any calculation. A second
   LLM's agreement is not independent proof. Reject ambiguous, unsupported,
   rights-unclear or privacy-violating examples. Preserve the original student
   error for diagnosis, but train only on reviewed target responses. Keep the
   private record and artifacts under ignored `data/evals/` or another approved
   ignored path; never commit private packets or answer traces.
5. **Try the cheaper control.** Compare the frozen untuned baseline with an
   improved prompt/teaching-profile control on the development families. Train
   only if a persistent error remains. First make a small supervised adapter
   pilot, one candidate and a fixed development budget. No preference/reward
   loop or recursive self-training in this pilot. Record GPU/CPU memory, elapsed
   time and voice contention; stop if it disrupts the active station.
6. **Evaluate the exact exported candidate.** Compare untuned, prompt-only and
   tuned/exported-Q4 arms using the same evidence, retrieval snapshot, runtime
   settings and prompts except for the deliberate treatment. For each locked
   family, obtain three outputs per arm; score at the family level, not as three
   independent cases. Blind arm identity for human review where feasible. Use
   the six 0–2 behavior ratings when applicable plus separate technical
   correctness. Record not-applicable dimensions, unjustified refusal, critical
   errors, source support, first-text and completion latency, tokens and memory.
   Run fixed-evidence and end-to-end retrieval analyses separately, plus an
   other-persona regression bank with direct-answer and voice-friendly cases.
7. **Keep, revise or reject.** Use the parent plan's proposed gate: at least a
   10 percentage-point family-level gain over the stronger untuned/prompt arm,
   with paired outcomes and uncertainty; no observed fabricated verification
   or new critical confidently wrong derivation; no observed regression on
   normal answers, source qualifications, security boundaries or other
   personas. A small sample or ambiguous gain means keep the baseline. If test
   failures guide another round, retire that test set and author a fresh locked
   set. Do not repeatedly optimize against the same holdout.
8. **Separate promotion from training.** Write a candidate decision receipt,
   retain original model and rollback artifacts, then seek a scoped model
   maintenance/release decision. Stage and prepare application changes under
   `docs/UPDATES.md`; no candidate, tag replacement, activation or automatic
   scheduled loop follows from this document. Validate the exported model in the
   actual local broker path before claiming LARPUS has a tuned production model.

## Required records and verification gates

Create one private run directory per round, e.g. `data/evals/tuning/<run-id>/`.
The operator's manifest must contain these fields, with `null` for unknowns:

| Record | Minimum fields and pass condition |
| --- | --- |
| `identity.json` | Run ID/time ET; student served tag **and digest**; training base/tokenizer/license digests; adapter digest; exported artifact/tag/digest; quantization; runtime/broker version; release ID. Never label the candidate “fine-tuned LARPUS” without a non-null adapter and exported artifact plus a completed evaluation. |
| `data-manifest.json` | Family IDs/splits and hashes; topic/persona balance; source IDs, rights and external-sharing approval; teacher packet/response digests; reviewer/date/admit-or-reject reason; overlap/leakage audit. Test answer keys remain in a separately access-controlled local file. |
| `train-receipt.json` | Local command/tool versions, parameters, seeds, start/end ET, resource samples, checkpoints, failures and final hashes. An absent training tool is a blocker, not a reason to fabricate a command or result. |
| `eval-receipt.json` | Baseline/prompt/tuned configuration pins; responses and references; blinded 0–2 scores with reviewer notes; correctness/critical-error counts; paired family deltas; first-text/completion distributions and resource cost; fixed-evidence versus RAG results; other-persona regression. |
| `decision.md` | Keep/revise/reject, gate-by-gate evidence, unresolved failures, owner review, candidate release/rollback IDs if applicable. Distinguish local experiment, prepared release and active production. |

Before each teacher packet, check privacy, rights and locked-test exclusion. Before
each training attempt, check admitted-only data, compatible artifact chain,
available resources and recoverable original model. Before any keep decision,
check independent answer review, leakage audit, exported-model results and
regression/latency evidence. Before production promotion, use the repository's
normal release, isolation, DLP, broker, authentication and health checks plus
owner acceptance. A green mechanical check never certifies mathematical proof,
student learning, all-persona expertise or production availability.

**First bounded action for Grok Bot:** prepare 12 synthetic training families,
one per topic lane, with teacher critiques and packet manifests; submit them
for independent review. Measure review yield and minutes per admitted family.
Only then estimate the work for a larger reviewed set or choose a smaller pilot. Do not
start GPU training, share private data or claim a model improvement at this step.
