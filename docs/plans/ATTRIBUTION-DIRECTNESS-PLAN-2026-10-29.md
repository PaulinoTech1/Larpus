# Attribution and directness improvement plan (2026-10-29)

Status: **PLAN ONLY.** Written 2026-10-29 (evening ET) by Grok Bot. The checkout, releases and eval folders were read without changes. Nothing was run on the GPU. Nothing called the gateway or model, staged or activated a release, or committed. The study-notes job (PID 55828, `data/notes-new-sources-20261029/`) was not touched. No `*.PRIVATE.json` or `*.UNBLINDED.md` file was opened.

Owner request: "generate a detailed plan to reach those percentages. Make sure the plan is incremental has checks and validation."

This plan builds on, and does not replace:
- `docs/eval/BASELINE-LARGE-20261025-REVIEW.md` (scorer audit, root causes, ranked ideas)
- `docs/LARGE_BASELINE_ACCURACY_ROADMAP_2026-10-26.md`

`B/` below means `data/evals/baseline/baseline-large-20261025-2135/`. Row ids are `sample/group/family/variant` as in `B/scored-rows.jsonl`.

---

## 1. Summary table

GPU hours assume about 22 s per request, run strictly one at a time. That gives smoke 36 = 0.25 h, dev 366 (122 variants x 3) = 2.3 h, other personas 75 = 0.5 h, and the full legacy protocol 2178 = 13.5 h.

| Phase | Change (one per phase) | Primary metric | Target / gate | Est. GPU h | Owner action |
|---|---|---|---|---|---|
| P0 | Measurement validity: score v2, human calibration, rescore, re-baseline control C0, holdout dev, sealed protocol | Scorer agreement with human labels | Agreement >= 85% and Cohen's kappa >= 0.6 per v2 metric, or the human sample stays the gate of record | 5.3 | Label 50 citation + 50 direct-answer items (blinded). Approve C0 staging. Commission locked tests and persona sets. |
| P1 | Eval instrumentation: harness-only seed and `done_reason` capture | A/A identical-output rate; truncation measured by finish reason | Smoke A/A identical >= 90%, or fall back to 3 unseeded samples. Production behavior unchanged. | 2.8 | Approve the runtime change (PR) |
| P2 | Citation-id contract: remove the `[source-id]` placeholder from `EVIDENCE_PROMPT` and inject the allowed-id list | Invented-id share of emitted citations | <= 0.5% (baseline 44/1007 = 4.4%). Citing share not down by >= 3 pts. | 3.0 | Review PR |
| P3 | Server-side citation validator (normalize, strip or flag unknown ids). Optional bounded repair on the non-stream route only. | Invented ids reaching the user | 0 by construction. DLP order unchanged. Latency <= +5%. | 3.0 | Review PR (touches the release path) |
| P4 | Answer-first and length policy: port v2 rules onto C0, plus an applicability guard | Direct answer v2; truncation | Direct >= 70% at this phase (target 80% after P9). Truncation < 8%. Applicability no regression. | 2.5 (+2.5 if P4b) | Review persona-prompt PR. Blinded spot check (20 items). |
| P5 | Per-claim grounding rule: cite each externally sourced claim; "source-supported" requires a valid cite | Replies citing >= 1 valid id; human-calibrated support | Citing >= 60%. Support >= 65%. Uncited-factual v2 down >= 50% vs C0. | 3.0 | Decide whether "not covered by the provided sources" counts as compliant |
| P6 | Retrieval for spin and perturbation. 6a: CPU diagnosis. 6b: release with the 96 new QM/math lecture sources and notes. 6c: optional rerank/top-k/passage formatting. | Annotated top-5 passage recall; support and citing share in spin/pert lanes | Recall@5 for spin/pert >= 70% annotated. Overall support >= 80%. Citing >= 70%. Quantum vs math all-checks gap <= 5 pts. | 3.0 (+3.0 if 6c) | Approve the corpus release. Annotate 30 retrieval cases. |
| P7 | Fixed-evidence control arm, via existing `runtime/rag_eval.py` and `scripts/mtrageval_local.py` (measurement only, reported separately) | Support and directness with known evidence | Diagnostic only, no gate. Run at P0 and at Final. | (in P0 and Final) | Choose rights-cleared passages for spin, RWA and clinical-screening cases |
| P8 | Per-persona test sets for the 10 thin personas, written independently (no GPU until Final) | Coverage: >= 10 cases per persona | Sealed and hashed before Final | 0 | Write or commission the cases. Not authored by Grok Bot. |
| P9 | Contingency: answer-budget instruction and/or `num_predict` per answer type, only if truncation >= 5% or direct < 80% | Truncation; direct | Truncation < 5%. Direct >= 80%. Latency budget held. | 2.5 (contingent) | Approve the latency/VRAM budget change |
| Final | Confirmation on the full predeclared protocol with live security gates. Fixed-evidence and live-retrieval arms reported separately. | All targets + no-regression rules | All targets met on dev holdout and locked test. Zero safety failures. | 15.9 (+10.6 optional train) | Approve the Final protocol, then the push, merge and activation decisions |

**Total estimated GPU time:**
- Planned path: **38.5 h**
- With every contingency (P4b, 6c, P9): **46.5 h**
- With the optional train diagnostic in Final: **57.1 h**

At one batch per night (about 8 to 10 h), this is roughly 6 to 8 overnight windows. Phases never overlap with each other, with study-notes generation, or with training.

---

## 2. Targets, made measurable

All metrics are family-level means with paired family bootstrap 95% CIs: 5,000 resamples, seed scheme `20261025|group|metric`, as in `B/score.py`. They are reported for dev-tuning, dev-holdout (P0.5) and locked test separately. Legacy v1 numbers are always reported next to v2 and never silently redefined.

| Target | Definition under score v2 (P0) | Baseline 14911af1 (v1 heuristics) |
|---|---|---|
| Citation support >= 80% of emitted citations | Every bracketed citation occurrence, including duplicates, invented ids and malformed attempts. Support is judged against the **exact passage served** for that id and locator, not the last preview with that id. The gate of record is a human-calibrated label (P0). | dev 5.9% (family mean over citing families), 16/199 occurrences. Train 10.2%. |
| 0 invented ids | Any citation token not in that reply's returned source ids, after P3 normalization. Measured before and after the validator. | 44/1007 dev+train occurrences unresolved |
| >= 70% of tutor answers cite >= 1 source | Mathematician and QM replies where evidence was supplied (sources > 0). Strict: >= 1 valid id. Lenient (owner decision, Q3): or an explicit "not covered by the provided sources" statement. | dev 105/366 (28.7%), train 482/1701 |
| Uncited factual sentences cut >= 50% | v2 counts only claims that need a source: named results and theorems, attributions, author/year, empirical or historical claims, physical constants with values. Excludes display math, LaTeX lines, matrix rows, headings, list labels, questions and "Verification" lines. | v1: about 12.1 per reply. v1 is mostly derivation lines (see 3.3). |
| Direct answer >= 80% (excl. hint-only practice) | (a) The decisive result, or the false-premise/condition correction, appears in the first two substantive sentences, after stripping a pure acknowledgement such as "Right, boss.". (b) The reply was not truncated. Length is reported separately. Calibrated on 50 human labels. Note: none of the 41 dev / 177 train `direct_answer`-tagged variants carries `practice_one_hint`, so the exclusion is currently empty and becomes relevant only for new sets. | v1: dev 20.3%, train 23.2% |
| Truncation < 5% | `done_reason == "length"` from Ollama (P1 adds capture). Until then, `output_tokens >= 1024`. | 531/2178 (dev 91/366: QM 70, math 21) |

**Must-not-regress gates** (every phase and Final):
1. **Safety:** any DLP hold, privacy hit, or claimed-live-action failure on a candidate is a fail, regardless of CI. FAB regex flags are adjudicated by hand, since they have known false positives (`s2/dev/grok-r1-open-20/b`, `s2/smoke/quantum-experiment`).
2. **Behavior checks:** false_premise, missing_assumption, applicability and verification_status. Each fails if candidate minus control is <= -3 pts with the paired 95% CI entirely below 0. Applicability gets extra attention because v2 dropped it from 90% to 79% in `data/evals/tuning/prompt-control-r2-20261022-1754/summary.md`.
3. **Persona all-checks-pass:** the predeclared rule in `B/PROTOCOL.md` section 6, per persona.
4. **Latency budget** (proposed; owner to confirm, Q1): median completion <= 1.20 x control and p95 <= 1.25 x control. On 14911af1 the median was 22.48 s, so the cap is 27.0 s; p95 was 31.49 s, so the cap is 39.4 s. C0 values will replace these.
5. **GPU:** model at 100% GPU residency at every residency check, and minimum free VRAM >= 512 MiB (baseline minimum was 769 MiB). Any OOM is a stop.

---

## 3. Evidence behind the ordering (read-only analysis, 2026-10-29)

### 3.1 Invented ids come from our own prompt

`runtime/knowledge.py:EVIDENCE_PROMPT` (lines 33-59) tells the model to "cite its source IDs in brackets [source-id]" and gives the example "(Blackwell, 1956) [source-id]". The model copies it:
- `s1/train/grok-r1-ode-21/b`: "Chicone's exercise [source-id]"
- `s3/dev/grok-r1-opt-15/a`: "According to Treil (2017) [source-id]"
- `s1/dev/grok-r1-spin-15/a`: two `[source-id]`, zero resolved

Other invented forms, all in `B/responses.jsonl`:
- A real id with a prefix added: `s3/train/grok-r1-ent-18/c` `[source-mit-3c297b60-...]`
- Truncated hashes: `[mit-9c7d547b]`, `[mit-a316e95f]`
- A catalog-like slug not returned: `s1/train/grok-r1-meas-04/c` `[karamlou-quantum-simulation-...]`
- An author-year in brackets: `s1/dev/grok-r1-ode-05/a` `[Teschl, 2012]`

`runtime/inference.py:citation_check` (line 65) only labels these `unknown-identifiers`; the text is released unchanged.

### 3.2 Citations exist but rarely match the passage

Breakdown of 1007 dev+train citation occurrences, by lexical overlap with the preview:

| Category | Count |
|---|---|
| Supported (v1) | 121 |
| Near miss (>= 2 shared words or >= 30%) | 435 |
| Low overlap | 357 |
| Claim shorter than 3 words | 49 |
| Unresolved | 44 |
| Withheld | 1 |

Only 12 citations come directly after a sentence end, so sentence splitting is not the main problem. Patterns:
- **Whole-book citations for general facts not in the served passage:** `s3/train/grok-r1-fa-11/a`; `s2/dev/grok-r1-fa-15/a` (rank-nullity "(Treil, 2017)").
- **Standalone reference lines:** `s3/train/grok-r1-ode-12/a` "Reference: (Teschl, 2012) [teschl-ode-dynamical-systems]".
- **Citations inside "Verification/Checked" lines,** and hedged non-claims: `s2/train/grok-r1-ent-14/a` "No specific citation ... required ... but it aligns with ... [mit-439a28d3...]".
- **Irrelevant citations:** `s1/other/psychologist-expertise`.
- **v1 false negatives:** `s2/dev/grok-r1-meas-15/b` (the review notes the passage does list the phase gate).

Passage preview length: median 696, p90 1197, max 1199 chars. Some derived-note previews hold damaged PDF math, such as the Hatcher "/arrowext" glyph names.

### 3.3 Two v1 metrics measure length, not the target behavior

- **direct_answer:** of 98 dev failures, 97 fail only on the 250-word limit (59 of those are also truncated). All 408 train failures are length failures. Only 1 dev failure opens with a question. The median direct-tagged dev reply is 368 words. The check misses answer-first replies that run long (`s1/dev/grok-r1-spin-15/a` opens with the correct `1.16 x 10^-4 eV`). It passes non-answers (`s3/dev/grok-r1-spin-05/a` asks for the question again).
- **uncited_factual:** of 4,519 flagged dev sentences, about 89% are math/LaTeX lines, 67.7% contain only digits as math, and about 22% are list or heading lines (`### Case 3: $|x| = 1$`). Only about 3% carry a fact cue. Examples: `s2/dev/grok-r1-dyn-10/a` "$$ E = ... $$"; `s1/dev/grok-r1-fa-20/a` "1 & 1 & 0 \\". Shorter replies halve it mechanically: v2 prompt arms went from 12.1 to 7.0 per reply with no grounding change.
- **Openings:** about 79% of dev+train replies (1636/2067) start with a short sentence of 8 words or fewer with no math ("Right, boss.", "Understood, boss.", "Nudge received, boss."). Some are legitimate corrections ("No, boss."), so v2 treats a pure acknowledgement as non-substantive rather than as a failure.
- **Unbacked "source-supported":** 234 dev+train replies say "source-supported" with no citation (`s1/dev/grok-r1-meas-05/a`, whose sources were algebraic topology and a file-system paper).

### 3.4 Prompt v2 trades citations for directness

On the same r2 responses (dev), measured with the v1 heuristics:

| Metric | baseline -> v2 |
|---|---|
| direct_answer | 25% -> 69% |
| Truncated | 33.3 -> 9.0 per 122 (about 7.4%) |
| Median latency | 25.1 s -> 15.5 s |
| Replies citing | 29.9% -> 16.9% |
| Unresolved share of cites | 4/116 -> 13/93 |
| Support | 19.0% -> 12.9% |
| Applicability | 90% -> 79% |

So v2 alone cannot reach the citation targets. It must be paired with P2, P3 and P5 and an applicability guard.

### 3.5 Quantum lanes lack textbook-level sources

**Citing share by lane** (dev+train):

| Lane | Replies citing |
|---|---|
| Spin | 14% |
| Perturbation | 15% |
| Dynamics | 22% |
| Measurement | 22% |
| PDE | 25% |
| Optimization | 28% |
| ODE | 30% |
| Limits | 31% |
| Calculus | 32% |
| Entanglement | 37% |
| Open systems | 39% |
| Functional analysis | 46% |

**Corpus:** the quantum persona's library in release 1022de11 is 28 sources, all research theses or papers. Examples:
- `mit-84033887` many-body simulation
- `mit-d540fb86` superconducting qubits (Karamlou), which appears across every lane
- `mit-b61b51fa` spinor algebra, the top spin source (98 hits)
- `mit-cf01f99f` perturbation theory (66 passages)

There is no introductory textbook. Question-to-best-source word overlap is lowest for perturbation (median 0.40), and 16% of spin replies have best overlap below 0.2.

**What is coming:** the checkout already indexes 96 new lecture sources (`mit-805-*`, `mit-806s16-*`, `mit-806s18-*`, `tong-applications-quantum-mechanics`, `preskill-ph219-*`; 53 for QM, 43 for math; 81,511 passages). Their notes are being generated now. They are **not live** (DECISIONS 2026-10-29 5:42 PM entry). That is the natural single change for P6b.

### 3.6 What release 1022de11 changed vs the 14911af1 baseline

Changed:
- Added the Horizon input guard (`runtime/horizon_guard.py`, `horizon_worker.py`, `config/horizon.json`) and DLP input quarantine (`runtime/dlp.py:store_held_input`).
- `runtime/text_filter.py` +45 lines.
- Added `runtime/rag_eval.py`, `scripts/mtrageval_local.py` and the `fixed_selectors` plumbing in `knowledge.py`/`inference.py`.
- `approved.sqlite`: passages 76,850 -> 76,851, rejected 8,392 -> 8,416.
- **It ships `knowledge/notes.build.backup-20261015-pre-fixes.sqlite` inside the release** (tar 605 MB vs 413 MB).

Unchanged: persona prompts, `EVIDENCE_PROMPT` and the model.

`docs/BEHAVIOR_STAGE_PREP_2026-10-29.md` saw slower smoke latency on 1022de11 (completion 18.4-45.2 s; possibly GPU contention with notes or the guard). **Consequence:** the 14911af1 numbers are not a valid paired control for candidates built on 1022de11. P0 re-baselines.

---

## 4. Rules that apply to every phase

### 4.1 Privacy and rights
- No cloud API, telemetry, remote asset, hosted grader or new network path. Graders are this repo's local code, the already-installed local CPU cross-encoder used by `runtime/knowledge.py:_hybrid`, or humans.
- No training of any kind is part of this plan. The existing dev/train families are Grok-authored (package `owner-opt05-20261022-1311`). They may be used as **eval prompts only**: never as training targets, and never as grading truth beyond the owner-reviewed targets already recorded. Locked tests and persona sets must be written independently (`docs/finetune/locked-test-spec.md`), never by Grok Bot.
- Never open `B/blind-key.PRIVATE.json` or any `*.UNBLINDED.md`.

### 4.2 One change per candidate release
Each phase builds candidate `Cn` = last accepted candidate + one change.
- Build with `python scripts/releases.py stage --source <prepared tree>` and `python scripts/releases.py prepare ID`, as on 2026-10-25 (DECISIONS 8:58 PM entry).
- **Never** stage straight from the checkout until P6b. The checkout holds the uncommitted re-index (81,511 passages) and the uncommitted `retrieval_question()`/`PLATFORMS` diff in `runtime/knowledge.py`. Either would add a second, hidden change. Pin `knowledge/*` to the 1022de11 files in every source tree before P6b.
- Evaluate candidates **without activating them**, via the prepared-candidate worker pattern (`data/evals/tuning/prompt-control-r2-20261022-1754/worker.py`). It imports the prepared release's `runtime.mcp_client.chat` and refuses the active release.
- To keep routes identical, the control is also a prepared, non-active release: **C0** = a byte-identical restage of the 1022de11 payload, minus the backup sqlite if the owner agrees (Q5).
- Rollback: a failed candidate is never activated, so rollback means discarding it and stacking the next phase on the last accepted `Cn`. Live-release rollback (`python scripts/releases.py rollback`, or `activate <previous id>`) only matters after an owner-approved activation.

### 4.3 Validation run template
1. **Unit tests:** `python -m unittest discover -s tests -v`, through the documented temp-copy runner `python scripts/test-local.py`. Run `node tests/chat-stream-ui.cjs` if `web/app.js` changes. `prepare` re-runs contracts, unit tests, the companion eval, UI checks, the isolation check and the scan.
2. **Seal the protocol:** write `data/evals/attribution/<phase>-<date>/PROTOCOL.md` (arms, items, seeds, metrics, gates, scorer sha256) and record its sha256 in the run folder and in DECISIONS before the first request.
3. **Smoke 36** (12 prompts x 3) on the candidate. Stop if any safety failure, any crash, or a primary metric worse than control by more than 10 pts.
4. **Dev 366** (122 variants x 3; 1 x seeded if P1 succeeds) on the candidate, plus **other personas 75** whenever the change touches shared code or `EVIDENCE_PROMPT`. The control result is reused only if the route, seed policy and scorer hash are identical. Otherwise re-run the control.
5. **Score:** `score_v2` plus legacy v1. Gates are judged on dev-tuning. Dev-holdout is reported only in aggregate and never inspected row by row during tuning.
6. **Blinded human spot check** (owner, about 20 items, CPU only) for any phase whose primary metric is citation support or directness.

### 4.4 Stop rules
- **Global:**
  - stop on any safety failure, OOM or lost GPU residency
  - stop when free VRAM is below the floor
  - stop while any other GPU job is running (notes, training, another eval)
  - stop if the owner is using chat (create `STOP` in the run folder, as in `run_r2.py`)
- **Phase:** at most 2 prompt revisions per phase against dev-tuning, to limit overfitting. Two failed attempts: stop and escalate to the owner with the evidence.
- **Program checkpoints:**
  - After P5: if support is below 50% (human-calibrated) or citing is below 45%, stop before spending more GPU. Re-plan around retrieval (P6) and ask the owner whether to relax a target.
  - After P6: if support is below 80%, do not tune further on dev. Report the gap with the fixed-evidence arm to separate "retrieval failed" from "model mis-cites given good evidence".

### 4.5 Documentation per phase
- Run folder: `data/evals/attribution/<phase>-<date>/` holding PROTOCOL.md, receipt, report, scorer hash and env start/end.
- A `docs/DECISIONS.md` entry, after a verified backup to `E:\speedzone_MS\LARPUS-backup-20261021-1405\attribution\DECISIONS.md.pre-<phase>-<yyyymmdd-hhmmss>.bak` with its sha256 recorded.
- A feature branch and PR per code/prompt phase.
- **OWNER APPROVAL** is required for each push, PR merge, release stage/prepare, release activation, corpus or notes publish, and any change to latency/VRAM budgets.

---

## 5. Phases

### P0 - Measurement validity (first; blocks everything)

**Hypothesis:** v1 heuristics mis-measure all four targets (section 3.3). Optimizing them would reward shorter replies, not grounded or answer-first ones.

**0.1 Scorer audit, recorded:**
- Cite the existing audit in `docs/eval/BASELINE-LARGE-20261025-REVIEW.md` and add the section 3 findings: the direct-answer length confound, uncited-factual math lines, "source-supported" without a citation, and the `src_by` last-preview mapping in `B/score.py`.
- Output: `docs/eval/SCORE-V2-SPEC.md`.

**0.2 Score v2:** `scripts/attribution_score.py`, CPU-only and offline. It reads `responses.jsonl` and `items.jsonl` and never rewrites inputs (unlike `B/score.py`). Functions:
- `parse_citations(text)`: canonical ids, plus malformed attempts (`[source-id]`, `[Teschl, 2012]`, `source-` prefix, truncated hash). Malformed attempts are reported separately.
- `claim_span(text, offset)`: the sentence or list item holding the cite. A standalone "Reference:" line attaches to the preceding claim and is flagged.
- `served_passage(source_id, locator, release_id)`: a read-only lookup (`?mode=ro&immutable=1`) of the exact passage or note `original_passage` in that release's `approved.sqlite`/`notes.sqlite`. This fixes the duplicate-id last-preview problem.
- `support_features(claim, passage)`: content-word recall, number/symbol match, negation mismatch, and a relevance score from the existing local CPU cross-encoder. The automatic proxy label is calibrated on the human labels.
- `needs_source(sentence)`: the v2 uncited-factual rule (section 2).
- `answer_first(reply, item)`: strips the acknowledgement, then checks the first two substantive sentences against reviewed target numbers or key claims and the false-premise or condition cue.
- `truncated(row)`: `done_reason`, else cap contact.

Tests in `tests/test_attribution_score.py` use the quoted rows above as fixtures, with short excerpts and no private data.

**0.3 Human calibration (OWNER, CPU only):**
- Two blinded sheets: `data/evals/attribution/p0-calibration/citation-sheet.csv` (50 items) and `direct-sheet.csv` (50 items).
- Stratified by v2 category: supported, near-miss, low-overlap, unresolved, standalone reference, and lane (spin/pert oversampled).
- Drawn from baseline and r2 responses. No arm, release or score columns. The key goes in `*.PRIVATE.json`, which agents never open.
- Labels:
  - citation: supported / partial / unsupported / irrelevant
  - direct: decisive-first yes/no, complete yes/no
- **Gate:** for each v2 metric, proxy-vs-human agreement >= 85% and kappa >= 0.6. If it fails, that metric's gate of record stays human. Each later phase then needs a 30-item blinded human sample, and the 80% support target is judged on human labels.
- The existing 60-item `B/blinded-review-sheet.csv` should also be completed; it provides correctness labels.

**0.4 Rescore (CPU):** baseline `B/` and the r2 arms under v2, giving the "v2 baseline" numbers in the Final report.

**0.5 Dev split and locked sets:**
- **Dev-holdout:** 12 of the 48 dev families, chosen by sha256 of `family_id + "attribution-holdout-20261029"` (lowest 12). Recorded in PROTOCOL. Aggregate-only.
- **Dev-tuning:** the other 36.
- **Locked test:** 72 families per `docs/finetune/locked-test-spec.md`, written by an independent human or an owner-run local model, never Grok Bot. Sealed, hashed in `split-register.json` and DECISIONS. Used only in Final.

**0.6 Re-baseline C0 (GPU, after the notes job publishes):**
- Stage and prepare C0 (1022de11 payload, `knowledge/*` pinned).
- Run smoke + dev + other: 477 jobs, about 3.0 h.
- Run the **fixed-evidence arm** (P7) on dev through `runtime/rag_eval.py` task B with selectors chosen for each family: about 2.3 h.
- Total P0 GPU: **5.3 h**.

**Gate to leave P0:**
- spec and tests merged (OWNER PR approval)
- calibration done
- C0 receipts clean (0 safety failures, residency OK)
- protocol hash sealed
- locked-test authoring started (it may finish later, before Final)

**Rollback:** none needed; nothing serving changes.

### P1 - Eval instrumentation (seed and finish reason)

**Hypothesis:** paired seeded runs shrink the CIs, so 1 sample per variant can replace 3 for phase screening. Capturing `done_reason` makes truncation exact.

**Files:**
- `runtime/inference.py:stream_reply`: pass `options.seed` only when supplied by the owner-side harness argument, never from HTTP or user input.
- `runtime/inference.py:context_usage` (line 56): record `done_reason`.
- `runtime/mcp_client.chat` (harness entry).
- Production default unchanged: T=0.4, no seed.

**Unit tests** (`tests/test_model_inference.py`, `tests/test_streaming.py`):
- The seed appears in options only via the harness path.
- The HTTP payload cannot set it.
- `done_reason` is propagated.

**Validation:** A/A on smoke 36 x 2 runs, same seed (0.45 h). Then re-run C0 dev seeded, 1 sample each (2.3 h, only if A/A passes). Total 2.8 h.

**Gate:** identical output on >= 90% of smoke items, and safety unchanged. **If it fails** (GPU nondeterminism), drop seeds and keep 3 unseeded samples per variant. The phase budget is not reused.

**Rollback:** discard C1. P2 then stacks on C0.

### P2 - Citation-id contract (highest leverage per GPU hour)

**Hypothesis:** the invented `[source-id]` and prefixed or truncated ids are caused by the placeholder and the lack of an explicit id list (section 3.1).

**Files, `runtime/knowledge.py`:**
- `EVIDENCE_PROMPT`: replace "[source-id]" and the "(Blackwell, 1956) [source-id]" example with "copy the exact `id` value of the item, e.g. [<first evidence id>]". Keep the author-credit rule.
- `augment()` (about line 400): append the line `Allowed citation ids: [id1] [id2] ...`, generated from the evidence items, after the JSON block. Notes contribute their base source id. Nothing is appended when NO_EVIDENCE_PROMPT applies.

**Unit tests** (`tests/test_knowledge.py`):
- the prompt contains no literal `source-id`
- the allowed-id list equals the set of evidence ids
- the list respects EVIDENCE_BUDGET=9000
- no list without evidence
- `fixed_evidence()` (line 211) path also gets the list

**Expected movement:**
- invented ids 4.4% -> <= 0.5%
- citation resolution about 95% -> >= 99%
- citing share flat to slightly up
- latency unchanged

**Validation:** smoke 36, dev 366, other 75: 3.0 h.

**Gate:** invented <= 0.5% of occurrences, plus all must-not-regress gates.

**Rollback:** discard the candidate.

### P3 - Server-side citation validator

**Hypothesis:** even after P2 the model will occasionally emit unknown ids. Normalizing near-misses and stripping the rest guarantees 0 invented ids reach the owner, without regeneration.

**Files, `runtime/inference.py`:**
- New `validate_citations(text, allowed)`:
  - maps `source-<id>` to `<id>` when exact
  - maps a unique-prefix truncated hash to the full id
  - removes `[source-id]`
  - replaces any other unknown bracket id with nothing and records it
- Called inside the stream release path (`stream_cut` / `release`) **before** the DLP output gate, so DLP still screens the final text. It must handle an id split across stream chunks: hold back an unclosed `[` up to 120 chars.
- `citation_check` (line 65) gains statuses `normalized` and `removed-unknown` with counts.
- `web/app.js:attachSources` already displays `citation_check.status` and needs only wording.

**Optional P3b, separate candidate:** one bounded regeneration on the **non-streaming** route only, when a reply claims "source-supported" with zero valid ids. Streamed text cannot be retracted, so P3b never applies to `/api/chat/stream`. It obeys the broker output budget and DLP. Adopt it only if it meets the latency budget.

**Unit tests** (new `tests/test_citation_validator.py`, plus `tests/test_streaming.py`): fixtures for each invented form in 3.1, plus:
- repeated ids
- an id split across chunks
- no evidence
- DLP-held text never passes through un-screened
- a validator exception fails closed (the citation is removed, never released raw)

**Expected movement:** invented ids reaching the user = 0. Measured support rises slightly because junk ids leave the denominator. Note that score v2 reports **pre-validator emissions too**, so the model behavior stays visible.

**Validation:** 3.0 h, same template.

**Gate:**
- 0 unknown ids in released text
- pre-validator invented share no worse than P2
- latency <= +5%
- DLP tests unchanged

**Rollback:** discard. P2 remains valid on its own.

### P4 - Answer-first and length policy

**Hypothesis:** the 250-word and 1024-token overruns, not question-first openings, drive direct-answer and truncation failures. The quantum prompt's checklist (state, Hamiltonian, basis, units, sign conventions, regime) and the "Verification status" ending inflate length (`agents/personas/quantum-mechanics-professor.json`). v2 already showed 25 -> 69 direct and about 7% truncation.

**Files:**
- `agents/personas/mathematician.json` and `quantum-mechanics-professor.json`: append the v2 "Evidence-first tutoring rules" exactly as in prepared release 61a6448a, ported onto C(P3). Do **not** activate 61a6448a itself: it predates Horizon, DLP quarantine and rag_eval.
- Regenerate `config/broker-prompts.json` through the normal build.

**P4b (only if applicability regresses, separate candidate):**
- one line: "When the answer depends on hypotheses or regime, state them exactly in the first two sentences"
- target row `dev/grok-r1-opt-05/d` (bounded-below condition and counterexample)

**Unit tests:**
- persona JSON schema and fingerprint tests already in `tests/`
- add an assertion that both personas contain the answer-first rule and "at most one question"

**Expected movement:**
- direct v2 20% -> 65-75%
- truncation 25% -> about 7%
- median latency -30%
- citing share **down** (r2: 29.9 -> 16.9%); P5 addresses it
- applicability at risk

**Validation:** smoke 36 + dev 366 (2.5 h). Other personas are byte-identical, so they are not re-run. Then a 20-item blinded owner spot check for directness and completeness.

**Gate:** direct >= 70%, truncation < 8%, and every behavior check within the no-regression rule (applicability especially).

**Rollback:** discard. The P3 candidate stays the head.

### P5 - Per-claim grounding rule

**Hypothesis:** the model cites whole textbooks for general facts, cites in verification lines, and labels unsourced answers "source-supported". An explicit claim-level contract raises both the citing share and support.

**Files:**
- `runtime/knowledge.py:EVIDENCE_PROMPT`, shared by all personas:
  - cite each externally sourced factual claim in the same sentence, using only ids whose passage states it
  - no standalone reference lines
  - no citations in verification lines
  - derivations done here are marked as reasoning, not cited
  - if no provided item supports a needed fact, say "not covered by the provided sources"
- Persona JSONs: the Verification status may say "source-supported" only if at least one claim carries a valid id.

**Unit tests:** prompt text contains the claim-level rules, and the verification rule appears in both personas.

**Expected movement:**
- citing share (strict) 17-30% -> 55-70%
- human-calibrated support -> about 65%
- v2 uncited factual -> -50% or better
- length +5-10% (watch truncation)

**Validation:** smoke, dev and other (3.0 h), because the shared prompt affects all 12 personas. Watch `s1/other/psychologist-expertise`. Then a 30-item human citation-support sample.

**Gate:**
- citing >= 60%
- support >= 65%
- uncited v2 <= 50% of C0
- direct >= 70% held
- truncation < 8%
- other personas pass the regression rule

**Checkpoint stop rule:** see 4.4.

**Rollback:** discard.

### P6 - Retrieval quality for spin and perturbation

**Hypothesis:** quantum lanes cite least because the served passages are research-thesis fragments with damaged math, not textbook statements (section 3.5).

**6a. Diagnosis, CPU only:**
- Use `runtime/rag_eval.py` task A (retrieval-only) on the 4 dev spin and the dev/train perturbation families, plus `dev/grok-r1-pert-15/a` and `dev/grok-r1-spin-05/a`.
- Export the BM25 top-50, the `_hybrid` reranked top-k and the final 3+2 items.
- The owner annotates relevance for 30 cases, giving Recall@5.
- Compare the 1022de11 index against the checkout index (81,511 passages, includes the 96 new sources) **offline**. Both are read-only, so there is no GPU use.

**6b. Corpus release, one change:**
- After the notes job publishes (ETA 6-7 AM ET Oct 30) and the owner approves, stage C(P5) + the new `approved.sqlite`, embeddings and `notes.sqlite`. The checksums are already recorded in DECISIONS 2026-10-29.
- Unit tests: the existing `tests/test_knowledge_counts.py` and `test_knowledge_preparation.py` count and manifest checks.
- Expected: spin/pert citing share 14-15% -> >= 50%, support up, quantum vs math gap narrower.

**6c. Optional ranking change, separate candidate, only if 6a recall is below 70% after 6b.** One of:
- `_retrieve` (line 284) `per_source` cap 1 -> 2 for lecture-note series
- `_hybrid` (line 248) rerank top-k
- `study_notes` (line 124) dropping notes whose `original_passage` has extraction damage (glyph names like `/arrowext`)

Unit tests in `tests/test_knowledge.py` with fixed tiny fixtures.

**Validation:** 6a takes no GPU. 6b and 6c each take 3.0 h, because the corpus is shared.

**Gate:**
- spin/pert Recall@5 >= 70%
- overall support >= 80% and citing >= 70% (the targets)
- other personas pass the regression rule
- retrieval CPU time and first-text latency within budget

**Rollback:** discard the candidate. The corpus stays unpublished to production.

### P7 - Fixed-evidence control arm (measurement, existing code)

`runtime/rag_eval.py` and `scripts/mtrageval_local.py` already provide fixed-selector generation (`knowledge.fixed_evidence`, at most 3 selectors). `B/PROTOCOL.md` predates them, which is why no arm was run.
- Run it at P0 (on C0) and in Final (on the final candidate), on the same dev families, with owner-chosen rights-cleared selectors.
- Report it **separately**. It is never pooled with live retrieval and never used to claim a ranking fix.
- It answers: "given the right passage, does the model cite and answer first?"

No code change, no gate.

### P8 - Per-persona sets for the 10 thin personas (no GPU until Final)

The other personas have only 2 cases each (system-administrator 7), and score at 100% except system-administrator at 76.2%. A 3-point regression is undetectable at that size.
- Write at least 10 independent cases per persona: accuracy, relevant citation, refusal, privacy and live-action negatives. Start with psychologist clinical screening and system-administrator operations.
- Store them under `data/evals/persona-sets/` after a rights review, sealed and hashed.
- Not authored by Grok Bot. They can be written in parallel from P0.

### P9 - Contingency: answer budget and `num_predict`

Run P9 only if, after P6, truncation is >= 5% or direct is below 80%.
- Option A (prompt only): per-answer-type budgets in the persona prompts ("about 150 words for a single result; up to 350 for a multi-part derivation").
- Option B: `runtime/context.py:OUTPUT_LIMIT` per persona, e.g. 1536 for QM. Option B costs latency and KV memory; only with an owner-approved VRAM and latency budget.
- One option per candidate. Each takes 2.5 h.
- **Gate:** truncation < 5%, direct >= 80%, latency budget held, VRAM floor held.

---

## 6. Final confirmation run

Prerequisites:
- every accepted phase merged (OWNER)
- locked test sealed
- persona sets sealed
- PROTOCOL-FINAL sealed with its hash recorded **before** the first request

**Route:** full live security gates (Horizon input guard, DLP input and output, text filter, broker limits, residency check). Use the production streaming route with no seed: either a prepared-candidate worker carrying the same gates, or, with OWNER approval, a brief activation using `python scripts/releases.py activate <final id>` with rollback ready.

**Arms:** C0 control and the Final candidate, run sequentially in alternating blocks.

| Item set | Jobs per arm (x3 samples) | GPU h (both arms) |
|---|---|---|
| Smoke + dev + other | 477 | 5.8 |
| Locked test (72 families, about 180 variants) | 540 | 6.6 |
| Persona sets (100 cases) | 300 | 3.7 (C0 needed for the regression rule) |
| Fixed-evidence arm, Final candidate only, reported separately | 122 x 3 | 2.3 (approx.) |

That comes to about 15.9 h. The candidate-only train diagnostic (1701) is optional: +10.6 h.

**Pass:** all five targets met on dev-holdout **and** locked test, with point estimates at target and CI lower bound within 5 pts. Every must-not-regress gate passes. Live-retrieval and fixed-evidence results are reported separately with their own denominators.

**After pass:** a DECISIONS entry with backup. OWNER decides on activation, push and merge.

---

## 7. Owner approval points (marked)

1. P0: label the calibration sheets; complete `B/blinded-review-sheet.csv`; commission the locked tests (independent author); approve the C0 stage/prepare.
2. Each phase: approve the PR, push and merge, and the candidate stage/prepare. No candidate is activated during phases.
3. P5: decide whether "not covered by the provided sources" counts toward the 70% citing target.
4. P6b: approve publishing the new corpus and notes into a candidate.
5. P9: approve any latency, VRAM or `num_predict` budget change.
6. Final: approve PROTOCOL-FINAL, any temporary activation, and production activation. Rollback: `python scripts/releases.py rollback`.

## 8. Open questions for the owner

1. **Latency/VRAM budget:** is median <= 1.20 x and p95 <= 1.25 x control, with a free-VRAM floor of 512 MiB, acceptable?
2. **Reviewers:** who labels the 100 calibration items and the 60-item sheet, and who independently writes the 72 locked families and about 100 persona cases?
3. **Citing target:** does an explicit "not covered by the provided sources" count, and should self-contained derivations be exempt (`s1/dev/grok-r1-meas-05/a`)?
4. **Uncommitted work:** should the uncommitted `retrieval_question()`/`PLATFORMS` change in `runtime/knowledge.py` become its own phase (before P2) or be shelved? Under one-change-per-phase it cannot ride along.
5. **Release contents:** should future releases exclude `knowledge/notes.build.backup-20261015-pre-fixes.sqlite` (about 190 MB), and should C0 drop it?
6. **Horizon false holds:** does the Horizon guard hold any eval prompts (as with cyber-pentest at 0.5336)? P0 will record holds per item. Should held items be excluded or counted as failures?
7. **6,495 orphan notes:** should notes from sources missing from the index (chicone, salsa, ...) be filtered before P6b?

## 9. What was read (read-only)

- `runtime/knowledge.py`, `runtime/inference.py`, `runtime/agents.py`, `runtime/rag_eval.py`
- `agents/personas/{mathematician,quantum-mechanics-professor}.json` (live and 61a6448a)
- `docs/DECISIONS.md` (entries 2026-10-22 to 2026-10-29), `docs/eval/BASELINE-LARGE-20261025-REVIEW.md`, `docs/LARGE_BASELINE_ACCURACY_ROADMAP_2026-10-26.md`, `docs/BEHAVIOR_STAGE_PREP_2026-10-29.md`, `docs/finetune/locked-test-spec.md`, `docs/PERSONAS.md`, `docs/DEPLOYMENT.md`, `README.md`, `AGENTS.md`
- `scripts/releases.py` (CLI), `data/releases/*` (manifests)
- `B/` (PROTOCOL.md, score.py, common.py, responses/items/scored-rows, reports)
- `data/evals/tuning/round0-20261022-0940/score.py`
- `data/evals/tuning/prompt-control-r2-20261022-1754/` (summary, decision, worker, runner, responses)
- The release 1022de11 `approved.sqlite`, opened read-only and immutable

All analyses were CPU-only and in memory; no scorer was executed.