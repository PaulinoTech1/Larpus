# Source chronology, corrections and authorship

Source processing uses recorded publication/revision dates, oldest first, with
undated sources last. Retrieval still selects relevant passages; selected
references are presented chronologically. Snapshot dates are not publication
dates. A newer paper does not automatically invalidate older work. Version
branches such as Ubuntu releases can remain valid alongside one another.

## Why this changed

The remaining note workload is substantial. Adding provenance before resuming
avoids repeating valid work and reduces the risk of giving an older claim as
current guidance. Author names in a bibliography describe cited works; treating
them as the document author creates false attribution. Explicit source identity,
scoped corrections and retained quotations address these different problems
without deleting historical evidence or assuming newer publications are correct.

## Source identity

`python scripts/source-provenance.py build` exports reviewed local catalogs into
ignored `knowledge/provenance.json`. It records source identity, original-file
SHA256 when available, publication/revision date precision, snapshot/retrieval
information, document authors and metadata evidence URL/basis. The sidecar is
bound to the approved index digest and included in frozen release fingerprints.
`check` detects catalog drift. Staging checks it before copying. Knowledge
preparation regenerates it after indexing. No LLM or network is used.

Research authors and dates come from reviewed `research/catalog.json` university
repository metadata, never reference-list extraction. Official-document dates
and version scope can be recorded explicitly in `knowledge/sources.json`;
unknown fields remain unknown. HUD references distinguish document authors from
passage text. A thesis discussing someone else's result is secondary evidence,
not proof the thesis author originated it. Repository ownership remains distinct
from file authorship and third-party contributions.

## Reviewed changes

`config/source-relationships.json` supports `supersedes`, `corrects`, `conflicts`.
Each link requires new/old IDs, applicability scope, supporting HTTPS URL and
review date. Unknown IDs, self/duplicate links, missing evidence and correction/
supersession cycles are rejected. Mutual conflict links are allowed. Example
shape only (not an installed factual relationship):

```json
{"new":"new-source-id","old":"old-source-id","kind":"corrects",
 "scope":"specific affected claim or version","evidence_url":"https://publisher.example/erratum",
 "reviewed_on":"2026-10-11"}
```

Present-day queries explicitly matching a reviewed scope demote corrected/
superseded candidates. Historical/date-specific queries retain ordinary relevance
ordering. Both sources and scoped links stay available; instructions require
version distinctions and conflict disclosure. Literal scope matching is conservative,
not complete claim reconciliation. The initial links are empty: newer documents
alone do not establish corrections. Regenerate metadata after relationship changes.

## Derived notes and bibliography review

Notes retain source ID, locator, exact quote, context and source+locator+text key.
Chronological sorting changes traversal only: 13,105 windows, 3,147 matching
completed keys and 9,958 remaining are unchanged. No model inference was run.
Future generation receives source metadata and author/secondary-citation rules.
Strong reference headings reject reference-section quotations; bibliography-only
windows do not generate facts. Citation-heavy passages are labelled for review,
not automatically discarded. PDF heading detection remains heuristic.

`python scripts/source-provenance.py audit` reads the build database without
changing it and writes ignored `data/provenance-audit.json`. It checks source
identity, current-window/quote linkage, normalized quote/context and bibliography
indicators. No old notes are deleted or blanket regenerated.

The 2026-10-11 audit checked 30,568 notes; SQLite quick_check passed. There are
1,114 citation/bibliography review candidates, not proven errors. No remaining
current-window/quote mismatch was detected. Two initial quote/context flags were
whitespace differences resolved using the grounding normalization. This is not
proof that all factual claims or author attribution are correct.

## Deployment

At the initial review these changes were checkout-only and the station was stopped after the Windows bugcheck. They were subsequently committed, pushed and included in active release `9d76eed753ad4ec9901c8b988e961248`. The nightly workload resumed and saved progress using the new chronology queue. See [STATUS.md](STATUS.md) and [UPDATES.md](UPDATES.md) for the dated deployment and recovery evidence. Restart success does not resolve the Windows crash or certify model attribution accuracy.

Validation: the final pre-push offline suite passed 196 tests (two skips). Seven targeted
provenance tests passed, including an added scoped-correction/history case.
Chat, context and teaching UI contracts passed. Headless retrieval against the
actual corpus attached authors/dates and returned chronologically ordered evidence.
These checks do not establish deployed model attribution accuracy or physical HUD acceptance.

Historical candidate: `43afda5d3e184b249420caca0f8d043e` was staged only and never prepared/activated. It was superseded by the later activated snapshot above; the active pointer is no longer the one recorded at initial review.

An independent pre-push code review approved the authored changes; 15 focused
checks passed with one Unix-socket skip on Windows. This does not certify live
provenance behavior or resolve the Windows crash.
