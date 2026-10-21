# LARPUS improvement plan and review

Prepared 2026-10-20 from the current owner checkout and recovery worktree.
This is an execution proposal, not approval to deploy or operate a supervisor.

Handoff refresh: subsequent work in the recovery worktree has addressed the
reserved-replacement shutdown race, strengthened drill receipts and added
synthetic SQLite export/restore. Its execution ledger reports 531 full-suite
tests with four skips; the latest focused recovery/backup check passed 49 tests.
Final independent review of `_stored_deaths` remains open. The findings below
record the earlier review baseline; recheck them against the newer recovery
ledger before implementing. No recovery worktree implementation is included in
this documentation commit.

## Review basis and current state

Read-only review included `AGENTS.md`, `README.md`, `docs/UPDATES.md`,
`docs/STATUS.md`, `docs/ARCHITECTURE.md`, the architecture module/contract/
scorecard records, `docs/PROJECT_REVIEW_2026_10_17.md`, the October 20 execution
profile report, existing quality-routing and recovery plans, implementation
entry points, Git/worktree state and recovery test receipts. This is a targeted
engineering review, not an exhaustive audit or fresh answer-quality evaluation.

`python scripts/releases.py status` reported:

- Active: `042f91c0a1454887a694c945f49237ad`, running.
- Previous: `7df2e957751642d6ace4630fa047fe94`; no pending cutover.
- Main checkout: `a2f12c0`, branch `feat/secure-execution-profiles`.
- Recovery: separate sibling worktree `E:\speedzone_MS\LARPUS-worktrees\recovery-supervisor`,
  branch `feat/recovery-supervisor`, same committed base, substantial uncommitted work.
- Additional worktrees exist for latency/quality and MCP Skills. Inspect before
  reusing their work. Do not infer integration from their branch names.
- Main checkout already has an edited failure-isolation outline and untracked
  recovery plan/spec, `New Text Document.txt` and `larpus-sensors.csv`. Preserve them.

The production update record explicitly leaves execution profiles and MCP Skills
unpromoted. `docs/STATUS.md` still presents an October 11 deployment snapshot.
Historical sections of other documents describe earlier selections. These are
provenance/visibility issues to reconcile, not permission to change production.

## Findings that determine the order

1. **Recovery is promising but unfinished.** Pure policy, bounded durable state,
   owner controls, Windows adapter and generation-bound health metadata exist
   only in the recovery worktree. Its isolated runner logged 514 tests with four
   skips; the repeated harness logged 30 passing rows. These logs predate later
   review fixes and are not final validation of the current diff.
2. **The independent recovery review found real safety gaps.** RuntimeError
   handling, cleanup after an unrecorded launch, persistence of locked holds and
   validation during reserved-launch reconciliation received local fixes and
   focused regressions. Reverify those changes. A combined shutdown can still
   miss a recorded replacement when publication failed and the selected pointer
   names the old dead gateway. Resolve this before calling recovery complete.
   The reviewer exhausted its usage limit before delivering a final verdict.
3. **Drill receipts overstate observability if read without their limits.** The
   gateway uses real disposable processes with simulated dependency/pin/health
   gates. Five other cases mostly reuse injected unit contracts. Gateway
   transition labels are hardcoded rather than captured; cancellation does not
   yet combine the scheduler fault with supervisor zero-launch accounting;
   BM25 evidence does not yet demonstrate a complete approved-evidence request.
   Null counters remain uninstrumented. Thirty passing rows do not establish all
   the approved drill acceptance targets.
4. **Application rollback is not data recovery.** The inspected owner scripts do
   not expose a dedicated general backup/restore workflow. This does not prove
   the owner lacks external backups. Models, original documents, notes, browser
   chats, TLS identity and quarantine have different recovery/security needs.
5. **Quality is a demonstrated constraint.** The October 20 profile comparison
   retained five failed attempts and twelve critical answer flags across profiles.
   Faster answers have not established quality parity. Multi-turn correctness,
   source entailment, uncertainty and appropriate refusal need stronger evaluation.
6. **Five-second latency remains unmet.** Reported Ultra Fast mean/p95 were
   5.718/7.980 seconds versus Verified 6.703/9.045. Stage clocks overlap; their
   medians must not be added. No runtime second-model critic was found to remove.
7. **Modularity work should follow demonstrated pain.** Broad handlers, global
   initialization and remaining import cycles are documented. Existing contracts,
   fixed transports and the complexity gate provide a useful base. A rewrite or
   new orchestration framework would create avoidable regression risk.

## Program goals and boundaries

The aim is a station that recovers predictably, preserves committed work,
answers with better demonstrated support and exposes accurate operational state.
Retain local inference, local CPU voice, home-LAN scope, existing HUD behavior,
approved source provenance, broker cancellation fences, authentication,
integrity checks and DLP. No cloud fallback, broader model tools, arbitrary
provider transport, automatic model substitution or silent quality downgrade.

Each work package must name inputs, outputs, failure owner, state owner, timeout,
cancellation behavior and evidence required for acceptance. Use existing standard
library and test infrastructure where sufficient. Do not raise complexity
allowances, relax scanners or replace failed measurements with a better run.

## Phase 0 — Establish a reproducible baseline

1. Record branch, SHA, dirty-file inventory, worktrees, selected/previous release,
   pending cutover and verified gateway identity. Record model/voice identities
   only through bounded read-only owner probes; never boot stopped WSL to inspect.
2. Build a feature-state table: production, prepared, checkout, isolated worktree,
   proposed. Include execution profiles, MCP Skills, quality routing and recovery.
3. Inventory existing tests, UI manifest, complexity policies, static scan scope
   and ignored public assets required by fresh test workspaces. Do not copy
   credentials, private corpus or model data into tests.
4. Run the configured isolated baseline and UI manifest in the chosen workspace;
   retain exact commands, versions, counts, skips, failures and asset prerequisites.
5. Separate pre-existing failures from new regressions. Select a single bounded
   worktree for each implementation package, preserving uncommitted work.

Deliver: baseline manifest, feature-state table, dependency-ordered task ledger
and explicit authority boundaries. Exit gate: no production mutation and a
repeatable baseline, or a clearly isolated blocking defect with a repair plan.

## Phase 1 — Finish and independently review recovery

Resume the existing recovery spec/plan; do not rebuild it from scratch.

1. Add a failing shutdown regression: reserve launch; record new identity; allow
   readiness; fail pointer publication; issue `disable --stop-gateway`. Assert
   disable is durable first, exact recorded replacement is drained and no
   unrelated process is signalled. Cover reused PID, absent process, missing
   recorded identity, drain timeout and active-selection changes. Ambiguous
   ownership must produce an explicit held outcome, never false shutdown success.
2. Revalidate review fixes: RuntimeError sanitization, post-launch persistence
   failure cleanup, durable broker-fault holds and reserved-launch pin/isolation
   revalidation. Test both pre-validation and post-validation races.
3. Check restart authority across ordinary process restart, monotonic reset,
   wall-clock changes, cooldown, two-attempt window, disabled intent, pending
   cutover, maintenance and corrupted/ACL-modified state. Acknowledgement cannot
   clear broker fences, reservations or budgets.
4. Audit journal writes for prior-commit preservation under ENOSPC, permission
   failure, interrupted replacement and diagnostic sink failure. Document the
   actual filesystem durability limits rather than claiming power-loss proof.
5. Ensure every production observation is bounded and read-only. Verify stopped
   WSL cannot be booted as a side effect; no general startup, model warm-up,
   broker reset, voice restart, pruning or arbitrary commands are reachable.
6. Review health producer identity/freshness, repeated confirmation and stale
   health behavior without changing existing required health/API contracts.
7. Request fresh independent review after fixes. If reviewer capacity is absent,
   retain the open review gate; do not mark independent review passed.

Deliver: tested recovery candidate, updated review disposition and owner runbook.
Exit gate: no unresolved critical/important safety findings; full current-diff
validation; supervisor remains uninstalled, stopped and disabled in production.

## Phase 2 — Make failure drills demonstrate their claims

Use disposable stores, unique receipts, ephemeral loopback ports and exact owned
process handles/creation identities. Never inject faults into the serving station.

| Scenario | Required instrumented evidence |
| --- | --- |
| Gateway exits | Independent supervisor identity survives; actual observation/decision journal; same release restored; exact launch count; readiness and cleanup times |
| Retrieval worker unavailable | Approved fixture index remains queryable through the normal retrieval/request boundary; BM25 evidence IDs and order retained; supervisor does not restart healthy gateway/model/voice |
| Cancellation unconfirmed | Real scheduler fixture refuses both lanes; supervisor consumes that fault and durably holds; zero launches and no fence reset |
| Stream truncates | Actual transport/HUD fixture keeps partial output out of completed saved history; generation-request counter proves no automatic replay |
| Disk-full write | Explicit storage failure; previous committed fixture bytes/hash and logical record IDs survive; no unauthorized launch; temporary-file cleanup recorded |
| Candidate readiness fails | Existing updater with disposable store/adapters restores previous selection and expected owned process; candidate cleanup and pending-marker disposition recorded |

Record before/after identities, observed transitions, attempts, generations,
committed record IDs/counts/hashes, refusals, elapsed times and cleanup status.
Distinguish not applicable, not instrumented, failed, held and not run. A passed
unit contract is supporting evidence, not a measured end-to-end drill.

Run every completed drill at least five times with the default policy interval.
Retain all failures, including early runs; never retry until green and omit them.
Report count/median/p95/max where meaningful and document quantile convention.
Targets: zero lost committed records in tested stores, zero duplicate automatic
generations, zero unnecessary negative-case restarts, bounded attempts and exact
cleanup. These remain scoped targets, not whole-system guarantees.

## Phase 3 — Design and demonstrate data restoration

1. Classify data by irrecoverability and authority: original sources, approved
   manifests/indexes, generated notes and progress journals, release selections,
   model artifacts, browser exports, auth/TLS material and private quarantine.
2. Document each store's writer, commit boundary, consistency requirements,
   regeneration source, size, retention need and restore validation.
3. Ask only for missing owner choices that matter: backup destination, encryption
   key custody, acceptable recovery-point/recovery-time targets and retention.
   Continue inventory and synthetic tooling while those decisions are pending.
4. Implement reviewed export/backup primitives using consistent SQLite backup
   where applicable, immutable manifests and checksums. Keep secrets out of
   ordinary artifacts; quarantine keeps its restricted policy. Never copy live
   SQLite files and call the result transactionally consistent without evidence.
5. Restore synthetic stores to a separate location. Validate schema, provenance,
   logical records and startup/read-only behavior. Include corrupt/truncated
   backups, missing keys, interrupted copies and insufficient space.
6. Propose an owner-data backup/restore rehearsal separately. No original data
   replacement, key rotation, production restore or deletion is authorized here.

Deliver: store matrix, recovery objectives for owner approval, dry-run tooling,
synthetic restoration receipts and recovery runbook. Exit gate: independent
restoration from the backup artifact, not merely a successful backup command.

## Phase 4 — Improve answer quality before promoting speed

1. Inspect and reuse the existing quality-routing worktree/spec/fixtures. Preserve
   manual skill selection and keep automatic routing off/shadow until accepted.
2. Build development and whole-family held-out cases spanning multi-turn factual
   follow-ups, corrections, conflicting sources, unsupported premises, mathematics,
   IT/security judgment, source age and ordinary conversation. Synthetic fixtures
   must not reproduce private conversations.
3. Convert the critical profile-report flags into regression families: unsupported
   vulnerability dismissal, premature alert closure, incorrect metrics, conflicting
   time budgets, stability/norm claims and unsupported hardware observability.
4. Bind judgments to exact case/fixture/response/source hashes. Separate mechanical
   completion/citation checks, agent rubric scores and human claim-support review.
   Missing review is null. A citation's presence does not demonstrate entailment.
5. Measure source relevance/coverage, claim support, appropriate uncertainty,
   task success, multi-turn consistency and refusal quality. Keep failure/held
   answers in the denominator; track critical errors separately from means.
6. Compare original-source retrieval, optional CPU retrieval and derived notes
   against the same workload. Preserve access to originals and source nuance.
7. Pre-register promotion criteria before a live comparison. Live GPU runs need
   an owner-approved window; offline fixture/evaluator development can proceed.

Deliver: reproducible evaluation suite, failure taxonomy, source-bound review
package and narrowly justified changes. Exit gate: held-out evidence and required
human review, with no unreviewed automatic-routing promotion.

## Phase 5 — Pursue latency with attribution and quality gates

1. Implement or verify nonoverlapping stage timing with explicit clock origins:
   queue/admission, integrity/isolation, MCP startup, retrieval, first model frame,
   first approved text, completion and speech. Record numeric metadata only.
2. Define controlled workloads: short conversation, evidence-heavy question,
   multi-turn follow-up, long context, idle/cold service, notes contention and
   delayed/disconnected client. Preserve failed attempts and warm-up rules.
3. Start with the largest demonstrated costs. Evaluate bounded MCP lifecycle
   reuse or retrieval work only after measuring their actual contribution.
   Persistent clients require fresh per-request policy checks, correlation IDs,
   cancellation isolation, leak bounds and stale-state rejection.
4. Change one hypothesis at a time. No skipped security checks, approved-verdict
   caching, smaller evidence coverage, weaker DLP or CPU model fallback for speed.
5. Compare paired/interleaved workloads and report mean/median/p95, failures,
   output pacing, memory/CPU and quality outcomes. Treat five seconds as a target
   that may fail, not a reason to alter the denominator or acceptance threshold.

Deliver: stage evidence, smallest useful optimization and an accepted/rejected
experiment record. Exit gate: pre-registered latency/pacing/quality/security
criteria all pass; otherwise retain the experiment without promotion.

## Phase 6 — Improve maintainability and operational clarity

1. Generate a bounded owner status view distinguishing active release, prepared
   candidates, checkout changes, functional readiness, broker admission, notes,
   recovery state and scan age/completeness/reviewed warnings.
2. Preserve the existing HUD. Add only decision-useful status and recovery cues;
   keep reauthentication and partial-stream conversation preservation tested.
3. Update STATUS/README from verified dated evidence, retaining historical records.
   Avoid another independent status store that can drift from selected release.
4. Split only measured hotspots: gateway route dispatch, retrieval ranking/budget
   stages and import-time/global configuration. Preserve result shapes and error
   codes with characterization and mutation tests before changing boundaries.
5. Review the canonical test/scan inventory for new owner modules. Add genuinely
   missing UI/PowerShell contracts; do not create tests that merely restate helpers.
6. Keep public-only CI free of private corpus, credentials and owner reports.

Deliver: accurate operator view, small reviewed refactors, updated contracts and
reproducible checks. Exit gate: same API/HUD semantics and policy decisions, no
complexity-allowance growth to hide new debt.

## Phase 7 — Review package and separately authorized rollout

Run the current configured Python suite, every suite in `scripts/ui_checks.py`,
prompt pin check, complexity gate, diff whitespace check and relevant source/
scanner inventory checks. Record every skip and platform limitation. Never alter
frozen scan receipts or auto-accept a changed warning inventory.

Prepare a source/hash-bound 30-minute observation-only proposal measuring probe
overhead, request latency and false suspicions. Do not start it without owner
authorization. Present installation/arming separately after evidence review.

Any later release must be a scoped snapshot retaining the active release's
corpus/config/prompts and excluding unrelated unaccepted features. Use stage,
prepare, prepared-status verification and authorized activate. Preserve automatic
candidate-rejection rollback, explicit owner rollback and the durable shutdown
contract. Report brief rebinding honestly; LAN sessions need fresh login.

No commit, push, deployment, arming, schedule installation, production fault,
model/dependency replacement or owner-data restore is authorized by this plan.

## Completion package

- Current-state and feature-state manifests, scoped source diff and task ledger.
- Review findings with fixed/deferred/blocked disposition and fresh evidence.
- Repeated drill and restore receipts with all failures and coverage limits.
- Quality and performance comparisons bound to exact source/workload hashes.
- Owner commands, held-state handling, rollback and uninstall procedures.
- Required owner decisions and next concrete approval, without presenting
  unperformed observation, usability, security or durability work as complete.

Execute Phases 0–2 first. Build Phase 3 inventory while awaiting review capacity.
Quality work precedes performance promotion. Documentation and small maintenance
fixes can proceed alongside those phases only when they do not collide with the
same files or obscure validation. No calendar promise is made before baseline.
