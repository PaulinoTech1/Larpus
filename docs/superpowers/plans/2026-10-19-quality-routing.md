# Quality Evaluations and Conservative Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for native execution, or superpowers:subagent-driven-development if the owner explicitly selects delegated execution. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evaluate multi-turn answer quality and add conservative, observable skill/evidence routing without weakening LARPUS's local boundaries.

**Architecture:** A pure router proposes bounded decisions; a separate policy applies them or retains existing behavior. An offline catalogue and evaluator distinguish mechanical checks from human claim-support review. Production defaults to shadow mode; active routing needs completed held-out and answer review evidence.

**Tech Stack:** Existing Python standard library, unittest, JSON, browser JavaScript and Node UI checks; existing local MCP, CPU retrieval, broker and release tools. No additional packages or models.

**Spec:** [Approved design](../specs/2026-10-19-quality-routing-design.md)

## Global Constraints

- Keep MCP as the existing transport. Keep skills locally authored, registered, hash-pinned and prompt-only.
- No new model, dependency, tool capability, external service, executable skill, corpus download or training is part of this change.
- All owned artifacts and temporary files stay on E:. CPU settings remain unchanged.
- Keep the station, GPU model, voice and nightly jobs in their existing operating state; this work does not authorize restarting the stopped station for live tests.
- Existing `None` remains persona only for compatibility with open HUD tabs and existing API callers.
- Existing explicit skill IDs always win and keep current validation.
- No automatic promotion while required human reviews or model-dependent measurements are absent.
- Do not increase a complexity allowance just to clear this feature's checks.
- Preserve unrelated working changes and frozen releases, including prepared Assembly candidate `341de68e12974563ab8da85c370542cc`. Commit/push only if requested.

## Review Focus

- Auto survives saved chats, exports and handoff imports without being mistaken for an installed skill (Task 5).
- A short acknowledgement following an unresolved factual question retains retrieval (Tasks 2 and 3).
- Teaching/context envelope contents are validated before routing; quoted instructions cannot grant routing authority (Tasks 2 and 3).
- A streaming answer retains route metadata in its final frame; partial/held answers never count as quality successes (Tasks 3 and 4).
- Missing, stale or incomplete human review never becomes a perfect support score or active-routing approval (Tasks 1 and 4).

## Shared contracts

`AUTO_SKILL = 'auto'` is a request sentinel, never an installed skill ID and never a broker prompt. `None` retains its current meaning. Reject a registry entry with this reserved ID.

`Decision` is a frozen dataclass with fields `route_id: str` (`grounded`, `conversational`, `unknown`), `skill_id: str | None`, `evidence: str` (`retrieve`, `skip`), `rule_id: str` (fixed policy ID), and `abstained: bool`. It contains no user text or instructions.

`RoutingOutcome` has `mode` (`off`, `shadow`, `active`), `proposed: Decision`, `effective: Decision`, and `duration_ms: float`. Its public serialization contains only those fields. `unknown` always means retrieve and no automatically selected skill; manual skills remain effective.

Policy JSON: `version: 1`, `mode: 'shadow'`, and `skill_rules`, a list of `{id, persona, skill_id, all_terms}`. IDs and skills must be registered/allowlisted; terms are literal bounded strings, never loaded regular expressions or code. Conversational recognizers are fixed code, not arbitrary policy expressions. Keep initial rules few and narrow; empty/no-match behavior is valid.

## Task 1: Quality fixtures and trustworthy report metrics

**Files:** Create `evals/quality.json`, `scripts/quality_cases.py`, `scripts/quality_metrics.py`, `tests/test_quality_cases.py`, `tests/test_quality_metrics.py`.

**Interfaces:**
- `load_cases(path: Path) -> tuple[dict, str]`: validated catalogue and SHA256.
- `mechanical_checks(case: dict, result: dict) -> dict`: release status, unknown citations and repeated-text warnings.
- `claim_support(claims: list[dict]) -> dict`: supported/reviewed counts, unsupported/uncertain counts, ratio or null.
- `validate_review(review: dict, report: dict) -> dict`: bind case IDs, fixture hash, run ID and response hashes; reject unknown/duplicate/stale entries.

- [ ] Write failing tests rejecting duplicated IDs, family leakage, private text fields, unsupported schema versions, nonalternating histories and invalid expected skills. Fixtures use `id`, `family`, `split`, `persona`, `messages`, `skill`, `allowed_routes`, `expected_skill`, `evidence_required`, `rubric`, and `relevance` (nullable labels keyed by approved fixture reference IDs).
- [ ] Write failing metric tests: empty/unreviewed claims produce null support ratio; two supported and one unsupported reviewed claims produce counts 2/3 and ratio 2/3; uncertain reviews remain explicit. A repeated quotation or mathematical equation produces a warning classification, not an automatic factual failure. Held/non-200 output is incomplete regardless of text.
- [ ] Run `python -m unittest tests.test_quality_cases tests.test_quality_metrics`; verify failures concern missing new interfaces.
- [ ] Implement small validators and pure metrics. Create 48 synthetic cases across the 12 design families, with 8 whole families in development and 4 in held-out; include evidence-required cases in both splits. Include multi-turn subscription-loop and correction cases without copying the owner's private transcript. Publish coverage rather than claiming comprehensive language recognition.
- [ ] Run the same command; require all tests pass. Review fixture content manually for accidental private data and label consistency. Retain human answer scores as null.

## Task 2: Pure routing and strict policy loading

**Files:** Create `runtime/routing.py`, `runtime/routing_policy.py`, `config/routing.json`, `tests/test_routing.py`, `tests/test_routing_policy.py`; modify `runtime/skills.py` to reserve Auto.

**Interfaces:**
- `load_policy(path: Path | None = None) -> dict`: schema/size/path checks and registered skill constraints.
- `decide(persona: dict, history: list[dict], skill: str | None, policy: dict) -> Decision`.
- `apply_mode(proposed: Decision, skill: str | None, mode: str) -> Decision`: shadow/off preserve existing retrieval and explicit skill, translating Auto to no effective skill.
- `public_outcome(outcome: RoutingOutcome) -> dict`: bounded JSON metadata.

- [ ] Write failing tests: manual allowlisted skill wins; disallowed skill rejected; Auto selects exactly one allowed rule match; two matches/no match abstain; `None` never activates a skill; rule text cannot become a prompt. Invalid/missing policy returns to legacy behavior through the integration adapter, not a fabricated match.
- [ ] Add tests for mixed reflection plus pricing, a factual follow-up followed by “thanks”, quoted bypass instructions, code/URLs, and teaching envelopes. All ambiguous inputs retrieve. Test malformed policy values, oversized files and symlinks. Test off/shadow preserve actual behavior.
- [ ] Run `python -m unittest tests.test_routing tests.test_routing_policy` and observe expected missing-module/interface failures.
- [ ] Implement literal matching over normalized validated question text. Use at most the last 6 messages for routing context; validate rather than truncate an oversized latest message. Validate/unpack teaching via `runtime.teaching.unpack`; validate conversation records through existing context APIs and exclude their wrapper text from match signals. If a conversation record may hide an unresolved factual task, abstain from skipping evidence.
- [ ] Recognize only a small full-message acknowledgement set and narrow owner-grounded reflection patterns. Any factual trigger, unknown term pattern or conflicting recent context overrides skip. Do not infer confidence from model scores. Separate skill matching from evidence decisions.
- [ ] Run tests and catalogue route evaluation on development cases only. Keep held-out families unavailable to rule tuning; run their final assertions in Task 6.

## Task 3: Request integration and pinned conversational templates

**Files:** Create `runtime/routing_adapter.py`, `tests/test_routing_integration.py`; modify `runtime/agents.py`, `runtime/inference.py`, `runtime/knowledge.py`, `scripts/broker-prompts.py`, `config/broker-prompts.json`, `runtime/security_scan.py` and existing relevant tests.

**Interfaces:**
- `prepare_route(persona: dict, history: list[dict], skill: str | None) -> RoutingOutcome`: validated request adapter; policy/router failures yield effective legacy behavior.
- Extend `knowledge.augment(prepared, persona, *, evidence_mode='retrieve')` without changing its two-value return. Only trusted internal code passes `skip`.
- Optional `result['routing'] = public_outcome(outcome)` and `timing_ms['routing']`; no request-supplied routing object is accepted.

- [ ] Write failing integration tests for old `None`/explicit callers, Auto in shadow mode, missing policy, invalid inputs, manual precedence, and retrieval exceptions. A retrieval exception on a grounded request still returns the existing diagnostic; it must never retry as conversational.
- [ ] Test compression bypass and unchanged summary prompt, notes lane and budget/DLP behavior. Test both protected-record and ordinary context pressure for no-retrieval mode. A conversational request must still pass context accounting, teaching unwrapping, input checks, GPU placement and full output screening.
- [ ] Run `python -m unittest tests.test_routing_integration` to establish the failing cases.
- [ ] Integrate after input/history validation and internal-lane identification, before final skill instructions are assembled. Gateway prevalidation accepts the Auto sentinel without loading a skill; only trusted inference applies a routing outcome. Keep dynamic user data out of system templates.
- [ ] Add one static conversational guidance constant forbidding added external facts, diagnoses, invented mechanisms and citations. In `augment`, share teaching/context handling across modes; skip only the `retrieve` call for an effective conversational route. Keep evidence empty and distinguish deliberate no-retrieval from failed/no-match retrieval in the system template.
- [ ] Extend prompt generation to enumerate the new static conversational combinations for approved personas and concrete skills; Auto is never a template component. Add exhaustive reachable-template tests and scan/fingerprint coverage for new runtime and policy files.
- [ ] Run `python scripts/broker-prompts.py`, then `python scripts/broker-prompts.py --check`, plus integration, context, knowledge, skill and broker tests. Reject unexpected notes-hash changes. No broker verification bypass.

## Task 4: Owner evaluator and review workflow

**Files:** Create `scripts/evaluate_quality.py`, `scripts/quality_report.py`, `tests/test_quality_runner.py`; modify performance helpers only if an existing reusable interface needs a backward-compatible extension.

**Interfaces:** `run_catalog(catalog: dict, policy: dict) -> dict`, `run_live(catalog: dict, mode: str, transport) -> dict`, `render_report(report: dict, reviews: dict | None) -> str`.

- [ ] Write failing tests proving default invocation performs no inference/WSL startup; invalid review hashes fail; interrupted runs retain partial rows; warmups are excluded; absent timing fields remain null; held streaming output cannot pass. Shadow reports distinguish proposed/effective routes.
- [ ] Run `python -m unittest tests.test_quality_runner`; observe expected failures.
- [ ] Implement default contract-only CLI: `python scripts/evaluate_quality.py --split development`. Use ignored UUID run directories under `data/evals/quality/`, validate E: resolution before writes, and record catalogue/policy/runtime hashes. `--review FILE --report RUN` renders verified review input without modifying raw run results.
- [ ] Implement explicit `--live` against an already running frozen station only; never start it. Live results are accepted only when the deployed release reports expected routing mode and matches declared policy/source pins. Do not label a legacy release's uninstrumented result as an active-routing trial.
- [ ] A paired comparison uses the same fixture/model/settings, interleaved case order and recorded warmups, plus independently prepared frozen off/active candidates when authorized. Mode changes require the owner release workflow, never edits to frozen config. While the station is stopped or candidates/review are absent, emit blocked/pending status; do not invent baseline/candidate measurements.
- [ ] Store responses and bounded source previews only in private ignored run reports. Review schema records factual claims with support status (`supported`, `unsupported`, `uncertain`), quoted supporting spans/reference IDs, latest-turn relevance and repetition judgement. Refuse spans/IDs absent from that case result. Human reviews are assessments, not independent proof.
- [ ] Report contract results, repetition warnings, reviewed answer scores, retrieval labels, first checked text and completion separately. `eligible_for_active` must remain false without complete pinned held-out results, required answer review and paired live evidence. This field informs owner review; it never edits policy or activates a release.
- [ ] Run all Task 1 and Task 4 tests and the development catalogue. Keep deployment-dependent results visibly pending.

## Task 5: Auto skill UI and old-client compatibility

**Files:** Modify `web/app.js`, `web/index.html`, `runtime/gateway.py`, related memory/handoff validation and `scripts/ui_checks.py`; create `tests/routing-ui.cjs`, `tests/test_routing_gateway.py`; extend existing memory/context/stream UI tests.

**Interfaces:** Existing chat request `skill` accepts `'auto'` in addition to concrete IDs/null. No new required request field. `/api/personas` adds optional `routing: {mode, auto_supported: true}`; old clients ignore it. Both HTTP and streaming success results preserve optional bounded `routing` metadata.

- [ ] Write failing UI/API tests for unchanged null/manual requests, Auto preserved through search/persona refresh, save/load, export/import, teaching scope and conversation compression; mixed clients omit new fields successfully. Test direct POST of an arbitrary routing decision is rejected.
- [ ] Add streaming final-frame assertions and fallback presentation. Show “Auto (preview)” when shadow mode computes proposals but applies none; show “Auto” only when active. No implication that preview selected an effective skill.
- [ ] Run `node tests/routing-ui.cjs` and `python -m unittest tests.test_routing_gateway` to verify expected failures.
- [ ] Add Auto to the current selector without changing its layout; keep Persona only as the existing default. Manual skill choice does not opt into automatic evidence routing: active automatic routing requires explicit Auto, while shadow proposals may be measured for other choices. Manual and `None` requests retain existing evidence behavior.
- [ ] Preserve an unavailable Auto selection in saved data and explain it on load instead of silently applying an arbitrary skill. Accept the reserved sentinel in handoffs only when supported; older clients may reject such a new handoff, but their existing conversations continue unchanged.
- [ ] Run new checks and all suites listed by `scripts/ui_checks.py`; check notices are honest about preview, active and fallback behavior.

## Task 6: Acceptance, documentation and deployment boundary

**Files:** Create `docs/QUALITY_ROUTING.md`; update `docs/ARCHITECTURE.md`, `docs/VERIFICATION.md`, and `docs/UPDATES.md` with actual results only. Add held-out contract assertions to `tests/test_quality_cases.py`.

- [ ] Before executing checks, set process `TEMP`/`TMP` to a new E: test directory. Use the existing isolated public-fixture local test runner so tests cannot mutate private source/index data.
- [ ] Run the development catalogue, then the untouched held-out route catalogue. Every declared allowed route/skill must match; every evidence-required fixture must retrieve. Record failures and coverage without changing held-out labels to fit the router.
- [ ] Run `python scripts/complexity.py check`, `python scripts/test-local.py`, `python scripts/evaluate-companion.py`, `python scripts/broker-prompts.py --check`, configured Node suites and `git diff --check`. Investigate new failures; record unrelated existing failures separately rather than resetting baselines.
- [ ] Review the final diff for prompt authority, untrusted-source execution, private diagnostics, fallback semantics and current API compatibility. Read verification-before-completion guidance before final claims.
- [ ] Document contract results and any remaining manual/live evidence as pending. Active routing stays disabled. Do not claim quality or latency gains from contract-only checks.
- [ ] Do not call `prepare`, `activate` or restart services while shutdown remains in force. When separately authorized and prerequisites exist, use a fresh `stage` → `prepare` → prepared-status check → `activate` flow and retain all scan warnings/rollback evidence. The separately prepared Assembly snapshot is immutable.
- [ ] Finish with exact implemented capabilities, tests run, blocked/pending live checks, owner operating state and no commit/push unless requested.

## Execution choice and self-review

Recommended method: native execution in this session. The six tasks share routing,
metadata and review schemas; keeping one implementer avoids divergent contracts.
No subagents are authorized by this plan alone. If independent review is requested,
use a bounded read-only reviewer and preserve the stopped-station constraint.

Self-review completed: evaluation claims are separated from heuristics; all five
review-focus items map to tests; shadow and active behavior are distinct; explicit
Auto is the only eventual active-routing opt-in; no frozen release or complexity
baseline is changed to obtain a pass. Live answer-quality and latency acceptance
remain pending rather than silently waived while the station is stopped.
