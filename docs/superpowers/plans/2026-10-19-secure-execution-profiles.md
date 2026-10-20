# Secure Execution Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Native execution is recommended, pending owner plan review.

**Goal:** Introduce independently testable execution profiles while retaining mandatory security, quality and output consistency.

**Architecture:** One shared inference/security path consumes a frozen request context. Pure integrity hashing and numeric tracing are independent modules; profile orchestration composes existing validators rather than creating another security stack. Benchmarks determine promotion, not profile names.

**Tech Stack:** Existing Python, MCP SDK, browser JavaScript and unittest; no new dependencies.

**Spec:** [Approved design](../specs/2026-10-19-secure-execution-profiles-design.md), approved 2026-10-19 with explicit emphasis on modularity.

## Execution closeout - 2026-10-20

The owner approved native execution and the live window. The original detailed
checkbox list below is retained as the planning specification; this closeout
and data/execution-profiles/progress.md record execution evidence.

| Tasks | Status |
| --- | --- |
| 1-2 integrity and context | Implemented; independent import/hash/strict value tests passed |
| 3-4 shared transport, diagnostics and controls | Implemented with additive compatibility and bounded clocks; 11 UI suites passed |
| 5 selected security/removal/recovery faults | Implemented; final isolated suite 457 tests/four skips, exit0 |
| 6 matched benchmark | Completed 100 attempts/profile in two invocations; five failures retained, 295 answers scored blind |
| 7 measured optimization | Fresh batching implemented and benchmarked; pacing passed, latency target failed, quality parity unresolved; no promotion |
| 8 evidence/handoff | Final report, 12-dimension before/after scorecard, retained warnings, links and stopped-state verification recorded |

Live logging-on/off causal control, broad cold/history/concurrent scenarios and
rendered LAN/browser acceptance remain unestablished; they are not inferred from
unit tests or fixed sequential HTTP results. Activation, commit and push were not
performed. See [final acceptance](../../EXECUTION_PROFILES_PERFORMANCE_2026_10_20.md).

## Global Constraints

- Preserve local-only operation, existing mandatory checks, answer quality and output pacing.
- The production objective is mean and p95 first-visible response below five seconds.
- Accepted profiles are `verified`, `ultra-fast` and `diagnostic`; interaction labels are `conversation`, `analysis` and `coding`.
- Diagnostic base is `verified` or `ultra-fast`, defaulting to verified; other profiles reject base.
- No profile selects host/direct transport or grants capabilities; owner raw benchmark remains separate.
- Keep logs/builds on E:, stock power and the existing 20-processor ceiling.
- No deployment, activation, commit or push is implicit in executing this plan. Preserve unrelated owner files and frozen releases. Follow `docs/UPDATES.md` for any later authorized release work.
- Keep running services available; do not start stopped services for unit tests. Obtain a scoped service window before live benchmarks requiring startup.

## Review Focus

- Old HUD requests omit execution: identical Verified behavior and compatible stream schema (Tasks 2-4).
- Malformed or forged metadata attempts bypass/host selection: reject before model work (Tasks 2-3).
- Cancellation/timeout followed by another request: no leaked context, chunks or diagnostic state (Tasks 3, 5).
- Optional component removal versus tampering: reviewed removal works, corrupt approval still fails closed (Task 5).
- Diagnostic storage/telemetry failure: cannot release rejected content or disrupt unrelated requests (Tasks 4-5).

## File ownership and module contracts

| Unit | Files | Contract and exclusions |
| --- | --- | --- |
| Fresh hashing | new `runtime/source_integrity.py`; existing `runtime/security_scan.py`, `runtime/isolation.py` | `fingerprint(root: Path) -> str`; stdlib only, no MCP, model, scanner initialization or cached approval |
| Execution values | new `runtime/execution_profiles.py` | frozen `ExecutionContext(profile: str, interaction: str, base: str)`; `resolve(value: object = None) -> ExecutionContext`, `to_wire(context) -> dict`; reject invalid input with ValueError; no process/env/transport dependencies |
| Transport integration | `runtime/gateway.py`, `runtime/mcp_client.py`, `runtime/mcp_server.py`, `runtime/inference.py` | Optional trailing `execution=None` on internal chat/call functions; validated context carried in `larpus_execution`, existing MCP arguments unchanged |
| Numeric observations | new `runtime/execution_trace.py` | request-local `Trace(enabled: bool, clock: Callable[[], float])`; `mark(name: str) -> None`, `snapshot() -> dict`; fixed event names, relative ms only, no arbitrary text payload |
| Fast observations | new `runtime/execution_preflight.py`; existing `runtime/isolation.py` | `observe() -> dict` fresh per call, consumed by existing validators; no allow verdict, policy decision, long-lived cache or alternate validator |
| HUD | `web/index.html`, `web/app.js` | profile/interaction controls; additive execution object; no raw mode |
| Measurement | new `scripts/benchmark_execution_profiles.py`, `evals/execution-profiles.json` | fixed secure workload, balanced schedule, raw numeric rows and summary; never imports owner raw Backend |

Small modules earn their place through independent tests and dependency direction.
Do not introduce a generic plugin registry, abstract provider framework or mutable
global execution context. Do not split large handlers beyond these scoped seams.

### Task 1: Extract fresh integrity hashing

**Files:** create `runtime/source_integrity.py`, `tests/test_source_integrity.py`; modify `runtime/security_scan.py`, `runtime/isolation.py` and scanner source-copy inventory.
**Consumes:** existing fingerprint scope and isolation preflight contract.
**Produces:** `fingerprint(root: Path) -> str`, compatibility `security_scan.fingerprint()`.

- [ ] Write `test_matches_legacy_scope`, comparing old and new implementations against the same temporary tree, including missing optional artifacts, ordering, native/skill/deployment files, oversize rejection and symlink behavior. Add `test_fresh_reads_detect_edit` and subprocess `test_import_does_not_load_mcp_or_spawn`.
- [ ] Run `python -m unittest discover -s tests -p test_source_integrity.py -v`; confirm missing module failure first.
- [ ] Move exact hash algorithm, parameterize ROOT only, retain wrapper using scanner ROOT; isolation imports pure module. Include new runtime modules in scanner copied source inventory as each is introduced, without changing approved warnings or pins.
- [ ] Repeat focused tests plus `test_isolation.py` and `test_isolation_snapshot.py`; require passes or explicit documented platform skips. Verify import SCC is removed, without claiming latency savings.
- [ ] Review only this task's diff; record logical changeset, no automatic commit.

### Task 2: Establish strict profile value contract

**Files:** create `runtime/execution_profiles.py`, `tests/test_execution_profiles.py`.
**Consumes:** no runtime services. **Produces:** resolver and canonical wire context defined above; resolved base equals own profile except Diagnostic's selected base.

- [ ] Write `test_defaults_verified_conversation`, `test_all_profile_interaction_combinations`, `test_diagnostic_base`, `test_rejects_base_on_non_diagnostic`, `test_rejects_unknown_fields_and_non_strings` and `test_context_frozen`. Assert None defaults; booleans/lists/unknown keys/raw/host/security overrides fail; no environment lookup or capabilities field.
- [ ] Run `python -m unittest discover -s tests -p test_execution_profiles.py -v`; verify missing module failure.
- [ ] Implement strict resolver with size/key bounds and canonical `to_wire`; serialize base only for Diagnostic. Imports must be dependency-light standard library.
- [ ] Repeat tests; prove canonical wire round trip and no shared mutable state across contexts.
- [ ] Review task diff and update module contracts; no automatic commit.

### Task 3: Integrate one shared execution path

**Files:** modify `runtime/gateway.py`, `runtime/mcp_client.py`, `runtime/mcp_server.py`, `runtime/inference.py`; create `tests/test_execution_transport.py`; extend `tests/test_mcp.py`, `tests/test_streaming.py`.
**Consumes:** Task 2 resolver. **Produces:** optional trailing execution parameter on internal call/chat APIs, resolved independently at each trust boundary; unchanged public three-tool argument schema.

- [ ] Add failing tests `test_old_request_defaults`, `test_metadata_roundtrip_stream_and_nonstream`, `test_forged_metadata_rejected_before_inference`, `test_unknown_execution_rejected_before_child`, `test_profile_never_selects_host`, `test_cancel_then_next_context_isolated` and `test_exact_stream_join_still_required`. Patch backend to assert zero calls after rejection.
- [ ] Run `python -m unittest discover -s tests -p test_execution_transport.py -v`; confirm intended integration failures.
- [ ] Extend strict gateway body fields with execution; pass canonical metadata for chat only. Resolve in server even without streaming; reject malformed execution before inference. Add optional context to inference without branching around security. Preserve broker options, scheduler fence, descriptors, auth, DLP, provenance, evidence and final gates.
- [ ] Repeat focused transport/MCP/stream tests; test sealed deployment mocks reject direct-route invocation for all profiles. Retain explicit owner fixture mode outside production-profile claims.
- [ ] Review dependency direction: orchestration imports value module; value module imports no orchestration. No second broker/session cache. Record logical changeset.

### Task 4: Add bounded diagnostics and compatible controls

**Files:** create `runtime/execution_trace.py`, `tests/test_execution_trace.py`; modify gateway/MCP/inference timing hooks, `web/index.html`, `web/app.js`; create `tests/execution-profile-ui.cjs`.
**Consumes:** ExecutionContext and existing timing boundaries. **Produces:** bounded numeric diagnostics for Diagnostic; default profiles do not allocate detailed traces.

- [ ] Add fake-clock tests `test_relative_monotonic_marks`, `test_fixed_event_names_only`, `test_bounded_trace`, `test_disabled_no_clock_work`, `test_no_payload_or_private_path`, `test_trace_failure_cannot_change_release_verdict`. Test UI default omission, independent interaction, secure label, history preservation and unknown diagnostic field tolerance.
- [ ] Run focused unittest and `node tests/execution-profile-ui.cjs`; confirm intended failures.
- [ ] Implement maximum 32 fixed event entries, bounded numeric values and request-local ownership. Keep host/child durations separately labeled. Reuse existing approved timing fields; do not claim host first release equals browser paint. Hook browser performance timer at first nonempty rendered text; never export user content in diagnostics.
- [ ] Run focused tests and `node tests/chat-stream-ui.cjs`; verify replay/history behavior through existing UI checks. Rendered browser acceptance remains a separate live check.
- [ ] Review trace overhead explicitly and record logical changeset.

### Task 5: Prove profile security and optional-component independence

**Files:** create `tests/test_execution_security.py`, `tests/test_execution_modularity.py`; extend affected existing fixtures; update architecture contracts.
**Consumes:** shared profile path. **Produces:** explicit per-profile fault matrix, no new authority abstraction.

- [ ] Add failing tests for every profile: unavailable scanner, malformed policy, quarantine write/delete failure, unapproved evidence, forbidden tool, truncated model stream, cancellation, poisoned skill catalog, and source change. Expected: existing rejection/hold behavior, no released unsafe text and no direct fallback.
- [ ] Add reviewed skill-removal test with matching registry/persona update; distinguish it from corruption. Test absent optional derived notes, reranker failure -> existing BM25 fallback and Assembly failure -> existing NumPy fallback; mandatory index corruption rejects.
- [ ] Add back-to-back different-profile/persona/skill requests; assert no context, chunks, trace or capability leakage. Test unavailable Diagnostic sink retains core verdict.
- [ ] Implement only missing seams needed for fault injection; do not weaken production checks to make mocks pass.
- [ ] Run focused matrix and `python scripts/test-local.py`, with TEMP/TMP under `data/tmp` on E:. Compare to 414-test/four-skip baseline; explain any changed skip count. Record exact command, duration, result and log.

### Task 6: Build reproducible secure benchmark

**Files:** create `scripts/benchmark_execution_profiles.py`, `evals/execution-profiles.json`, `tests/test_execution_benchmark.py`; write reports under `data/execution-profiles/`.
**Consumes:** normal sealed chat API, existing approved workload cases and quality rubric. **Produces:** owner-only benchmark CLI, numeric JSON rows and readable report; no raw model route.

- [ ] Test deterministic balanced scheduling, warm-up exclusion, percentile interpolation, sample std deviation, failure denominator, missing telemetry and redaction with synthetic rows. Assert profile payload contains no authority settings and 100 measured samples/configuration minimum for acceptance runs.
- [ ] Implement CLI with explicit base URL constrained to existing approved local owner route, output directory constrained to E:, fixed seed/workload fingerprints and resume identity checks. Save failures separately; do not silently drop them. Pace within existing budgets and abort rather than raise quotas.
- [ ] Record source/release/model/broker sampling/corpus/security fingerprints, request class, warm/cache/history/queue labels and per-request clocks. Report all specified summary metrics; task success and quality are explicit assessments, not inferred from HTTP 200.
- [ ] Run benchmark unit tests without services. Create run manifest: 20 fixed cases x five repetitions per profile, split across at least two sessions; balanced interleaving, warm-up separate, Diagnostic base recorded. Keep genuinely cold tests separate, without evicting active production GPU solely to manufacture cold state.
- [ ] Before live run, verify authorized service window and initial station state. Prepare isolated candidate through updater, retain all scan warnings and record readiness. Do not activate production. Execute at least 100 measured calls each for Verified, Ultra Fast and Diagnostic; report actual elapsed time and restore initial state.

### Task 7: Optimize fresh observations with controlled comparison

**Files:** create `runtime/execution_preflight.py`, `tests/test_execution_preflight.py`; modify `runtime/isolation.py` and context propagation only as needed; extend benchmark replay cases.
**Consumes:** existing batch observation helpers and unchanged validators. **Produces:** per-call fresh observation bundle, no security verdict cache.

- [ ] Write malformed/incomplete/stale-bundle tests; assert all existing container/image/mount/selection/GPU validations run and failures reject identically. Two calls must observe intervening state changes. Verified keeps existing observation behavior.
- [ ] Add identical-output frame replay tests against both bases, measuring acquisition, gate and release gaps; preserved bytes/security decisions required. Run failing tests first.
- [ ] Implement fresh batched collection for Ultra Fast and Diagnostic/Ultra Fast, retaining validator ownership in isolation. No reduced retrieval deadlines, sampling changes, reused approval or deferred output gates.
- [ ] Repeat fault matrix and full regression, then balanced benchmark from Task 6 for pre/post comparison with matched manifests. Predeclare pacing gates from `docs/RESPONSE_CONSISTENCY_2026_10_19.md`; retain its 10% regression threshold and one confirmation run rather than retuning thresholds after results.
- [ ] Reject promotion if security/quality/pacing fails, or explain if latency benefit is unproven. Do not represent the rejected earlier collector or direct raw timings as controlled evidence.

### Task 8: Evidence report and release handoff

**Files:** update `docs/architecture/engineering-report.md`, inventory/contracts/maps/scorecard; create `docs/EXECUTION_PROFILES_PERFORMANCE_2026_10_19.md` (use actual run date if later); document UI/profile semantics in appropriate existing user docs.
**Consumes:** executed tests, manifests and benchmark rows. **Produces:** final evidence-backed acceptance matrix and rollback instructions.

- [ ] Link each original requirement to source/test/report evidence; label missing live tests and unachieved targets explicitly. Record after-scores only for demonstrated changes, with confidence and no weighted aggregate.
- [ ] Report security parity, quality rubric, all latency/resource statistics and telemetry limits; distinguish correlation from causes. Keep stock-power conclusions separate from silicon-lottery speculation.
- [ ] Check relative links, `git diff --check`, changed source inventory, test commands/results and manifest reproducibility. Protect existing owner files and unrelated inactive feature changes.
- [ ] Document candidate scope, readiness, rejected/rollback evidence and retained warnings. Activation and commit/push stay pending explicit authorization. Mention LAN relogin and brief port rebinding if later activated; never claim zero downtime.

## Self-review and handoff

The design maps to Tasks 1-2 (interfaces), 3-4 (profiles/UI/trace), 5 (faults),
6 (measurement), 7 (measured optimization), 8 (report). The five Review Focus
conditions have assigned tests. Each runtime boundary has a single owner and
independent test seam; persistent MCP lifecycle and broad provider rewrites are
explicitly excluded. A faster result is not assumed. Native execution is
recommended because the transport, context and fault tests share one contract.
Owner review of this written plan is required before implementation.
