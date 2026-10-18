# Larpus Model Selector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an authenticated station-wide 3.5/3.8 model selector with truthful load-time messaging, progress, preserved conversation and verified failure recovery.

**Architecture:** Extend the existing Windows owner gateway, offline Ollama service and broker. A fixed owner-side controller publishes a small atomic selection/status document read-only to the broker; the agent can observe selection but cannot request a switch. Reuse the current model server and pinned images; one GPU model is loaded at a time.

**Tech Stack:** Existing Python standard library, Windows/WSL rootless Podman, local Ollama, existing vanilla JavaScript HUD and unittest/Node harnesses. No new packages or ports.

**Spec:** `docs/superpowers/specs/2026-10-17-model-switch-design.md` (owner approved).

## Global Constraints

- Display **Larpus 3.5 27B Q4** and **Larpus 3.8 27B Q4**; preserve exact upstream identities/checksums separately.
- Use exactly the warning copy in the spec; no fabricated countdown or fixed load-time guarantee.
- Preserve gateway, CPU voice, conversation and browser-local memory during switches.
- Preserve context/output/filtering/prompt approvals; 131,072-token chat context on 3.8 requires an actual full-GPU warm-up check.
- No arbitrary model tags, download commands, owner-control MCP tools, CPU/cloud fallback, authentication/binding/image/dependency changes.
- Refuse switching during GPU notes maintenance; never cancel that work implicitly.
- Use staged releases, preserve unrelated edits and retain static warnings. No commit or push unless requested.

## Review Focus

- Refreshing or opening a second tab during loading must show the same real operation and prevent a competing switch (Tasks 2 and 4).
- A stale client must never bypass selection or cause the old model to reload during a switch (Tasks 1 and 3).
- A note already generating must keep its model; the next note may use the new selection only with accurate producer metadata (Tasks 2 and 3).
- A target-model failure followed by failed restoration must remain visibly failed and recoverable after owner-process restart (Task 2).
- A model installed on disk but unable to fit the approved context fully on GPU must not be reported available/ready (Tasks 2 and 5).

## File boundaries

Create `config/model-selection.json` for the two fixed catalog entries and weight pins. Create `runtime/model_selection.py` for platform-neutral catalog/state validation and broker-visible read-only selection. Create `runtime/model_switch.py` for Windows owner-side operations and journaling only. Create `scripts/model-switch.py` for owner status/recovery and reviewed cache preparation. Create `web/model-switch.js` for selector/status behavior. Extend existing broker, inference, notes, health, release/isolation wiring and gateway/HUD without restructuring unrelated code.

### Task 1: Fixed catalog and broker selection contract

**Files:** create the catalog and `runtime/model_selection.py`; modify `runtime/inference_broker.py`, `config/inference-broker.json`; test `tests/test_model_selection.py`, `tests/test_inference_broker.py`.

**Interfaces:** `catalog(root) -> dict`; `read_selection(path, catalog) -> dict` returns `active_id`, `target_id`, `phase`, `operation_id`, `error`; broker status includes validated `active_model` and `switching`. Selection is writable only by the owner controller; agent mounts remain unchanged.

- [ ] Add failing tests named `test_only_two_pinned_local_models`, `test_invalid_or_missing_state_fails_closed`, `test_switching_refuses_new_generation_but_allows_status`, `test_request_cannot_select_an_inactive_model`, and `test_inflight_request_keeps_its_original_selection`. Assert malformed IDs/paths/options are rejected, while existing framing/prompt/token controls remain enforced.
- [ ] Run `python -m unittest tests.test_model_selection tests.test_inference_broker`; verify the new tests fail for missing behavior.
- [ ] Implement the validated fixed catalog and versioned broker policy, preserving old policy compatibility for existing frozen releases. Publish selected-model metadata through existing read-only status responses; no switch route on an agent-mounted socket.
- [ ] Re-run the focused tests; require all pass and retain tests for arbitrary tags, unexpected routes and prompt hashes.

### Task 2: Owner controller, cache maintenance and recovery

**Files:** create `runtime/model_switch.py`, `scripts/model-switch.py`; modify `scripts/releases.py`, `runtime/isolation.py` only for explicit read-only broker selection mount/profile validation; test `tests/test_model_switch.py` and existing release/isolation tests.

**Interfaces:** `ModelSwitch.status() -> dict`; `ModelSwitch.request(model_id: str) -> dict` returns existing/no-op/new operation status; `ModelSwitch.recover() -> dict`. Controller accepts only catalog IDs. `scripts/model-switch.py` exposes fixed `status`, `prepare-cache`, `recover` owner operations without arbitrary executable/path inputs.

- [ ] Add failing tests for duplicate requests, current-model no-op, update-lock conflict, active GPU notes refusal, waiting for current inference, blocked new inference, strict unload-before-load order, target verification failure, successful restoration, failed restoration, and restart recovery. Mock only Podman/model boundaries; assert durable state and ordering.
- [ ] Run `python -m unittest tests.test_model_switch` and confirm the new tests fail.
- [ ] Implement a background switch worker with the existing owner update lock, atomic state/journal writes and bounded waits. Publish a switching phase before waiting for broker idle; snapshot the selected model per in-flight generation. The controller must not stop gateway or voice, or expose Podman to the agent.
- [ ] Implement fixed owner calls to unload/load/warm/inspect the selected model using the existing pinned offline images. Validate exact model tag, weight pin, context and full GPU residency. Only commit the ready selection after checks pass; recover the prior selection on failure.
- [ ] Implement checksum-verified owner cache preparation for the already-downloaded 3.8 artifact. Never write active frozen payloads or replace model images/dependencies. Document and journal the cache-maintenance scope separately from app activation.
- [ ] Run focused model-switch, release and isolation tests. Confirm failed restoration remains an explicit failed state with a usable fixed recovery command.

### Task 3: Inference, health and background-note compatibility

**Files:** modify `runtime/inference.py`, `runtime/health.py`, `runtime/notes_worker.py`, `scripts/study-notes.py` as needed for current-model observation and accurate note provenance; tests `tests/test_model_selection.py`, existing broker/notes/health tests.

**Interfaces:** inference resolves the active model from validated broker status rather than a browser-supplied tag. Existing persona/messages/skill chat APIs stay unchanged. Notes resolve and record the actual producing model at a window boundary; a switch does not rewrite an in-flight job or misattribute output.

- [ ] Add failing tests that an old HTTP chat body follows the station selection, GPU checks use the actual selected tag, statuses distinguish switching from ready, voice remains independent, and note producer identity matches the response. Assert notes requests cannot choose arbitrary tags.
- [ ] Run the focused tests and confirm failures before implementation.
- [ ] Implement dynamic active-model observation for inference and health, keeping prompt construction and all security/output/context controls unchanged. Implement model-aware note window admission/producer provenance without changing completed-window keys or reprocessing held/completed notes.
- [ ] Re-run focused inference, notes and health tests; verify both approved models and stale-client/switch-race cases.

### Task 4: Authenticated endpoints and HUD controls

**Files:** modify `runtime/gateway.py`, `web/index.html`, `web/app.js`, `web/style.css`; create `web/model-switch.js`; test `tests/test_model_switch_gateway.py`, `tests/model-switch-ui.cjs`, existing chat/context/memory/voice UI tests.

**Interfaces:** `GET /api/model-selection` returns catalog availability and current operation; `POST /api/model-selection` accepts exactly `{model_id: <approved ID>}` and returns asynchronous status. Neither endpoint is an MCP tool. `bindLarpusModelSwitch(...)` uses the existing same-origin API helper and reports active/requested model separately.

- [ ] Add failing gateway tests for unauthenticated LAN requests, foreign origins, extra fields, arbitrary IDs, duplicate requests and busy-maintenance responses. Test that no chat-request schema change is required.
- [ ] Add failing UI tests: selecting alone sends no request; explicit Switch shows the exact warning; active model is separate from requested; refresh/second tab observes the same operation; duplicate submits/chat are disabled while switching; ready/rollback/failure copy reflects server state; conversation/local memory are untouched.
- [ ] Run `python -m unittest tests.test_model_switch_gateway` and `node tests/model-switch-ui.cjs`; confirm expected failures.
- [ ] Implement endpoints with existing auth/origin/rate-limit handling and bounded JSON. Add compact controls beside the model display, warning text and real stage labels. Reuse existing layout and API patterns; no new frontend dependencies or forced page reload/login.
- [ ] Run the focused gateway/UI tests and existing chat/context/memory/voice UI harnesses; require all pass.

### Task 5: Controlled live validation and staged delivery

**Files:** owner maintenance receipts under `data/model-switch/`; `docs/MODEL_SWITCHING.md`; isolated candidate source based on the active frozen release.

- [ ] Check the notes GPU journal is `chat-restored`, owner update lock is free, and all required station checks pass before maintenance. Preserve model/voice container identities/start times and saved conversation state.
- [ ] Prepare the 3.8 shared-cache artifact through the fixed owner tool and verify checksums. Keep live services running during copying and app implementation/preparation.
- [ ] Run required local tests, complexity, MCP discovery and security scans through the release workflow. Inspect any changed finding inventory rather than weakening the gate. Keep unrelated working changes out of the candidate.
- [ ] During the scoped live test, switch 3.5 -> 3.8 -> 3.5, verifying actual full GPU residency and 131,072-token context, successful chat, truthful UI stages and voice continuity. A filled-context quality/throughput claim is outside this check. Confirm the old chat body and refreshed tabs still work. Exercise target-load failure recovery with controlled fixtures; do not pretend a mock proves live rollback.
- [ ] Record observed cold/warm durations and any availability interruption. If 3.8 cannot meet approved GPU/context readiness, leave it unavailable with the concrete reason and restore 3.5; do not silently reduce context or enable CPU fallback.
- [ ] Stage/prepare/activate the isolated candidate with the normal live broker check and retained warnings. Verify serving HTTP, CA-verified LAN authentication, both switch directions and final readiness. Document recovery and the remaining limits honestly. No commit or push.

## Self-review

The five review-focus conditions each map to explicit failing tests above. The proposal preserves the existing chat API, two-model allowlist, conversation and voice, and separates shared-cache maintenance from app delivery. No new packages, owner-control MCP surface, arbitrary model selection or false readiness claims are introduced. The live 3.8 chat-context qualification is a delivery gate, not an assumed result of the previous 8,192-token notes run.

## Execution handoff

Recommended method: **Native** implementation in this session, task by task, with one fresh final reviewer. These tasks share the selection/state contract closely; keeping implementation in one context reduces interface drift. No implementation or commit has been performed yet. The owner reviews this plan and selects the execution method before code changes.

Execution completed 2026-10-17. See `docs/MODEL_SWITCHING.md` and `data/model-switch-ledger.md` for implementation rulings, live evidence and limits. Native implementation and fresh review completed; no commit/push.
