# Locked-test gap and authoring spec (round 1 dataset build)

Status: **GAP — 72 locked-test families are NOT written.** Written 2026-10-22 ET by Grok Bot. Grok Bot is the hosted teacher, so under GROK_TEACHER_TUNING_LOOP.md it must not author, see, or grade locked-test material. This file is a specification only. It contains no test prompts, answers, or subtopic choices.

## Why this is a gap
- The plan, scaled to the boss's 28x target (12 round-0 families x 28 = 336), keeps the plan's per-lane ratio of 13 train / 3 dev / 4 test, rounded to **18 / 4 / 6 per lane**. That's 216 train, 48 dev and 72 locked test.
- Train and dev are written: 204 new families plus the 12 existing round-0 families, all train, and 48 dev.
- Test slots are reserved in `split-register.json` as `locked-test-<lane>-01..06`, with status `GAP: to be authored independently, sealed from Grok Bot`.

## Slots (6 per lane, 36 per persona)
| lane | persona | plan topic lane | reserved ids |
|---|---|---|---|
| lim | Mathematician | Limits, continuity and convergence | locked-test-lim-01, locked-test-lim-02, locked-test-lim-03, locked-test-lim-04, locked-test-lim-05, locked-test-lim-06 |
| calc | Mathematician | Differentiation and integration | locked-test-calc-01, locked-test-calc-02, locked-test-calc-03, locked-test-calc-04, locked-test-calc-05, locked-test-calc-06 |
| ode | Mathematician | ODEs and dynamical systems | locked-test-ode-01, locked-test-ode-02, locked-test-ode-03, locked-test-ode-04, locked-test-ode-05, locked-test-ode-06 |
| pde | Mathematician | PDE boundary problems | locked-test-pde-01, locked-test-pde-02, locked-test-pde-03, locked-test-pde-04, locked-test-pde-05, locked-test-pde-06 |
| opt | Mathematician | Continuous optimization | locked-test-opt-01, locked-test-opt-02, locked-test-opt-03, locked-test-opt-04, locked-test-opt-05, locked-test-opt-06 |
| fa | Mathematician | Functional analysis | locked-test-fa-01, locked-test-fa-02, locked-test-fa-03, locked-test-fa-04, locked-test-fa-05, locked-test-fa-06 |
| meas | Quantum Mechanics Professor | States and measurement | locked-test-meas-01, locked-test-meas-02, locked-test-meas-03, locked-test-meas-04, locked-test-meas-05, locked-test-meas-06 |
| dyn | Quantum Mechanics Professor | Dynamics and stationary states | locked-test-dyn-01, locked-test-dyn-02, locked-test-dyn-03, locked-test-dyn-04, locked-test-dyn-05, locked-test-dyn-06 |
| spin | Quantum Mechanics Professor | Spin and angular momentum | locked-test-spin-01, locked-test-spin-02, locked-test-spin-03, locked-test-spin-04, locked-test-spin-05, locked-test-spin-06 |
| pert | Quantum Mechanics Professor | Perturbation and approximation | locked-test-pert-01, locked-test-pert-02, locked-test-pert-03, locked-test-pert-04, locked-test-pert-05, locked-test-pert-06 |
| ent | Quantum Mechanics Professor | Entanglement and reduced states | locked-test-ent-01, locked-test-ent-02, locked-test-ent-03, locked-test-ent-04, locked-test-ent-05, locked-test-ent-06 |
| open | Quantum Mechanics Professor | Open systems and experiments | locked-test-open-01, locked-test-open-02, locked-test-open-03, locked-test-open-04, locked-test-open-05, locked-test-open-06 |

## Who
- An **independent author**: a human expert, or a local model run by the owner on the PC, that has not seen the Grok-written train/dev drafts' targets.
- Not Grok Bot or any hosted teacher, not Codex sessions that have read the drafts, and not LARPUS itself.
- A second person (or a second independent pass) reviews each test family before sealing.

## Content requirements
1. **Coverage per lane:** 6 families on the same topic lane, choosing subtopics **not** among that lane's 21 train/dev `planned_subtopic` entries in `split-register.json`, so test measures transfer, not recall. Span difficulty from intro to graduate. Aim for at least 1 intro and at least 1 graduate-level family per lane.
2. **Behaviours:** across each lane's 6 families, include all six target behaviours:
   - direct answer
   - practice mode with exactly one hint
   - false premise
   - missing assumption
   - preserve qualifications from supplied evidence (synthetic excerpts only, clearly labelled)
   - honest verification status
3. **Balance:** missing-assumption and evidence-qualification variants should each be at least 1/6 of test variants. Use 2-3 variants per family.
4. **Correctness:** every family gets an executable sympy/numpy/scipy check, kept in a **separate** sealed `verify_locked_test.py`, not in `verify_families.py`. Otherwise mark it `hand-proof-only` with a proof sketch. Only passing families are sealed.
5. **Originality:** write from scratch. No textbook, licensed or LARPUS knowledge-base text, and nothing from `data/` or chat logs.
6. **Dedupe:** check against train/dev by normalized prompt similarity, using `difflib` ratio >= 0.80 or 3-shingle Jaccard >= 0.5, and by core problem. A test family must not be a reworded train/dev family. The test author may run the dedupe script against train/dev prompts without reading the targets.

## Record format
Use the same schema as `families-train.draft.json` (`larpus-grok-teacher-round0/draft-1` family/variant fields), with these differences:
- `split: "test"` and family ids `locked-test-<lane>-NN` exactly as reserved.
- `review.status: "sealed-pending-independent-review"`, then `"sealed"` after review. Keep `reviewed_target: null` until the reviewer signs.
- `packet_manifest.teacher_identity`: the independent author, never Grok Bot. Set `locked_test_material_included: true`, and set `outbound_from_pc: null` with a note that test material never leaves the PC.
- `student_answer.origin`: a real round-zero LARPUS attempt, collected **after** sealing by the owner, or a clearly labelled synthetic stand-in.
- `provenance`: set `license`, `training_use` (must be `"never"` for test) and `external_sharing_approval` (must be `"never"`).

## Sealing and hashes
1. Write `families-test.sealed.json` and `verify_locked_test.py` on the PC only, outside any folder shared with Grok Bot or staging (not `grok-finetune-staging`).
2. For each family, compute `family_sha256` = SHA-256 of `json.dumps(family_without_packet_manifest, sort_keys=True, ensure_ascii=False)`, the same rule as train/dev.
3. Compute a file-level SHA-256 of `families-test.sealed.json`. Record only the **hashes**, the count and the date in `split-register.json` (update the 72 slot statuses to `sealed`) and in a dated `docs/DECISIONS.md` entry. The content stays sealed.
4. Never send test files to a hosted service. Never include them in training packets. Grading by LARPUS happens locally, after training rounds, against the sealed file.

## Acceptance checklist
- [ ] 72 families, 6 per lane, ids match the register
- [ ] `verify_locked_test.py` passes (hand-proof-only items listed with sketches)
- [ ] dedupe vs train/dev clean, or each flag adjudicated
- [ ] behaviour mix: MA >= 1/6 and EQ >= 1/6 of test variants; all six behaviours in every lane
- [ ] independent review signed; hashes recorded; files stored outside shared/staging folders
