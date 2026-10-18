# Measuring LARPUS responses

See the [dated performance baseline](PERFORMANCE_BASELINE_2026_10_17.md) for the
recorded conditions, full results, stage measurements and answer-quality findings.

The owner-local suite tests the running station through its fixed localhost HTTP
streaming API. It does not deploy, switch models, unload GPU weights, change CPU
limits, install packages, or expose an endpoint. Keep the current gateway/model/
voice running. Requests use real inference sequentially and can compete with an
interactive user. A busy or held request is a recorded failure, not an automatic
retry. An exit code of zero means the run completed stably without failed requests;
it does not certify a latency target or factual accuracy.

```powershell
# Plan only: eight cases, eight conditioning requests and 24 measured requests.
python -m scripts.performance_suite

# Run the approved baseline with owner-only answer retention for review.
python -m scripts.performance_suite --run --repeats 3 --warmups 1 --retain-answers

# Same workload and runner, compared with a previous 32-hex run ID.
python -m scripts.performance_suite --run --repeats 3 --warmups 1 --retain-answers --baseline RUN_ID
```

Default seed is 5900. Warmups exercise every case once; each measured round uses
a reproducibly shuffled order. These are conditioning requests, not guaranteed
cold starts. The suite deliberately does not unload the active model or erase
caches. Record external station use and other load when comparing runs.

## Cases and measurements

The public case catalog is `evals/performance.json`:

| Case | Main purpose |
| --- | --- |
| home-greeting | Simple first-text baseline |
| home-norms | Basic learning and a concrete example |
| home-stability-pushback | Correct the scalar Euclidean/max norm misconception |
| home-context | Use prior conversation and fit 75 minutes of tasks into 60 |
| cyber-soc | Validate AI triage with evidence and human oversight |
| cyber-governance | Data, approval and audit controls in a fictional company |
| cyber-pentest | Independently validate findings in an authorized isolated lab |
| cyber-knowledge-gap | Admit absence of live SOC telemetry |

The suite reports first checked text and total request times, per-case median,
nearest-rank p90, minimum, maximum and sample count. With three samples, per-case
p90 equals the largest observation; it is not a tail-latency guarantee. The pooled
summary describes this equal-weight fixed workload, not all possible chat usage.

Success requires a completed `done` event after nonempty checked text. HTTP
rejection, interrupted/truncated streams, protocol errors, transport failures and
operator cancellation stay in the denominator. Partial failed replies are not
included in successful latency distributions or saved as completed review answers.
Missing timings remain absent; they are never replaced with zeros. Raw partial
observations are flushed after each request. An interrupted run is invalid for
comparison even if its completed samples were successful.

Stage names and overlap follow [CPU timing](CPU_TUNING.md). Stage counts show
measurement coverage. These are API measurements, excluding physical browser
paint, microphone behavior and speech playback. Unknown citation identifiers are
a mechanical check, not a factual-answer score.

The report records the active frozen release, source fingerprint, gateway PID,
selected model and weight identity, context, retrieval settings, approved corpus
and embedding/note manifest identities, WSL configuration and observed CPU count.
It captures station identity before and after the run. A changed identity or an
incomplete schedule invalidates the comparison. Workload and benchmark-source
hashes, repetition counts, warmup counts and seed must match across compared runs.
Cross-run station changes are explicitly listed: same workload does not imply
identical environments or prove which change caused a timing difference.

## Reports and answer review

Each run gets a fresh directory at `data/evals/performance/<RUN_ID>/`:

- `report.json`: numeric summary, provenance and optional baseline comparison.
- `summary.md`: readable per-case table and stage medians.
- `observations.jsonl`: flushed numeric observations, including failures/warmups.
- `review.json`: five-dimension manual quality rubric and unscored sample records.
- `answers.jsonl`: only with `--retain-answers`; completed fixed-test answers and
  their screened reference previews, stored in ignored owner data.

No existing user conversation, recording or credential is read into test cases.
The numeric files do not contain generated answer text or retrieved passages.
Retained references are untrusted data for inspection, never instructions to
execute. Do not publish private answers or passage previews with the public suite.

Review each released measured answer against the case's explicit review points
and its original supporting passages. Score factual accuracy, grounding,
uncertainty, usefulness and instruction following from 0 to 2 each. Record a
reviewer and evidence notes. A total out of ten is a rubric judgment, not an
accuracy percentage, safety certification or independent expert evaluation.
Leave unknown dimensions unresolved rather than guessing. Failed requests remain
reliability failures; do not count absent answers as correct quality samples.

There is intentionally no keyword-based factual pass or automatic LLM judge.
Unfilled reviews stay pending. Cite the reviewed sample count separately from
the total measured request count when publishing quality observations.

## Verification

`python -m unittest tests.test_performance_suite -v` checks failure/warmup
accounting, missing data, truncation and rejection, reproducible scheduling,
comparison identity disclosure, cancellation, separate answer retention and
partial-report validity. These checks are also discovered by the existing public
Python test runner. The live suite adds actual local API evidence; it is not a
concurrent load test, physical browser test, or broad adversarial security audit.

## First completed baseline, 2026-10-17

Run `34ee0f7d916945ddba4b94eb2333ac2f` used active release
`690d8bcbedcd4ff2a0f710b8fedaaa83`, Larpus 3.8, 20 observed WSL processors,
eight retrieval threads and batch four. Station identity remained stable. All
24 measured requests and eight excluded conditioning requests completed; all
24 measured successes contained the expected stage fields. There were no unknown
citation identifiers, which does not establish citation support.

| Case | First-text median (s), n=3 | Completion median (s) |
| --- | --- | --- |
| Greeting | 5.988 | 6.203 |
| Vector norms | 7.579 | 9.790 |
| Stability correction | 6.017 | 7.876 |
| Conversation context | 6.660 | 8.614 |
| SOC validation | 6.768 | 8.573 |
| AI governance | 6.764 | 9.485 |
| Authorized pentest lab | 6.971 | 9.727 |
| Missing SOC knowledge | 8.270 | 10.242 |

Across this fixed workload, first-text median/p90 were 6.726/7.718 seconds;
completion median/p90 were 9.064/10.258 seconds. Stage medians included retrieval
2268.818 ms, preflight 1432.995 ms, MCP connection 990.643 ms and generation to
first frame 1353.759 ms. Do not add overlapping stage medians to derive a total.
These numbers are a baseline, not an improvement claim or capacity guarantee.

An assistant spot review of one first-round answer per case scored 8.75/10 on the
stated rubric; that is not a factual-accuracy percentage or independent expert
validation. Sixteen measured answers remain unscored. The governance example
scored 5/10: its retained FIPS203 excerpt did not support its AI data-leak
prevention claim. Three of eight reviewed outputs exceeded the requested sentence
count. The scalar ODE answer correctly computed the perturbation and equated the
two scalar norms, but retained imprecise finite-time instability wording.

Private evidence is in `data/evals/performance/34ee0f7d916945ddba4b94eb2333ac2f/`:
`summary.md`, `report.json`, `observations.jsonl`, `answers.jsonl`, `review.json`
and `quality-review.md`. The answer file is Git-ignored. All 300 public Python
tests completed successfully with two existing skips, and the complexity gate
passed. These are owner-side tools; no application activation, model switch,
processor change, commit or push was needed for this suite.
