# LARPUS performance baseline - 2026-10-17

Larpus 3.8 completed all 24 measured requests in this fixed local API workload.
Median time to first checked text was **6.726 seconds**; median completion was
**9.064 seconds**. This is the first suite baseline, not evidence of improvement
over an earlier configuration.

## Conditions and provenance

| Setting | Recorded value |
| --- | --- |
| Run ID | `34ee0f7d916945ddba4b94eb2333ac2f` |
| Active frozen release | `690d8bcbedcd4ff2a0f710b8fedaaa83` |
| Run window | October 17, 2026, 7:07:49-7:12:45 PM EDT (America/New_York) |
| Model | Larpus 3.8 27B Q4; GPU-ready before and after |
| Context setting | 131,072 tokens |
| Observed WSL processors | 20 logical processors |
| Retrieval threads / rerank batch | 8 / 4 |
| Lexical / semantic candidates | 10 / 6 |
| Shared semantic/reranking budget | 0.9 seconds; an in-progress batch can exceed it |
| Measured workload | 8 cases, 3 rounds, seed 5900 |
| Conditioning | 1 request per case, excluded from measured distributions |
| Concurrency | Sequential requests to the fixed localhost streaming API |

The [hardware investigation](CPU_TUNING.md) recorded a Ryzen 9 5900X with 12
physical cores and 24 logical threads. The WSL limit does not reserve four
dedicated host cores. Conditioning did not unload the model or erase caches.
Other load was not isolated: the broader Python checks ran during part of this
live workload.

Release, gateway PID, selected model, context, retrieval settings and corpus
identity matched before and after the run. Exact model, corpus and benchmark
hashes remain in the private `report.json`. Request order was reproducibly
shuffled within each measured round.

## Overall results

| Metric | Result |
| --- | ---: |
| Measured requests completed | 24 / 24 |
| Recorded failures | 0 / 24 |
| Complete stage-timing records | 24 / 24 |
| First checked text, median | 6.726 s |
| First checked text, p90 | 7.718 s |
| First checked text, minimum / maximum | 5.651 / 8.380 s |
| Complete reply, median | 9.064 s |
| Complete reply, p90 | 10.258 s |
| Complete reply, minimum / maximum | 5.880 / 11.447 s |
| Unknown citation identifiers | 0 / 24 responses |

All eight conditioning requests also completed. Completion means nonempty checked
text followed by a valid `done` event, not a factually correct answer. Zero
observed failures in 24 requests is not a production reliability guarantee.

## Per-case results

Each row has three measured requests. With this sample size, nearest-rank p90 is
the largest observation, not a stable tail-latency estimate.

| Case | Completed | First-text median (s) | First-text p90 (s) | Completion median (s) |
| --- | ---: | ---: | ---: | ---: |
| Greeting | 3 / 3 | 5.988 | 6.213 | 6.203 |
| Vector norms | 3 / 3 | 7.579 | 7.718 | 9.790 |
| Stability correction | 3 / 3 | 6.017 | 6.327 | 7.876 |
| Conversation context | 3 / 3 | 6.660 | 7.021 | 8.614 |
| SOC validation | 3 / 3 | 6.768 | 7.617 | 8.573 |
| AI governance | 3 / 3 | 6.764 | 7.035 | 9.485 |
| Authorized pentest lab | 3 / 3 | 6.971 | 7.224 | 9.727 |
| Missing SOC knowledge | 3 / 3 | 8.270 | 8.380 | 10.242 |

## Stage measurements

These are elapsed-time scopes, not CPU-utilization measurements. Some scopes
contain others; their medians must not be added to reconstruct request latency.
Every stage had 24 observations.

| Stage | Median (ms) | p90 (ms) |
| --- | ---: | ---: |
| Input preparation/checks | 0.267 | 0.376 |
| Retrieval/augmentation/screening | 2268.818 | 2474.955 |
| Model selection | 50.230 | 52.580 |
| Generation start to first frame | 1353.759 | 1806.816 |
| Inference entry to first checked text | 4334.024 | 5294.822 |
| Total inference | 6445.309 | 7502.092 |
| Isolation preflight | 1432.995 | 1594.952 |
| MCP connection | 990.643 | 1094.364 |
| Total MCP operation | 8800.712 | 10048.797 |

Generation-to-first-frame includes admission, queueing, prefill and transport.
The API first-text measurement includes the surrounding request path and stops
before physical browser paint. See [timing definitions](CPU_TUNING.md#instrumentation).

Retrieval, isolation preflight and MCP startup are useful targets for controlled
follow-up experiments. These observations do not prove that increasing threads
will shorten replies.

## Answer-quality spot review

One first-round answer per case was reviewed: **8 of 24 measured answers**.
Sixteen remain unscored. Five dimensions were scored 0-2: factual accuracy,
grounding, uncertainty, usefulness and instruction following. The mean
**8.75/10** is an assistant rubric judgment, not an accuracy percentage or
independent expert validation. Grounding was checked against retained screened
passages; arithmetic and scalar-norm facts were also checked by direct reasoning.

| Case | Rubric score /10 |
| --- | ---: |
| Greeting | 10 |
| Vector norms | 9 |
| Stability correction | 9 |
| Conversation context | 9 |
| SOC validation | 9 |
| AI governance | 5 |
| Authorized pentest lab | 10 |
| Missing SOC knowledge | 9 |

- The governance answer used a valid FIPS203 citation identifier, but the retained
  excerpt did not support its AI data-leak prevention claim. Identifier consistency
  did not detect this support problem.
- Three of eight reviewed answers exceeded their requested sentence count.
- The scalar ODE answer correctly calculated the perturbation and equated scalar
  Euclidean/max norms, but retained imprecise finite-time instability wording.
- The SOC answer needed explicit missed-threat measurement and a stronger
  pre-closure approval boundary. The knowledge-gap answer admitted absent access
  but should request sanitized records.

## Interpretation and next measurements

This establishes a reproducible baseline for this station and workload. It does
not establish a speedup from the 20-processor limit, maximum throughput,
concurrent-user capacity, cold-load behavior, long-context capacity, physical
browser rendering time, microphone behavior, or speech-start latency.

Prioritize source-to-claim support and sentence-limit adherence alongside latency.
Evaluate retrieval and MCP startup changes against the same workload, retaining
failure counts and quality review. A faster reply that skips useful evidence is
not automatically better. Cache history and competing work must be considered
when comparing runs.

## Reproduce and inspect

```powershell
python -m scripts.performance_suite --run --repeats 3 --warmups 1 --retain-answers --baseline 34ee0f7d916945ddba4b94eb2333ac2f
```

Comparison requires matching workload/runner hashes, repetition/warmup counts and
seed. Cross-run station changes are listed explicitly; timing differences do not
establish causality. See the [suite guide](PERFORMANCE_SUITE.md).

Primary evidence is under the ignored owner directory
`data/evals/performance/34ee0f7d916945ddba4b94eb2333ac2f/`: `report.json`,
`observations.jsonl`, `summary.md`, `review.json` and `quality-review.md`.
`answers.jsonl` contains completed fixed-test answers and screened references;
those private contents are not reproduced here.

`data/performance-suite-tests-final.log` records 300 Python tests with two
existing skips. `data/performance-suite-live.log` records the successful live run.
The complexity gate passed. This documentation update does not rerun inference,
change production, or claim a clean security audit.
