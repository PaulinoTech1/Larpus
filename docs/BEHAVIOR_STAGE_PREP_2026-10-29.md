# Behavior-stage preparation, 2026-10-29

Release `1022de11b0df4ce6be2915f49f1286ba` was running. Health returned 200.
The served model was `larpus3.8:27b-q4` on GPU. No adapter was trained and no
model was switched.

## Release smoke

The eight public math and quantum cases in `evals/companion.json` were sent
through the live verified gateway. These cases are a smoke test. They are
already public, so they are not a locked test. Answers were not retained.
Mechanical result: 8/8 returned text. No input quarantine, no stream error,
and no HTTP hold.

| Case | First text | Completion | Characters |
| --- | ---: | ---: | ---: |
| math-limit | 19.233 s | 45.217 s | 2894 |
| math-ode | 13.304 s | 37.428 s | 2966 |
| math-integral | 10.861 s | 18.443 s | 782 |
| math-unsupported | 13.135 s | 19.651 s | 1225 |
| quantum-normalization | 13.376 s | 26.643 s | 1483 |
| quantum-sign | 12.625 s | 26.175 s | 1486 |
| quantum-perturbation | 12.922 s | 28.231 s | 2266 |
| quantum-experiment | 12.417 s | 21.510 s | 1803 |

`math-limit` and `math-ode` are long for a behavior target that wants the
decisive step first. Length is not a correctness score. A person still has
to score assumptions, false premises, checks, and evidence qualifications.

Private timing receipt: `data/evals/behavior-smoke-1022de11.json`.

## What the next stage is

Behavior tuning compares an untuned baseline with a prompt or teaching-profile
control before any weights change. The linear-algebra bank validated. A
deferred comparison was prepared at
`data/evals/behavior-comparison-deferred-20261029.json`. It makes no model
calls. Live scoring waits until note generation for the current source
collection is finished and the bank has been reviewed. The run command in
`docs/CAPABILITY_TRIALS.md` is unchanged.

Do not treat the 2026-10-22 family packet as this dataset. Its student
answers are synthetic, its rights fields are null, and `grok-r1-opt-05/d`
is held. The follow-up retrieval change is still only in the checkout, so a
retrieval miss must not be labeled as a behavior error of the model.
