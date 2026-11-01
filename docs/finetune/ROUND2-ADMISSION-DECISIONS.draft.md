# Round 2 admission decisions: DRAFT for owner signature (nothing admitted)

Status: **DRAFT. Unfilled proposals only.** Grok Bot wrote this on 2026-10-27 (ET).
**No family, variant or example is admitted for Round 2 training until the owner fills in and signs every
decision below.** A blank decision means "not decided". Grok Bot agreeing with its own proposals is not
independent review. No family JSON, receipt or draft was edited to produce this file. Nothing was trained,
uploaded, committed or pushed. No `*.PRIVATE.json` blind key or `*.UNBLINDED.md` file was opened.

## 0. Evidence summary (read-only audit, 2026-10-27 ET)

### Which data pilot1 was trained on

- Receipt: `data/evals/tuning/pilot1-20261023-0742/train-receipt.json`. Under the `data` key, `source_package` is
  `C:\Users\PS5Killer\grok-finetune-staging\owner-opt05-20261022-1311`. That package is **not** the
  `owner-signoff-20261022-092213` package reviewed in `GROK-BOT-REVIEW-REPORT.md`. Its `split_used` is `"train only"`.
- Training file: `train-examples.jsonl`, sha256 `04f69de7dece796decaac443df00997ca0641a72ce05e52b202becb66f3acbe7`.
  The copy in `data/evals/tuning/pilot1-20261023-0742/` and the Larpus WSL copy at
  `/home/larpus/train-models/pilot1-20261023-0742/train-examples.jsonl` hash identically (rechecked 2026-10-27).
  It has 562 lines, 214 distinct families, and Mathematician 274 / Quantum 288 examples.
- Manifest: `data-manifest.json` sha256 `9ed42ee0c6ef85754905a327db0023bc1082ed224f297b71f58fb96a2b408c91`. Builder:
  `build_dataset.py` sha256 `a78bfc31a80a49ed614b62997092e04cb8e53a4db6222e3a2fac9da113f69602`. The builder reads only
  `grok-round0-families.owner-reviewed.json` and `families-train.owner-reviewed.json` into `fams`, and it runs
  `assert all(f['split'] == 'train' ...)`. The builder loads `families-dev.owner-reviewed.json` only for the leakage audit.
- Source file hashes (receipt key `data.source_file_sha256`; each matches the bytes on disk today):

| File in `owner-opt05-20261022-1311` | sha256 | Used for |
| --- | --- | --- |
| `grok-round0-families.owner-reviewed.json` | `a071b41a439a8c541e7ea4a84c471601db10ec09af2a375e53da5a4c74356579` | training (12 families) |
| `families-train.owner-reviewed.json` | `e2f0631c81578cad7abc74bcdb541060897e92d8355e7f2c8eb68187dfea9b1c` | training (204 families) |
| `families-dev.owner-reviewed.json` | `5d841e75239406e80c99b4a5d160a5f8803aff6268510f6fc1e428bdf56e016a` | leakage audit only |

  The two train files are byte-identical to those in `owner-rights-20261022-094356`. They are the rights-tagged copies
  of the owner-reviewed files. They are not the `docs/finetune/*.draft.json` drafts (draft hashes `04dff8dd...`/`b0fbea7b...`)
  and not the earlier `owner-signoff` copies (`a34efc18...`/`9af06a14...`). The examples' assistant text is `reviewed_target`.
- Dev leakage: none was found. None of the 48 dev family ids (opt05 package) appear in `train-examples.jsonl`. The manifest
  `leakage_audit` has `family_id_overlap_train_dev: []` and `exact_user_content_overlap: []`. It also has `exact_reviewed_target_overlap: []`,
  max 5-gram Jaccard 0.556 against 134 eval prompts, and `dev_split_used_for_training: false`.
- Skipped: `grok-r1-fa-13` (a, b) and `grok-r1-open-16` (a, b, c), both as "hand-proof-only verification".
- Rights fields on all 216 manifest family rows: `training_use` = "local training on the owner's PC only",
  `license` = "owner-internal, local-use only", `external_sharing_approval` = "denied: no external sharing".

### grok-r1-opt-05 and pilot1

- `grok-r1-opt-05` is a **dev** family (`split=dev` in all three owner packages). It is not in either train file.
- `train-examples.jsonl` contains **0** lines that mention `opt-05` (Windows and WSL copies both checked). So **no variant of
  opt-05 was in pilot1's training set**: not the false draft, not the corrected target, and nothing else.
- Only one training target discusses the `2/L` step bound: `grok-r1-opt-19/a`. It covers the 1-D positive-curvature quadratic
  `x_(k+1) = (1 - alpha L) x_k` and does not contain the false general claim.
- opt-05/d did appear in pilot1's **evaluation** as a dev item, scored against the corrected target (DECISIONS.md, pilot1 entry).
  That is the intended use of a dev reference.

### Existing records of the decisions (they already exist; the Oct-27 report did not see them)

- **training_use, license, external sharing:** `owner-rights-20261022-094356/RIGHTS-DECISION.md` and `OWNER-RIGHTS-RECEIPT.json`
  (sha256 `57869b49de134dc862661577234f722c25955c16613d1e72d5644a52755befd4`) contain these records:
  `decided_et 2026-10-22T09:36:00-04:00`, `owner_statement "Mark them for local training only on my PC, no external sharing"`.
  The receipt sets those three fields on all 264 families. The same values are carried into `owner-opt05-20261022-1311`
  and recorded in `docs/DECISIONS.md` (entry "Round-zero baseline started ... (2026-10-22, 10:45 AM ET)", "Owner rights decision (09:36 ET)").
- **opt-05/d correction:** `owner-opt05-20261022-1311/OWNER-OPT05-APPROVAL-RECEIPT.json` (sha256
  `a494c9ce85ef70e9a5c5f0e7d0ed0f86292d175d58c2b40c08c9995bcfc5d913`) records `approved_et 2026-10-22T13:10:00-04:00`,
  `owner_statement "Approve the opt-05/d correction"`, and family hash `9a3da320...c35d` -> `ee4be6cc...6a1b`. The source package
  is recorded as unchanged. The corrected `reviewed_target` (utf-8 sha256 `0641b10d1783413dcd5ebc8c5c9b0f4916ad8ff4119994f43d83e702906d3a33`)
  comes from `docs/finetune/opt-05-d-correction.proposed.md` (sha256 `ee4c7a85f007567aeec879e48c607e6a43ee9a63c52cec373b71e7056346e653`).
  The DECISIONS.md entry "opt-05/d correction approved; dev reference changed (2026-10-22, 1:10 PM ET)" also records it.
- **Why the conflict:** `owner-signoff-20261022-092213/GROK-BOT-REVIEW-REPORT.md` (written 2026-10-27, sha256
  `a2774102e81e065c67e86b65482d1cf7ffcfdda3efaa3ff5630538ade5690b4f`) reviews the **09:22 signoff package only**. That package
  predates both later decisions and was deliberately never edited. Its "null on all 264 families" and "opt-05/d held"
  statements are true of that package and stale for `owner-opt05-20261022-1311`. Both memory notes are therefore backed by
  files on disk. The owner must still say which package is canonical for Round 2 (decision 0).
- **Approval wording for pilot1 itself:** the train receipt states "Exact owner approval wording is not recorded in this folder".
  The rights receipt's `still_blocking_training` and the opt-05 receipt's `not_admission` both said that training needed further
  steps first: a recorded Grok/xAI terms check, real round-zero attempts, locked tests and per-family admission. pilot1 ran
  while `rights_open_item` ("check of current Grok/xAI terms ... not recorded") was still open.

## Decision 0: canonical source package for Round 2

Options:
- (a) `owner-opt05-20261022-1311`. This is the latest package: rights fields set, opt-05/d corrected, 264 families.
- (b) `owner-signoff-20261022-092213`. This is the package the Oct-27 report reviewed. Its rights fields are null and opt-05/d is held.
- (c) A new versioned copy made after these decisions are signed. Earlier packages stay untouched.

Proposed: (c), derived from (a). **Owner choice:** ________  **Date/time ET:** ________

## Decision 1: training_use, per family

Current record: "local training on the owner's PC only" on all 264 families (owner statement 2026-10-22 09:36 ET; see above).
Conflicting record: the 2026-10-27 report says null, because it reviewed the earlier package.

| Group | Families | Proposed `training_use` | Owner value |
| --- | --- | --- | --- |
| Round-0 train (`grok-round0-families`) | 12 | local training on the owner's PC only | ________ |
| New train (`families-train`) | 204 | local training on the owner's PC only | ________ |
| Hand-proof-only train: `grok-r1-fa-13`, `grok-r1-open-16` | (2 of the above) | excluded until a non-drafter reads the proofs | ________ |
| Dev (`families-dev`), including `grok-r1-opt-05` | 48 | **never for training** (evaluation reference only) | ________ |
| Locked test (not written) | 72 slots | `never` (per `locked-test-spec.md`) | ________ |

Options: (a) reconfirm the 2026-10-22 value as shown; (b) set evaluation-only for everything (no Round 2 training);
(c) list exceptions by family id. Decision 1 does not apply until decision 4 is resolved.
**Owner choice:** ________  **Exceptions:** ________

## Decision 2: license for the families

Current record: `license` = "owner-internal, local-use only" on all 264 families. The agent set this value in the rights package.
The owner's recorded words mention training and sharing but not the word "license", so this value needs explicit confirmation.

Options: (a) confirm "owner-internal, local-use only"; (b) "no license granted; subject to xAI terms" (see decision 4);
(c) other. **Owner choice:** ________

## Decision 3: external_sharing_approval

Current record: "denied: no external sharing" on all 264 families.
Proposed: **none / denied**. No upload to hosted teachers, training APIs, GitHub as data, or model hubs. No adapter trained on
these families may leave the PC.
**Owner choice:** ________

## Decision 4: may Grok-drafted families be used for training at all (xAI terms)

All 264 families, the targets and the 689 synthetic `student_answer`s were drafted by Grok Bot (an xAI product). Their use as
fine-tuning data is a rights question that comes before decisions 1 to 3.

Policy text, verified by a read-only fetch of https://x.ai/legal/acceptable-use-policy on 2026-10-27 (about 6:15 PM ET). The page
is titled "SpaceXSI Acceptable Use Policy", "Effective: August 14, 2026". Under "Detrimentally impacting the Service, including by:" it lists:
> "Using the Service or any Output to develop (or assist anyone in developing) machine learning models or any products or services that compete with SpaceXSI, whether directly or indirectly"
>
> "Scraping, harvesting or reselling any Input or Output, or distilling model data or Outputs"

The Consumer Terms (https://x.ai/legal/terms-of-service, "Last Updated: October 12, 2026") require compliance with the AUP.
**Unverified:** which agreement governs Grok Bot output specifically (Consumer, Enterprise or Grok Bot-specific terms). Whether a
private, local, non-distributed fine-tune of Qwen counts as "competing" or "distilling" is also unverified. The Enterprise Terms
were not fetched. This is not legal advice. Check https://x.ai/legal or ask xAI.

Options:
- (a) **Do not use Grok-drafted families for training.** Keep them for evaluation and dev reference only.
- (b) **The owner rewrites the targets himself.** Only owner-authored `reviewed_target` text is trained on, and Grok text is used as notes only. Record the authorship per variant.
- (c) **Regenerate with local Qwen drafts.** The local model drafts prompts and targets on the PC, the owner reviews them, and nothing is generated by Grok.
- (d) **Seek written xAI permission** before any training use, and record the reply.
- (e) Proceed under a documented owner risk acceptance (not recommended while the AUP text above stands).

Proposed: (a) now; (b) or (c) for Round 2 data; (d) optional. **Owner choice:** ________

## Decision 5: grok-r1-opt-05 variant d disposition

Facts: opt-05 is a **dev** family, so this decision affects the evaluation reference only, never training data.
The original draft (`docs/finetune/families-dev.draft.json`, `teacher_target_draft`) reads: "For an L-smooth function, any fixed step
0 < alpha < 2/L avoids divergence on quadratics, and alpha = 1/L is the standard safe choice." This is false. Counterexample: `f(x) = -x^2`
is L-smooth with `L = 2`, and `alpha = 0.5` is in `(0, 1)`. Then `x_(k+1) = x_k - 0.5(-2 x_k) = 2 x_k`, which diverges from any `x_0 != 0`.
The owner approved a corrected target on 2026-10-22 13:10 ET in `owner-opt05-20261022-1311`, as recorded above.

Options:
- (a) **Hold.** `reviewed_target` stays null in the Round 2 package and the item is excluded from target scoring.
- (b) **Keep the 2026-10-22 approved correction** (sha256 `0641b10d...3a33`) as the dev reference.
- (c) **Replace it with the scoped statement below** after an independent recheck.
- Separately: should variant c's "constant steps below 2/L work for convex problems" get the iterate-convergence qualification?

Corrected mathematical statement (**needs independent recheck by someone other than Grok Bot**). Let `f: R^n -> R` be
differentiable with L-Lipschitz gradient (`L > 0`). Gradient descent is `x_(k+1) = x_k - alpha grad f(x_k)`, with `0 < alpha < 2/L`.
1. If f is **bounded below**, then `f(x_(k+1)) <= f(x_k) - alpha(1 - alpha L/2) ||grad f(x_k)||^2`. So f never increases,
   and it strictly decreases while the gradient is nonzero. Also `||grad f(x_k)|| -> 0`. Iterate convergence is **not** guaranteed.
2. If f is a **convex quadratic** `1/2 x^T A x - b^T x` whose eigenvalues lie in `[mu, L]` with `mu > 0`, then
   `||x_k - x*|| <= rho^k ||x_0 - x*||` with `rho = max(|1 - alpha mu|, |1 - alpha L|) < 1`. That is, the iterates converge linearly to the unique minimizer.
3. If f is **convex** and has a minimizer, the iterates converge to some minimizer. This is a standard result: for convex L-smooth f,
   `grad f` is 1/L-cocoercive, so `I - alpha grad f` is averaged for `alpha < 2/L` (Krasnosel'skii-Mann).
4. With **no lower bound and no convexity**, nothing is guaranteed (`f = -x^2` above). On a quadratic with top eigenvalue L,
   `alpha = 2/L` oscillates without decaying and `alpha > 2/L` diverges.

Verification sketch:
- Item 1: apply the descent lemma `f(y) <= f(x) + grad f(x)^T (y - x) + (L/2)||y - x||^2` at `y = x - alpha grad f(x)`. This gives
  `f(x_(k+1)) <= f(x_k) - alpha(1 - alpha L/2)||grad f(x_k)||^2`, and the coefficient is positive iff `0 < alpha < 2/L`. Summing over k gives
  `sum ||grad f(x_k)||^2 <= (f(x_0) - inf f) / (alpha(1 - alpha L/2)) < inf`, so the gradient tends to 0. Counterexample for iterate convergence:
  the logistic loss `log(1 + e^(-x))` (`L = 1/4`) has `f' < 0` everywhere and no minimizer. So `x_k` increases without bound, because a bounded
  increasing sequence would converge to a stationary point and none exists.
- Item 2: the error recursion is `x_(k+1) - x* = (I - alpha A)(x_k - x*)`. In the eigenbasis each factor is `1 - alpha lambda`, and
  `|1 - alpha lambda| < 1` iff `0 < alpha lambda < 2`. This holds for all `lambda` in `[mu, L]` iff `alpha < 2/L`, given `mu > 0`.
- Item 4: arithmetic as shown. For `lambda = L` and `alpha = 2/L`, the factor is -1.
- Existing executable check: `owner-opt05-20261022-1311/check_opt05d.py` (sha256 `61cfde75...df00d90`). It ran on 2026-10-22 at 1:11 PM ET
  and printed "ALL CHECKS PASS". This covers specific instances only. It illustrates the results but does not prove them.

**Owner choice (a/b/c):** ________  **Variant c qualification (yes/no):** ________  **Independent rechecker:** ________

## Decision 6: is pilot1's training data retired?

Facts: `train-examples.jsonl` (sha256 `04f69de7...acbe7`, 562 examples, 214 Grok-drafted train families) trained the shelved
pilot1 adapter (`adapter_model.safetensors` sha256 `0650d883...5c05`). That adapter regressed in heuristic dev evaluation.
The data contains no opt-05 and no dev family. Training on it took place before the xAI terms check in decision 4 was recorded.

Options:
- (a) **Retire it as training input.** Never reuse `04f69de7...` for training, keep the files as an audit record, and delete nothing.
- (b) Keep it for evaluation and analysis only.
- (c) Allow reuse in Round 2, conditional on decision 4 = (d) or (e).
- Separately: the disposition of the shelved adapter (keep shelved, or quarantine it as derived from Grok output). It stays on the PC either way.

Proposed: (a), with the adapter kept shelved and unexported. **Owner choice:** ________

## Other gates that remain open (not decided here)

- Real round-zero student attempts are still missing: all 689 `student_answer`s are synthetic Grok Bot stand-ins.
- The 72 independently authored locked-test families do not exist.
- A non-drafter has not re-read the two hand-proof sketches and the six near-duplicate prompt pairs in `dedupe-audit.json`.
- Per-family admission decisions have not been made.

## Owner signature

I have read the decisions above. Only the families and variants I listed as admitted may be used, and only as I specified.

Owner: ____________________  Date/time (ET): ____________________  Signoff phrase: ____________________
