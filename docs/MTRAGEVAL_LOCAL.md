# Local multi-turn RAG evaluation, inspired by MTRAGEval

## Configuration follow-up - 2026-10-29

The current selected release is `1022de11b0df4ce6be2915f49f1286ba`.
The October 27 run described below is historical and must remain unchanged.
A new baseline must use a new run ID; do not append attempts from the new
release to that old station identity. No new live run or training is implied
by validation, deferred configuration, or these commands.

The runner's default minimum interval between generation starts is now six
seconds for C and B. Set `--minimum-start-interval 6` explicitly in the live
commands below; values from 6 through 60 are accepted. A performs retrieval
without generation pacing. The interval is recorded with the C arm, B must
use that same interval, and a comparison requires matched pacing across arms.
Pacing wait occurs before the timed probe, so it is not response latency.

This addresses a configuration risk: a fast 15-attempt B task can otherwise
exceed the broker's 12 requests / 12288 reserved output tokens per minute.
With 1024 output tokens reserved per request and exclusive use of the lane,
six-second starts leave margin under both limits. A quiet window and cleared
prior budget are still necessary; other consumers can still cause holds.
The old B holds were attempts 13-15, consistent with budget exhaustion, but
the original receipts contain only `sealed_agent_held`, so that cause is not
proven. Do not erase those failures or weaken broker limits.

C now retains bounded refusal codes, correlation IDs and HTTP statuses when
available, saving failed-attempt metadata separately without saving partial
reply text. This permits distinguishing budget holds from cancellation faults
on a new run. No automatic retries or direct model fallback are added.

The five-case configuration uses three repeats in order C, A, B: 45 total
attempts for one baseline. Human correctness/support review remains unset.
The current comparison gate is for distinct model weights with matched
retrieval/corpus/context pins. A same-model retrieval experiment needs a
separately defined comparison contract; do not relabel it as a tuned-model
comparison or relax the gate merely to obtain `comparison_ready`.

Status (2026-10-27): the active release
`882c959c3d4540a5ba4b4b89f1596b17` contains `runtime/rag_eval.py`. The older
note that release `6200bb30d68348f080f2c1c723ff2fb6` cannot run A/B is
historical. Task C originally failed closed on the Qubes answerable case
because the synthetic assistant line "specifications you supply" scored
0.6728 for injection. Horizon removed that setup turn, and the runner
treated the quarantine event as `invalid_protocol`, so the case produced no
completed measurement. The fixture now states that exact figures depend on
the versioned source, which scored 0.0018. The 0.5 label boundary is
unchanged. Human review of answer quality is still unset. Baseline run
`b11d49d6604d420fb84bb65f551f7e37` on that release completed task C 15/15
and task A 15/15. Task B completed 12/15; the three holds were repeat 3 of
the empty-evidence cases and were not reproduced by one immediate retry.
`qubes-requirements` included its gold source on all three A repeats and all
three C repeats. `qubes-followup`, whose last turn is only "And how much
storage does it call for?", included that gold source on none of the six A
or C repeats. Both tasks returned the same four MIT passage IDs instead.
That is the multi-turn retrieval gap this probe is meant to show. The
checkout now carries a platform named in an earlier user turn into the
retrieval query when the latest turn names none. Assistant text is not
used, and the model still sees the original question. A later release is
required before the live agent uses that rule. No
candidate arm was run, and `comparison_ready` is false. This is a local
adaptation of the
three-task design in [MTRAGEval, SemEval 2026](https://aclanthology.org/2026.semeval-1.447/),
**not** an official leaderboard run or a reproduction of its dataset. Its five
public synthetic cases are smoke fixtures, not a statistically representative
benchmark or secret held-out set.

## Purpose and boundary

MTRAGEval separates A (retrieval), B (generation with supplied evidence) and C
(end-to-end retrieval plus generation). Its question classes include answerable,
unanswerable, underspecified, non-standalone and unclear multi-turn requests.
The local [catalog](../evals/mtrageval-local.json) has one of each class.

The [runner](../scripts/mtrageval_local.py) provides catalog validation, a
deferred run manifest, local A/B probes, C capture through the existing checked
owner-loopback streaming API, manual review, and reporting with failures retained
in the denominator. A/B run through [the sealed-agent probe](../runtime/rag_eval.py),
which is not an MCP tool or gateway route. A calls the same approved retrieval
function as normal chat and records the selected passage IDs and locators. It uses
only the latest user question, exposing whether LARPUS presently fails to resolve
a multi-turn reference in retrieval. B selects exact passages by ID and locator
from the hash-verified approved database. LARPUS's normal persona, input filter,
broker, GPU-placement check and output DLP remain in the generation path, but
normal retrieval is omitted. Empty B selections test how LARPUS handles absent
evidence. These probes assess LARPUS capabilities; they do not implement the
organizers' corpora, full passage-ranking protocol or scoring.

The probe changes an internal inference call contract, but no ordinary MCP client
can pass `fixed_selectors`. The normal path still calls `augment` without an
override. Exact approved passage text is attached only as untrusted
`LOCAL_REFERENCE_DATA` in the user message, never as system instructions. This
adds no evidence tokens to ordinary production requests. Evaluation requests
consume CPU and, for B/C, GPU resources and can disturb tuning or latency.
Generated answers and screened source previews stay under ignored
`data/evals/mtrageval/<run-id>/` for owner review. Imported third-party A/B
receipts remain operator claims and are distinguished from local execution.
Until paired runs and human reviews exist, `comparison_ready` remains false.

## Deferred owner workflow

These commands do not start inference:

```powershell
python -m scripts.mtrageval_local validate
python -m scripts.mtrageval_local prepare
python -m scripts.mtrageval_local report RUN_ID
```

After tuning ends, freeze the baseline and candidate model identities, corpus,
retrieval settings, personas, sampling and questions. Keep the original model
available. In a quiet window, run one arm at a time; the script neither switches
models nor activates a release:

```powershell
python -m scripts.mtrageval_local run-c RUN_ID --arm baseline --repeats 3 --tuning-finished --quiet-window --minimum-start-interval 6
python -m scripts.mtrageval_local run-a RUN_ID --arm baseline --repeats 3 --tuning-finished --quiet-window --minimum-start-interval 6
python -m scripts.mtrageval_local run-b RUN_ID --arm baseline --repeats 3 --tuning-finished --quiet-window --minimum-start-interval 6
# Switch models only through the separately approved local model-selection procedure.
python -m scripts.mtrageval_local run-c RUN_ID --arm candidate --repeats 3 --tuning-finished --quiet-window --minimum-start-interval 6
python -m scripts.mtrageval_local run-a RUN_ID --arm candidate --repeats 3 --tuning-finished --quiet-window --minimum-start-interval 6
python -m scripts.mtrageval_local run-b RUN_ID --arm candidate --repeats 3 --tuning-finished --quiet-window --minimum-start-interval 6
```

`run-c` takes a station identity snapshot before and after each arm. A changed
snapshot makes that arm unstable for comparison. The two flags are owner
attestations, not automatic detection that training has ended or the GPU is
idle. Check those conditions before launching. Run A/B after C for each arm;
they require the same station identity and a release whose sealed agent image
contains `runtime.rag_eval`. Active release `882c959c3d4540a5ba4b4b89f1596b17` includes
`runtime/rag_eval.py`, so A/B can run against that sealed agent. A release
that does not contain that file still refuses A/B.

A/B can also accept independently produced receipts with `import-task RUN_ID
RECEIPT.json`; those are explicitly labeled operator supplied and are not
independent proof of execution. Each arm/task/repeat/case key is unique; a retry
needs a new run, preserving failed attempts. No result is automatically marked
correct.

Human reviewers should score answer correctness and passage support separately,
record the decisive evidence, and leave uncertain cases unresolved. Record a
review without editing JSON by using `review RUN_ID --arm baseline
--task C --case qubes-requirements --repeat 1 --reviewer OWNER --note "Checked
against the cited passage" --correct yes --supported yes`. For task A,
`--correct` means the retrieved set addressed the question; for B/C it means
the answer was correct. A reviewer must inspect the private completed answer
and actual original passage before marking B/C support. The two Boolean fields
cannot encode uncertainty; leave the review unset when evidence is inconclusive.

The report shows source-ID complete hits only as a retrieval diagnostic. It does not infer
claim support from a matching ID. Compare per-class failures, complete hit rate,
human-reviewed correctness/support, prompt tokens, first-text and completion
distributions. Report absent token counts as missing, never as zero. Three repeats
per case expose variability; they are not independent questions or a stable p95.
A records at most three approved passages plus two study notes, which is
the live retriever's own cap. B uses explicit
fixtures from the catalog. A/B timings are measured within the sealed probe and
exclude owner-to-container launch and gateway handling, so they must not be
presented as end-to-end response latency. C supplies that measurement.

## Completion gate

To call this a matched A/B/C result, both arms need all cases in each task,
matched repeat schedules, stable C station identities, A/B corpus fingerprints
matching each arm's C snapshot, matching source/context/retrieval/index pins across
arms, distinct recorded model weights, B model hashes matching that snapshot, identical
fixed-evidence packet hashes across arms, no failed/held responses and completed
human reviews. The harness enforces these accounting gates but does not approve
production promotion. Separate answer-quality, latency and security acceptance
from a tuned-model experiment still apply under
[the tuning loop](GROK_TEACHER_TUNING_LOOP.md).
