# MCP Skills Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish approved local skills through standard MCP Skills methods without changing chat authority, instruction bytes, security checks or the three-tool interface.

**Architecture:** Add a verified registry-resource layer and a public-SDK extension to the existing stdio server. Keep the current chat client and selection path; protocol discovery/read never activates skills. Profile optional request-local reuse independently; retain no unsupported permission cache.

**Tech Stack:** Python 3.10, installed mcp==2.3.0 and mcp-types==2.3.0, standard library, unittest, existing E:-backed WSL/rootless Podman release tooling. No new dependency.

**Spec:** [approved design](../specs/2026-10-19-mcp-skills-design.md); [compatibility evidence](../../MCP_SKILLS_COMPATIBILITY_2026_10_19.md). Architecture approved by the owner after `f1edb3f`; implementation plan approved by the owner; native execution underway.

## Global Constraints

- Extension identifier `io.modelcontextprotocol/skills`; modern revision `2026-07-28`; old three-tool path remains usable at `2025-11-25`.
- Preserve `chat_local`, `local_status`, `list_personas` and their exact approved descriptors. Do not add model-callable tools, remote ingestion, installers or execution privileges.
- Use exactly `skill://<registered-id>/SKILL.md`, at most 128 skills and 16000 raw bytes per file; one SKILL.md per skill.
- Pages contain at most 16 whole entries; no optional directory-read method. Modern cache fields are explicitly ttlMs=0 and cacheScope=private; successful resultType=complete.
- Keep existing full verification and persona authorization. Resource reads are not activation. Hash equality proves byte consistency, not authorship or benign intent.
- Preserve selected instruction bytes, weights, quantization, context, broker, GPU placement, retrieval, budgets, voice, DLP and authenticated HUD behavior.
- No unprotected cross-request cache, automatic skill selection or extra inference call. More than roughly 5 percent median first-text regression requires review, not automatic acceptance.
- Keep artifacts/temp on E:, CPU limits/power settings unchanged. Keep an already-running station available; return temporary tests to the prior stopped state.
- Freeze a candidate from selected release `7df2e957751642d6ace4630fa047fe94` plus explicit Skills hunks. Exclude collector experiment `ddf716bcc1f04df891de7545f2052b64`, unrelated dirt and unrelated newer commits.
- Never modify frozen pins/receipts or relax scan findings to pass. Stage/prepare via owner updater; no activation from plan approval. Scoped repository publication follows owner authorization and verified gates; unrelated changes stay unstaged.

## Review Focus

1. A registry/body change between list pages or between manifest/read must reject stale cursors/content, not reuse a prior verdict (Tasks 1, 2, 4).
2. Filesystem/parser failures must not expose workstation paths through SDK error serialization (Tasks 2, 3).
3. Modern metadata requires version and clientCapabilities; clientInfo is optional in the inspected base SDK. Do not accidentally reject a compliant client lacking clientInfo (Task 3).
4. Matching URI/name from a different host-assigned server identity must not become approved local instruction content (Tasks 1, 3).
5. Repeated requests in one process and cold child startup must not turn request-local reuse into a long-lived permission cache or eager content transfer (Tasks 2, 4).

---

## File responsibilities and execution setup

Use an isolated worktree on E: at execution time after reading using-git-worktrees. Record HEAD, origin/main, root dirt, selected/prepared release IDs and initial running/task state. Do not copy uncommitted root changes into that worktree. Use E:-local TEMP/TMP for every test/build command. Do not start LARPUS during pure implementation/unit/protocol work.

- `runtime/skills.py`: existing registry authority and bounded file verification; keep public return shape and selected_prompt behavior.
- New `runtime/skill_resources.py`: exact frontmatter, operation-local verified resource records and canonical URIs; no SDK or execution dependency.
- New `runtime/mcp_skills.py`: typed protocol results, paging, extension methods, standard resource registration and sanitized errors; no inference dispatch.
- `runtime/mcp_server.py`: attach the extension to the existing server; tool bodies/schemas unchanged.
- `runtime/mcp_client.py`: add a read-only discovery-surface observation for health/tests; do not change chat/stream call behavior.
- `runtime/health.py`: check expected extension/resources alongside existing tool snapshot, in the same discovery connection rather than extra per-chat calls.
- New focused tests, one owner benchmark script, and Skills/MCP acceptance documentation. Do not change shared dependencies or complexity allowances.

### Task 1: Verified registry resources with unchanged activation bytes

**Files:** modify `runtime/skills.py`; create `runtime/skill_resources.py`, `tests/test_skill_resources.py`; extend `tests/test_skills_health.py` where common-loader behavior is exercised.

**Interfaces:** `VerifiedSkill` frozen record containing `identifier: str`, `raw: bytes`, `frontmatter: dict[str,str]`; `verified_catalog() -> dict[str,VerifiedSkill]`; `parse_frontmatter(raw: bytes, identifier: str) -> dict[str,str]`; `skill_uri(identifier: str) -> str`; `resolve_skill(uri: str, catalog: dict[str,VerifiedSkill]) -> VerifiedSkill`; `skill_entry(skill: VerifiedSkill) -> dict`. Calls perform no inference and keep no cross-request state.

- [ ] Write failing tests `test_all_69_entries_match_raw_bytes`, `test_frontmatter_uses_file_not_display_metadata`, and `test_selected_prompt_bytes_unchanged`. Assert entry name equals registered ID, description equals file frontmatter, resource digest equals `sha256:` plus raw hash, size equals raw byte length; selected_prompt equals the original prefix plus exact UTF-8 file text.

```python
self.assertEqual(entry['resources'][0]['size'], len(raw))
self.assertEqual(entry['resources'][0]['digest'], 'sha256:' + hashlib.sha256(raw).hexdigest())
self.assertEqual(skills.selected_prompt(persona, identifier).encode(), b'\n\nLocal authored skill:\n' + raw)
```

- [ ] Add parameterized negative fixtures for changed/truncated/oversized bytes, invalid UTF-8, duplicate IDs/keys, malformed or unsupported frontmatter (including allowed-tools/hooks), unregistered origin/files/folders, symlink/regular-file violations and scanner failure. Test a one-word plain-string description as in existing fixtures; reject ambiguous YAML scalars/tags/aliases/structured forms. For symlinks include supported-platform tests and explicitly report unavailable cases.
- [ ] Run `python -m unittest tests.test_skill_resources -v`; observe failures for the missing functionality before implementing it.
- [ ] Implement the interfaces using the current registry/filters. Bound file reads to 16001 bytes, reject non-regular/escaping paths and unexpected root entries. Preserve existing load_skills record fields and return text without newline/Unicode rewriting; recover resource raw bytes from that verified UTF-8 text or a shared internal read, never a second unchecked read. Every operation freshly validates the whole catalog.
- [ ] Test wrong persona, unknown skill and foreign URI/server content through `inference.chat` with the upstream/model boundary spied: zero model calls. Discovery/resource helpers alone must never call inference. Full frontmatter mismatches in a client-side test fixture reject before use; do not invent a production foreign-content activation bridge for the test.
- [ ] Run `python -m unittest tests.test_skill_resources tests.test_skills_health -v` in the public fixture harness when owner knowledge is required. Preserve baseline fixtures rather than reading private data. Record pass/failure counts; review this unit before moving on.

### Task 2: Minimal standard extension and resource serving

**Files:** create `runtime/mcp_skills.py`, `tests/test_mcp_skills.py`.

**Consumes:** Task 1 interfaces. **Produces:** `LocalSkillsExtension(Extension)` with identifier above and public MethodBinding methods; `register_skill_resource(server: MCPServer) -> None`; `list_skill_page(catalog, cursor: str | None) -> tuple[list[dict],str | None]`; typed ListSkills/GetSkill params/results derived from SDK request/pagination/cache bases. Constructors/registering handlers must not load the catalog.

- [ ] Write failing tests using a real SDK Client and a temporary MCPServer with this extension/resource registration. Assert discovery advertises the extension with empty settings and Resources, skills/list/get have identical entries, and `resources/read` reconstructs exact raw bytes. No tool contribution and no directoryRead advertisement.
- [ ] Add tests `test_pages_are_atomic_and_content_bound` (69 entries: page lengths 16,16,16,16,5), empty catalog, unknown/malformed/stale cursor, and changes between list/get/read. Use a versioned opaque base64url cursor containing catalog digest and integer offset, at most 256 characters; offsets must be nonnegative page boundaries strictly below the catalog size. This is pagination state, not authorization.

```python
self.assertEqual([len(page['skills']) for page in pages], [16, 16, 16, 16, 5])
self.assertEqual(reply['result']['resultType'], 'complete')
self.assertEqual(reply['result']['ttlMs'], 0)
self.assertEqual(reply['result']['cacheScope'], 'private')
```

- [ ] Add raw-response assertions for resultType=complete, ttlMs=0, cacheScope=private and correct resource URI/content. Catalog digest covers sorted canonical entry data including raw digests; require every entry complete on each page. List responses contain no SKILL.md body. List/get/read each invoke a fresh catalog verification.
- [ ] Run `python -m unittest tests.test_mcp_skills -v`; verify expected failures before code.
- [ ] Implement supported SDK Extension/MethodBinding APIs, restricted to modern revision. Use standard resource registration for the exact skill URI template; never override a base method via an extension binding or register it as a tool. Reject noncanonical/encoded/query/fragment/other-scheme URIs by exact lookup. Map unknown URI/cursor to modern -32602 and verification/internal faults to sanitized -32603.
- [ ] Run the suite. Inspect serialized JSON-RPC rather than assuming model_dump or SDK defaults satisfy the wire. Verify absent/malformed entries, duplicate manifest records, wrong size/hash/frontmatter and truncated reads reject in verification test-client code; no network lookup or automatic activation occurs.

### Task 3: Existing server, real stdio and health integration

**Files:** modify `runtime/mcp_server.py`, `runtime/mcp_client.py`, `runtime/health.py`, `tests/test_mcp.py`, `tests/test_skills_health.py`; create `tests/test_mcp_skills_stdio.py`. Do not modify config/mcp-approved.json to accommodate tool drift.

**Consumes:** Task 2 extension/registration. **Produces:** unchanged existing server with additive extension; `surface_async() -> dict` and `surface() -> dict` in mcp_client returning `{protocol_version, capabilities, tools}` from one fixed-executor SDK connection. Existing call/chat/stream/health tool invocation signatures and behavior stay unchanged.

- [ ] Write failing tests comparing sorted existing tool descriptors exactly to the approved snapshot. Exercise modern Client against the existing server, forced legacy Client at 2025-11-25, unknown tool named skills/get, and normal streaming/DLP/filter paths. New surface observation reports only metadata, never skill bodies or an arbitrary remote server.
- [ ] Write genuine stdio tests: launch the existing module using fixed Python, fixture cwd and bounded child environment; modern Client explicitly selects 2026-07-28 and verifies list/get/read/pagination/cache fields. A raw JSON-line peer sends missing/wrong `_meta`, version/capabilities and invalid URIs without SDK auto-correction. Missing mandatory metadata returns -32602; a valid request without clientInfo succeeds; unsupported modern revision returns -32022. Assert extension methods at legacy revision are method-not-found (-32601) while all original tools remain usable. Test legacy resource errors using the pinned base revision's defined semantics.
- [ ] Run the new tests and observe failures. Fixtures patch model I/O and reset rate counters; never reach a real GPU just to test protocol. Invalid skill/persona or failed verification must produce zero model calls. Error strings must exclude temporary absolute paths.
- [ ] Attach the extension/standard resource callback, keeping all tool decorators unchanged. Add metadata-only surface discovery; health consumes its tools and capabilities from the same connection formerly used for discovery. Keep security_scan.discover's exact tool-only contract unchanged. Update synthetic health mocks so tests do not accidentally invoke live WSL. No extra discovery/get/read on the normal chat path.
- [ ] Run `python scripts/test-local.py`, each `node tests/<name>` from the fixed `scripts.ui_checks.TESTS` manifest (ui_checks.py itself only defines the manifest), `python scripts/broker-prompts.py --check`, `python scripts/evaluate-companion.py`, and `python scripts/complexity.py check`. Preserve failures independently; no allowance changes. Run raw stdio tests on Windows and Linux fixtures, labeling any missing platform evidence.
- [ ] Request a fresh scoped code review covering registry, protocol boundaries, models/metadata, privacy and activation invariants; fix important findings before performance/release work. Keep unrelated root changes out of the review.

### Task 4: Benchmark harness and offline loading profile

**Files:** create `scripts/benchmark_mcp_skills.py`, `tests/test_mcp_skills_metrics.py`; extend `scripts/performance_metrics.py` with additive p95 and `skills` stage only if needed; write `docs/MCP_SKILLS_PERFORMANCE_2026_10_19.md`. Existing metric keys and eight-case suite remain usable.

**Interface:** owner CLI `python scripts/benchmark_mcp_skills.py --baseline ID --candidate ID --repeats 6 --warmups 1` is plan-only by default; `--run` performs sequential fixed local MCP tests. `--cases focused|existing8` selects either the three fixed selected-skill cases below or unchanged cases from evals/performance.json. Validate 32-hex prepared IDs; no arbitrary executable/server URL. Store raw records, manifest and summary under `data/evals/mcp-skills/<new-id>/`, never overwrite existing receipts. Use existing performance_metrics.distribution semantics with nearest-rank p90/p95 and excluded warmups; absent/failed timings are not zero.

- [ ] Write failing metrics/harness tests for exclusion of warmups, failure denominators, percentile ranks, missing stages, changed identities, stale approvals, interrupted runs and complete raw receipts. A partial run cannot be called a valid comparison. Test no inference or child execution occurs without --run.
- [ ] Implement the minimal harness, recording release/source/SDK/model/options/corpus/selected skill hashes, standalone measured skill-validation cost alongside existing per-request stages, approved chunk arrivals, first/final times, full evidence identities and manual answer-review fields. Request-local test instrumentation must not alter instruction bytes or inference options. Keep raw answers private/ignored.
- [ ] Profile Windows full/selected loading with all current verification. Add the same fixed profiler to the harness for isolated Linux use after preparation in Task 5. B keeps current verification semantics; do not infer a chat-stage cost from standalone timings.
- [ ] Run `python -m unittest tests.test_mcp_skills_metrics -v` and the CLI without --run; expect metrics tests to pass and a request plan with no child, listener or inference execution. Live measurements belong to Task 5 after preparation.


### Task 5: Frozen preparation, acceptance matrix and handoff

**Files:** update `docs/SKILLS.md`, `docs/MCP.md`, `docs/UPDATES.md`, `docs/MCP_SKILLS_COMPATIBILITY_2026_10_19.md`; create `docs/MCP_SKILLS_ACCEPTANCE_2026_10_19.md`. Candidate source and receipts live only in ignored E: owner data.

**Consumes:** reviewed implementation and Task 4 harness. **Produces:** separately identified prepared candidate, interoperability/security/performance reports, explicit activation decision and rollback command. Execution order is Tasks 1-4, then preparation, live measurements and acceptance within Task 5; no dependency on a later task.

- [ ] Before touching services, record running state, selected/previous releases, notes-task state, model/voice identities/images, binding/auth and source/corpus pins. A plan-approved temporary benchmark window starts only existing local services, no new background notes jobs or dependencies. If initially stopped, restore stopped state at the end even on failure.
- [ ] Build an unfrozen source tree from the selected release; apply only the Skills change hunks and new tests. Do not copy whole newer versions of mcp_client/health/skills blindly, because frozen and main may contain unrelated differences. Confirm the payload diff contains only the named Skills changes; preserve the consistent knowledge index and all broker/model/voice/dependency pins. Add only source-only provenance prerequisites already required by staging.
- [ ] Run `python scripts/releases.py stage --source <E-source>` and `python scripts/releases.py prepare ID`. Record local/UI/companion/isolation/static results, exact scan inventory and retained warnings. No modifying frozen payload/pins/receipts or reclassifying warnings to get green. Stop at a genuine compatibility/scan blocker and retain diagnostics.
- [ ] Run the actual Skills stdio client against the prepared isolated agent, including modern/legacy discovery, pagination/get/read and negative traversal; record SDK parity and approved three-tool equality. Run the existing behavioral isolation probe and verify no listener, mount, capability or direct-model route addition. Do not call host-only mock tests Linux containment proof.
- [ ] Run the isolated Linux full/selected loader profiler. Propose C only for a measured duplicate operation within one request/operation; first add a failing equivalence/tamper test in the owning unit, then implement/review and prepare a separate C snapshot with identical prompt/security semantics. No startup/periodic verdict reuse. If no meaningful safe optimization exists, record C not adopted and keep B.
- [ ] Run A/B (and C only if justified) using the Task 4 fixed MCP harness: same selected skills, six measured balanced alternating rounds after one excluded warmup. Focused cases are home-assistant/home-planning, it-larp-coach/it-interview and mathematician/math-differential-equations. Keep cold observations separate; compare instruction bytes, approval decisions, evidence and generated outcomes.
- [ ] Run the existing HTTP eight-case suite on the selected baseline: `python scripts/performance_suite.py --run --repeats 3 --warmups 1 --seed 5900 --retain-answers`. Run the unchanged eight-case catalog through matched MCP transport for both A and B using `--cases existing8 --repeats 3 --warmups 1 --run`. No second gateway/listener and no unauthorized activation to benchmark B. Compare matched MCP timings only; baseline HTTP checks are a separate regression receipt. Candidate HTTP/browser acceptance remains explicitly pending until authorized activation.
- [ ] Review >5 percent median first-text regression, failure/evidence differences and cadence regressions. If a pacing metric rises >10 percent, investigate with a single predeclared confirmation; retain every result, with no retry-until-pass. Apply the explicit manual grounding rubric, separating citation identifiers from claim support.
- [ ] Obtain a fresh whole-change review. Populate a per-case status matrix: pass, fail, unverified, with receipt references for every required protocol/security/regression item. Mark unsupported frontmatter deliberately rejected, and live/browser/second-device limits explicitly.
- [ ] Update documentation with implemented behavior, exact client examples, raw-byte checks, server+URI provenance, no-activation semantics, performance and remaining risks. Compare original selected_prompt bytes across every registered/allowed pair; no model/system/broker prompt pin changes are permitted to hide a difference.
- [ ] Do not activate automatically. Handoff prepared ID, tests/metrics, limitations and concrete `python scripts/releases.py activate ID` / `rollback` steps for owner review. If activation is subsequently authorized, validate prepared status, drain/readiness/automatic restore and current bindings/auth; retain previous release. Do not promise zero downtime; LAN re-login may be needed.
- [ ] Drain/stop any temporarily started gateway and only verified LARPUS containers, terminate Larpus WSL, confirm empty running inventory and original disabled nightly task. Do not query Podman after termination and accidentally restart WSL. Preserve independent shutdown receipts.

## Self-review and execution handoff

Spec coverage: registry/security/bytes (Task 1), wire/caching/pagination (2), old client/health/stdio/regression (3), A/B/C/grounding/cadence (4), frozen isolation/rollback/availability/docs (5). All five Review Focus conditions have owning tests. Live benchmarking is ordered after candidate preparation inside Task 5; candidate HTTP/browser tests are explicitly deferred rather than bypassing the activation boundary. No new protocol code, dependencies or running services are authorized merely by writing this plan.

Recommended execution method: **native** in this session using executing-plans, because the five tasks share the verified resource records and one server integration. Use a fresh reviewer after integration and before final acceptance. Subagent-driven implementation remains an alternative if the owner chooses it. Review/confirm this written plan before implementation; the preceding approval covered the architecture actually presented.
