# Local multi-turn RAG evaluation, inspired by MTRAGEval

Status (2026-10-25): scoped capability probes remain checkout-only. Catalog
validation and seven focused unit tests passed on October 25; **no model-backed
A/B/C run or human answer review** has been performed for this status update.
The original owner instruction deferred GPU-backed and latency tests while Grok
Bot fine-tuning was in progress. Pilot1 has since been shelved; this status note
authorizes no live run or release activation. This is a local adaptation of the
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
python -m scripts.mtrageval_local run-c RUN_ID --arm baseline --repeats 3 --tuning-finished --quiet-window
python -m scripts.mtrageval_local run-a RUN_ID --arm baseline --repeats 3 --tuning-finished --quiet-window
python -m scripts.mtrageval_local run-b RUN_ID --arm baseline --repeats 3 --tuning-finished --quiet-window
# Switch models only through the separately approved local model-selection procedure.
python -m scripts.mtrageval_local run-c RUN_ID --arm candidate --repeats 3 --tuning-finished --quiet-window
python -m scripts.mtrageval_local run-a RUN_ID --arm candidate --repeats 3 --tuning-finished --quiet-window
python -m scripts.mtrageval_local run-b RUN_ID --arm candidate --repeats 3 --tuning-finished --quiet-window
```

`run-c` takes a station identity snapshot before and after each arm. A changed
snapshot makes that arm unstable for comparison. The two flags are owner
attestations, not automatic detection that training has ended or the GPU is
idle. Check those conditions before launching. Run A/B after C for each arm;
they require the same station identity and a release whose sealed agent image
contains `runtime.rag_eval`. The current active frozen release
`6200bb30d68348f080f2c1c723ff2fb6` lacks `runtime/rag_eval.py`, so the
A/B commands are **not yet runnable against it**. A later
stage/prepare and separate owner-approved activation are needed before a live
probe; building this code has not changed the serving release.

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
A retrieves at most LARPUS's current three selected passages; B uses explicit
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
