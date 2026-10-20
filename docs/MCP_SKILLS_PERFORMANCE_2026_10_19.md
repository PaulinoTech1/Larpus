# MCP Skills measurement — 2026-10-19

No chat speedup is established by this extension. It adds metadata/resource discovery,
not extra discovery calls to chat. Model selection, prompts, inference options, retrieval,
screening and CPU voice remain on the existing paths.

`scripts/benchmark_mcp_skills.py` is plan-only by default. `--run` compares prepared local
release IDs through the same fixed MCP executor, in alternating A/B order. Warmups are
excluded, failed attempts remain in denominators, missing stages are not zero and
p90/p95 use nearest rank. Private receipts retain answers, evidence and chunk arrival times.
An interrupted or identity-changing run cannot be a valid comparison. Answer quality
requires the existing rubric and supporting passages; citation identifiers alone do not prove it.

Standalone validation timings and live results are recorded separately.
Do not label standalone loader cost as an inference stage or compare candidate MCP timing
against baseline HTTP as a causal effect. Candidate HTTP/browser validation awaits activation.

Windows Python 3.10 standalone profile: ten measured trials after one excluded warmup.
Full-registry validation median was 185.184 ms (p95 190.401 ms); selected-prompt
validation median was 216.987 ms (p95 241.760 ms). Persona setup was outside the
selected-operation timer. These are descriptive host measurements, not isolated Linux
or end-to-end gains. The first profiler version also timed persona loading and is
retained as an invalid selected-operation comparison; it was not used to justify optimization.

No cross-request validation cache or optimization variant C has been adopted. Repeated
verification remains mandatory; a C candidate needs a measured, safe operation-local saving
and separate equivalence, tamper, review and prepared-release evidence.

The sealed Linux loader profile also used ten measured trials and one excluded warmup.
Baseline full/selected medians were 94.721/95.032 ms; candidate medians were
98.113/94.359 ms. These small mixed differences do not establish a useful loader gain.
The selected-prompt operation still performs fresh approval and integrity checks.


## First focused live run

Receipt `5be1c6aa433246e4a017e950fee903fe`: 42/42 completed replies,
six measured rounds per case after one excluded warmup. Before/after identities
remained stable and A/B base instruction, source/config/model and SDK pins matched.
All calls used the existing fixed sealed MCP executor and the selected 3.8 model.

| Case | A median first text (s) | B median first text (s) | Change |
| --- | ---: | ---: | ---: |
| Home planning | 6.166 | 6.894 | +11.8% |
| Cyber interview | 6.587 | 6.747 | +2.4% |
| Differential equations | 6.589 | 6.421 | -2.5% |

Home exceeds the registered +5% review threshold. Its chunk-gap p95 also rose
about 10.9%, triggering the single predeclared identical-protocol confirmation.
That run remains separate; a later result cannot erase this receipt.

AI rubric review read all 36 measured answers and 13 distinct retained source
records. This was not independent human validation. Both snapshots have quality
limits, including arithmetic/verbosity issues and unsupported or imprecise math
attribution. Candidate samples include an incorrect "equilibrium at infinity"
claim and a 30-minute interval described as 40 minutes. No factual-accuracy
percentage or answer-quality improvement is established.

Complete retained source objects matched in 12/18 pairs (home 6/6, math 5/6,
cyber 1/6). Exact source-code/image checks and live scorer observations matched;
both used Assembly optimized. A separate no-generation diagnostic observed
4/16 reranking pairs skipped under the existing deadline in each snapshot.
A diagnostic-only five-second budget processed all pairs and produced matching
alternative reference sets. This supports a timing-sensitive retrieval hypothesis,
but does not prove the cause of every original difference. Production budgets,
prompts and guards were not changed. End-to-end quality equivalence remains unresolved.


## Registered focused confirmation

Receipt `f2cb733c090940898687f938e0b6c66e`: 42/42 completed replies;
identities stable, same protocol, no changed settings or prompts.

| Case | A median first text (s) | B median first text (s) | Change |
| --- | ---: | ---: | ---: |
| Home planning | 6.645 | 6.439 | -3.1% |
| Cyber interview | 7.203 | 6.699 | -7.0% |
| Differential equations | 6.158 | 6.891 | +11.9% |

Home chunk-gap median rose from 0.338 to 0.393 seconds (about 16.4%);
its p95 improved from 1.083 to 1.002 seconds. Math now exceeds the first-text
review threshold, while the first run's Home regression did not repeat.
The result is mixed and does not establish stable latency neutrality or a
causal code regression. No further focused retry is planned, and the first
receipt remains part of acceptance. The candidate stays inactive.


The confirmation's 36 measured answers also received AI rubric review (72 focused
answers reviewed across both runs). Exact source records matched 16/18 confirmation
pairs. Additional issues included a candidate claim that an initial perturbation
must eventually dominate the solution (relative error is constant when the initial
value is nonzero), overbroad existence reasoning, and planning arithmetic/supervision
ambiguities in both snapshots. These findings prevent a blanket quality-preservation
claim; they do not isolate the MCP extension as their cause. Full private per-answer
scores, hashes, source records and reviewer notes are retained.

## Eight-case matched MCP run

Receipt `0ee36cd72370485282f1abae38c281ae`: valid stable identities,
64/64 completed replies, including 16 excluded warmups and 48 measured answers.
Each case has three measured samples per snapshot; this is a small descriptive
sample, not a statistical estimate of a causal code effect.

| Case | A median first text (s) | B median first text (s) | Change |
| --- | ---: | ---: | ---: |
| Greeting | 5.680 | 6.217 | +9.5% |
| Norms | 7.040 | 7.698 | +9.3% |
| Stability pushback | 7.247 | 6.217 | -14.2% |
| Context follow-up | 6.248 | 7.616 | +21.9% |
| SOC | 7.220 | 7.679 | +6.4% |
| Governance | 6.256 | 7.314 | +16.9% |
| Pentest | 5.800 | 6.632 | +14.4% |
| Knowledge gap | 5.828 | 6.736 | +15.6% |

Seven cases cross the registered +5% first-text review threshold. Norms gap p95
rose 1.782 to 2.171 seconds; context gap p95 rose 0.533 to 0.588; governance
gap median rose 0.351 to 0.408; knowledge-gap p95 rose 0.698 to 0.802.
Other cadence metrics improved or changed less. Greeting produced no inter-chunk
gaps, so its cadence is unavailable, not zero. These observations trigger the
single registered existing-eight confirmation. No automatic promotion follows.

AI rubric review covered all 48 measured answers and 35 distinct retained source
records; exact evidence matched in 23/24 A/B pairs. The differing pair was
stability round 1. Norm answers were correct and supported by the retained
passages. Both versions mishandled planning arithmetic in some follow-ups and
accepted misleading "simultaneous instability detection" framing. Other issues
included consistency presented as reliability, human review conflated with
automatic learning, and a citation used beyond its retained support. This is
AI review, not independent human validation or an accuracy percentage.

## Separate baseline HTTP regression

Receipt `f7ebb4535ecc41f387fc2cb84555f4a5`: valid stable run, 32/32
completed replies, eight excluded warmups and 24 measured samples. The selected
release, GPU model, corpus and settings stayed fixed. No candidate HTTP listener
or activation was used; these values cannot establish the extension's effect.

| Case | Median first text (s) | p90 first text (s) |
| --- | ---: | ---: |
| Greeting | 6.775 | 7.565 |
| Norms | 8.796 | 8.824 |
| Stability pushback | 6.858 | 9.586 |
| Context follow-up | 6.848 | 8.363 |
| SOC | 7.919 | 7.949 |
| Governance | 6.817 | 7.214 |
| Pentest | 7.205 | 8.172 |
| Knowledge gap | 6.810 | 7.925 |

Each row has three measured samples. Complete stage timings were present for all
24 measured replies; overlapping stages must not be summed. Browser paint,
physical speech and second-device behavior were not measured. The direct owner
CLI initially failed to import its package when launched by filename; a repository
root bootstrap fixes that invocation. Its dry-run and this live run then passed.

AI review covered all 24 measured HTTP answers and 35 distinct source records;
coverage, five rubric scores per answer, input and answer hashes were verified.
Context arithmetic and norm examples were correct. Stability explanations still
confused a finite-time magnitude comparison with an asymptotic stability test.
Other issues included premature dismissal after one failed reproduction and
claims exceeding citation support. The review agent wrote its complete receipt
before hitting its usage limit; the owner agent verified receipt coverage and
hashes. This remains AI review and separate baseline evidence, not candidate
quality equivalence or independent human validation.

## Registered eight-case confirmation and decision

Receipt `1fcd8183ba454ef7bedd9afcc2b45ba0`: valid stable identities,
64/64 completed replies with the same 16 excluded warmups and 48 measured samples.
This is the single allowed confirmation for this catalog; both receipts remain.

| Case | A median first text (s) | B median first text (s) | Change |
| --- | ---: | ---: | ---: |
| Greeting | 6.152 | 6.157 | +0.1% |
| Norms | 8.250 | 8.090 | -1.9% |
| Stability pushback | 5.333 | 6.579 | +23.4% |
| Context follow-up | 5.896 | 6.553 | +11.2% |
| SOC | 6.382 | 6.939 | +8.7% |
| Governance | 6.781 | 6.670 | -1.6% |
| Pentest | 6.085 | 6.728 | +10.6% |
| Knowledge gap | 5.994 | 6.375 | +6.4% |

Five cases still cross +5%. Context gap median/p95 rose 0.379/0.490 to
0.529/0.804 seconds; SOC median rose 0.629 to 0.802; governance median rose
0.397 to 0.543. Several other cadence measures improved. Small samples, shared
model caching, order and deadline-sensitive evidence limit causal attribution;
three rounds alternate order but cannot perfectly balance first position.
No further retry is planned. Stable latency neutrality is not established.

The primary AI assistant reviewed all 48 measured confirmation answers; evidence
matched in all 24 pairs and contained no new source records beyond prior reviews.
Math norm examples were correct, but stability framing remained misleading.
Baseline context arithmetic and false-negative testing contained errors; candidate
governance overstated what encryption prevents. One baseline SOC answer used an
unknown shortened citation. Other references were valid identifiers with partial
claim support. The private report contains individual five-dimension scores,
notes and hashes. This remains AI review, not independent human validation.

Across the five completed benchmark runs, 244/244 calls delivered replies:
52 warmups were excluded and all 192 measured answers received AI rubric review.
Successful delivery is not factual correctness. Candidate
`c7a16c1c9fbc408199b1d05a57d15244` remains prepared and **inactive**;
performance consistency and blanket quality preservation are not accepted.
No optimization C, validation cache, prompt change or weakened guard was adopted.

The later lifecycle check exposed whole-pod startup reviving retained historical
containers. The paired runs did not isolate that factor, and their receipts are
not rewritten or promoted into a causal speed claim after the startup correction.
Startup observations are separate from these warm-workload comparisons; see
[controlled restart evidence](BROKER_COLD_START_RECOVERY_2026_10_19.md).
