# Quality evaluations and conservative routing

Date: 2026-10-19
Status: owner approved on 2026-10-19; implementation plan review pending

## Purpose and agreed scope

The owner accepted the recommendation to begin with quality evaluations and
conservative skill/evidence routing. Improve whether LARPUS answers the latest
turn, uses relevant evidence, admits gaps, and avoids repetitive advice. Measure
quality and first checked text latency before claiming an improvement.

Keep MCP as the existing transport. Keep skills locally authored, registered,
hash-pinned and prompt-only. No new model, dependency, tool capability, external
service, executable skill, corpus download or training is part of this change.
All owned artifacts and temporary files stay on E:. CPU settings remain unchanged.
Keep the station, GPU model, voice and nightly jobs in their existing operating
state; this work does not authorize restarting the stopped station for live tests.

## Current behavior verified in the checkout

- `runtime/agents.py:messages_for` adds an explicitly selected approved skill.
  `None` currently means persona only.
- `runtime/inference.py:chat` validates input, handles compression, calls evidence
  augmentation, then uses the pinned broker and output screening.
- `runtime/knowledge.py` already combines lexical and semantic retrieval and a
  CPU cross-encoder. Changing that ranking algorithm is outside this increment.
- `citation_check` checks selected/unknown identifiers, not claim support.
- Companion evaluation has manual rubrics; performance evaluation has timing and
  review points. Neither alone establishes multi-turn evidence quality.
- Broker system templates are generated and hash-pinned. Routing must not weaken
  that check or let user text create a system prompt.
- Assembly optimized is separately prepared; this change must preserve that work
  and must not silently activate or replace its candidate.

## Alternatives and choice

1. **Rule-based routing plus abstention (recommended first):** deterministic,
   inspectable, no additional model load, and inexpensive to test. Narrow coverage
   is acceptable; ambiguous inputs keep current retrieval behavior.
2. **Embedding-based skill selection:** reuse the CPU embedder and match skill
   descriptions. Potentially broader matching, but requires calibrated thresholds,
   first/second candidate margins and additional worker traffic. Defer until the
   labelled set demonstrates a specific limitation of rules.
3. **An LLM router:** flexible, but adds a generation, consumes the shared slot and
   can erase latency savings. Excluded from the first implementation.

## Evaluation component

Add a versioned public/synthetic quality case catalogue and an owner-run evaluator.
Keep existing companion/performance contracts and their separate claims.

Cases cover conversational acknowledgement, personal reflection, factual lookup,
current/archived facts, mathematical correction, follow-up corrections, repeated
advice, missing evidence, source contradictions, citation support, skill selection,
and quoted instructions attempting to influence routing. Include conversations
modelled on the subscription loop, with personal details replaced by fixtures.

Each case declares its persona, history, explicit skill or Auto request, permitted
routes, expected skill or abstention, source relevance labels where applicable,
and a plain-language answer rubric. Partition by scenario family into development
and held-out sets; near-duplicate conversations must not cross the split. Record
the split, fixture version and hashes. Do not tune on held-out results.

Separate three report layers:

- Contract checks: valid route, manual override, allowed skill, output screening,
  unknown citations, deterministic failure handling and protocol compatibility.
- Heuristics: copied sentence/paragraph rates across turns, with quotations and
  necessary mathematical repetition reported separately. Similarity is a warning,
  not proof of an unhelpful answer.
- Human review: relevance to the latest turn, unsupported external factual claims,
  source support for each reviewed claim, and handling of corrections. Store
  unreviewed scores as null. Never label a keyword match or an LLM judge as verified
  factual correctness.

Report support as supported / reviewed factual claims, with unsupported and
uncertain counts; do not give a claim-free answer a perfect support percentage.
Report retrieval relevance only where labels exist. Preserve responses and bounded
source passages only in ignored owner-local reports. Repository fixtures contain
no private archive text, credentials or real chat exports.

For live paired runs, record release/model identities, inference settings, fixture
hashes, cold/warm status, route timing, retrieval timing, prompt token count, first
model frame, first checked text and completion. Distinguish absent measurements
from zero. Model-dependent results remain pending while the station is stopped.

## Routing component

Add one small pure routing module and a versioned local policy. The input is the
validated persona, normalized latest user turn, bounded recent conversation and
explicit skill choice. Unwrap validated teaching/context envelopes before routing;
do not treat wrapper syntax as user intent. Compression, notes and other internal
lanes bypass routing and keep their existing templates and scheduler behavior.

The result contains a fixed route ID, an allowed skill ID or null, an evidence
decision, a rule ID and an abstention flag. No prompt fragments, file paths, tool
names, model selection or permissions may be emitted by the router. Rule IDs and
categorical match strength are diagnostic labels, not calibrated probabilities.

Skill behavior:

- Existing explicit skill IDs always win and keep current validation.
- Existing `None` remains persona only for compatibility with open HUD tabs and
  existing API callers.
- A new explicit Auto choice requests automatic selection. It can activate at
  most one skill already allowed by the persona. Multiple plausible matches,
  conflicting turns, unavailable routing or no match mean no automatic skill.
- Full instructions are loaded only after selecting an approved skill, using the
  existing loader. Downloaded README/AGENTS/SKILL content is never a skill source.

Evidence behavior:

- Default is current retrieval. Questions about external facts, calculations,
  versions, sources, archive contents, prices, security, health or legal matters
  keep retrieval. Quoted requests to skip evidence cannot override these rules.
- Only narrowly recognized conversational acknowledgements and owner-grounded
  reflection may use a no-retrieval conversational route. A factual subquestion,
  uncertainty about intent, or unresolved factual follow-up keeps retrieval.
- A conversational response must address the owner's stated experience without
  adding product facts, diagnoses, invented psychological mechanisms or citations.
  That semantic requirement needs answer evaluation; a router cannot guarantee it.
- Missing evidence for a grounded request remains a knowledge gap. Routing must
  not convert an evidence error into an unsupported successful factual answer.
- Existing source screening, context limits, DLP and GPU/broker boundaries stay
  authoritative. Router exceptions revert to the existing validated request path.

First introduce shadow mode: compute and record the proposed route while using
the existing actual behavior. Active routing is separately opt-in and disabled by
default until the held-out route cases pass and answer review is complete. Record
both proposed and effective route so shadow mode cannot look like activation.

## Integration and compatibility

Add Auto to the existing skill selector without altering the page layout or
discarding drafts/history. Keep all existing API fields valid. Routing metadata is
an optional bounded response field; old tabs can ignore it. Do not place raw user
text or evidence in routine diagnostics.

Keep all new conversational system guidance static and regenerate the broker's
approved prompt manifest through its owner build command. Test every reachable
persona/skill/evidence combination against that manifest. Never disable template
validation or edit a frozen receipt to get a new route accepted.

Manual selection is the recovery control for skill routing. A single policy switch
disables active routing and restores current behavior; rollback is also available
through the ordinary release manager. No runtime self-modifying policy or training.

## Acceptance and rollout

1. Focused tests prove manual precedence, skill allowlists, wrapper handling,
   uncertain-match abstention, evidence-required mixed requests, failure fallback,
   unchanged internal lanes and compatibility with old requests/tabs.
2. Every held-out route fixture passes its declared allowed route and skill; every
   evidence-required fixture retains retrieval. Publish counts and coverage limits.
3. Mechanical and human quality results remain separate. No automatic promotion
   while required human reviews or model-dependent measurements are absent.
4. Live paired tests must show no new unsupported factual claim or copied-advice
   regression on reviewed cases. Report per-route latency, not an aggregate that
   hides regressions. Do not promise a numerical speedup before measurement.
5. Run the existing required local/UI/broker/isolation/security checks before a
   release is prepared. Retain scan findings and failures. Do not increase a
   complexity allowance just to clear this feature's checks.
6. Prepare a fresh frozen candidate through the documented release workflow only
   when its prerequisites are met. Do not modify the currently active or already
   prepared snapshots. Activation and live tests must respect the owner's station
   shutdown request and are not performed during design work.

## Deferred work

Learned routing, embedding replacement, reranker quantization, LoRA/DPO training,
knowledge tracing, autonomous browsing, executable skills and automatic ingestion
remain separate experiments. No part of this increment trains on model-generated
answers or claims to learn the owner's mastery from conversational confidence.
