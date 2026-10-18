# LARPUS improvement review - 2026-10-17

Read-only engineering review of the checkout and selected frozen release. Only this report and an ignored evidence summary were written. No model, gateway, voice, authentication, dependencies or deployment settings were changed. No commit or push. This is a bounded reliability, quality and maintainability review, not an exhaustive security audit.

At inspection, release `c67982159d99487d8635f362ae673407` was active and the owner had selected Larpus 3.8. Local model health reported online/full GPU and selection ready. Station health had one nonpassing item: the retained static-scan warning. The owner's model selection was left untouched.

## Priority 1: Keep conversations intact when authentication expires

**Confirmed code-path risk.** `web/app.js:36` and `web/app.js:71` navigate the page to `/login` on HTTP 401. Conversation history lives in page memory, and `web/memory.js:3,21` defaults saved chats off and skips persistence while disabled. A LAN session invalidated by gateway activation can therefore discard an unsaved conversation at its next authenticated request. This follows directly from navigation plus the storage policy; a rendered browser reproduction was not available.

**Improve:** show a reauthentication panel and retain the transcript/draft in the current page, then retry only an explicitly submitted action after login. Preserve opt-in storage: do not silently start persisting chats to disk. Cover session expiry during idle polling, chat submission and streaming; prove history, draft and compression record survive.

## Priority 1: Restore a usable checkout verification gate

**Reproduced.** `python scripts/test-local.py` exits 1 before unit-test discovery because the complexity gate reports `NotesWorker.request` decisions 21 > 20 and module fan-out 8 > 7. `scripts/test-local.py:15-16` deliberately stops on this failure. These were already present before the switch feature; the active frozen candidate had its own passing preparation. A deployed release passing does not mean this checkout can currently pass its normal test command.

**Improve:** narrowly simplify the notes-worker retry/admission handling and its imports until the existing limits pass, retaining retry, truncation, append and producer-provenance behavior. Do not increase allowances merely to obtain green output. Then run the canonical isolated suite. Integrate the outstanding checkout changes in small, separately verifiable releases; do not deploy the entire dirty checkout just to synchronize it.

## Priority 1: Make failed recovery diagnosable and fail the owner command

**Reproduced with synthetic boundaries.** `runtime/model_switch.py:57-72` catches switch/recovery exceptions and writes generic state without using the project's bounded diagnostic reporter. `runtime/model_backend.py:43` also drops the owner subprocess failure detail. `scripts/model-switch.py:57` calls recovery without inspecting its result or failed final state. Two mocked causes (GPU allocation and weight identity) both left phase `failed`, emitted zero stderr diagnostic bytes, and let CLI `main()` return normally. No live fault was injected.

**Improve:** record a correlation ID and reviewed failure category, phase, operation ID and fixed model ID. Preserve safe numeric exit/error codes without dumping prompts or arbitrary stderr. Return a nonzero owner-command exit status if recovery remains failed and print a bounded actionable status. Keep successful restoration distinct from successful loading of the requested model.

## Priority 2: Put the new UI test on both automatic gates

**Confirmed enforcement gap.** `tests/model-switch-ui.cjs` passes when explicitly run, but is missing from `scripts/ci.py:8-9` and the release preparation loop at `scripts/releases.py:228`. Release preparation also runs fewer Node suites than CI. Python unit discovery does not execute these JavaScript files.

**Improve:** use a single explicit public UI-test manifest for CI, owner preparation and local verification. Include model-switch, diagnostics and speech-text suites where applicable. Test the runner itself so a failed listed suite makes preparation fail. Add a small rendered-browser acceptance path later for keyboard use, refresh/second-tab state, reauthentication and conversation preservation; the current fake-DOM harness is useful but does not establish those behaviors in a browser.

## Priority 2: Make factual quality and honest pushback measurable

**Confirmed evaluation limit, not a claim that 3.8 is inaccurate.** `scripts/evaluate-companion.py:17-25` defaults to catalog-contract mode. Live mode records mechanical checks and leaves `manual_scores=None`; it is not a factual-answer promotion gate. `runtime/inference.py:56-62` checks citation identifiers, not support for each claim. The UI already explains this distinction correctly.

**Improve:** start with a compact owner-reviewed set covering ordinary useful answers, absent evidence, false premises, source disagreement, dates and attribution. Compare 3.5 and 3.8 on identical evidence snapshots and output limits. Score technical correctness, explicit knowledge gaps, justified pushback and source support separately, alongside latency. Keep held-out questions apart from tuning examples. The existing behavior-tuning plan already provides much of this framework; implement its evaluation before adding training complexity.

A concrete historical regression case is the owner's supplied ODE/norm reply. For scalar `y'=y` with initial perturbation epsilon, the difference is `epsilon*exp(t)`; both scalar L2 and L-infinity norms equal its absolute value. Asking which detects instability first is unsupported. In a fixed finite-dimensional state space, equivalent norms do not change the qualitative stability classification. Require the model to correct that premise and qualify the cryptographic analogy. This is a proposed test based on the supplied earlier reply, not a fresh score of the selected model.

## Priority 2: Measure first-text delay by stage before changing concurrency

**Confirmed architecture; performance gain remains unmeasured.** `runtime/mcp_client.py:24` opens a fresh stdio MCP client for every tool call. `child_parameters()` invokes the current isolation preflight, which validates source and live container boundaries. `runtime/security_scan.py:28-48` hashes a broad source scope. The frontend reports first checked text, while `scripts/benchmark-chat-latency.py` currently benchmarks short fresh greetings. Historical paired measurements in CHAT_LATENCY.md did not demonstrate a general improvement for library questions.

**Improve:** collect local numeric timings for admission, boundary verification, MCP startup, retrieval, model first frame and first screened text, tagged by model and workload class. Include warm/idle starts, library questions and long conversations; report distributions, not a single greeting median. Do not record prompt text by default. Then test a bounded persistent MCP session or other measured removal of repeated setup, preserving per-request boundary checks, cancellation and the broker. Keep it only if whole-request latency improves without weakening rejection behavior. More CPU is an experiment, not an assumed fix.

No live latency benchmark was run during this review because it would consume the owner's interactive GPU slot.

## Priority 2: Document and rehearse owner-data recovery

**Documentation/verification gap.** The inspected update flow retains frozen releases but shares owner data across them. No dedicated station backup/restore script or runbook was found in the reviewed `docs/` and `scripts/` paths. This does not establish that the owner has no external backups. Application rollback is not restoration of a lost WSL disk, model cache, notes database, browser chat or TLS identity.

**Improve:** inventory recovery assets and exclusions, define an owner-controlled encrypted backup plan, and rehearse restoration to a separate location. Protect authentication/TLS material, distinguish disposable caches from irreplaceable originals/notes and explicitly handle browser exports. Keep quarantine under its separate restricted policy rather than copying it into an ordinary shared backup. Do not move or delete originals during a review or test.

## Priority 3: Make operational status precise and current

**Confirmed visibility gap.** `docs/STATUS.md:3-19` remains explicitly dated 2026-10-11 and names an older release; README's deployment table uses that snapshot. At inspection 16 owned source/config/test files differed from active payload and 17 were checkout-only. These are legitimate unfinished changes, not automatically deployed features. `runtime/health.py:99` uses one warning message for missing, stale, incomplete and findings-present scan evidence, although these require different owner actions.

**Improve:** provide a bounded owner status summary showing active release/model, pending checkout changes, notes state, functional readiness, and scan age/completeness/reviewed findings separately. Retain warnings honestly; do not make findings disappear to obtain green health. Update the dated deployment record from verified receipts and link feature-specific documents. Avoid publishing owner-private paths, source contents or credentials.

## Suggested order

1. Repair the checkout gate and add the omitted UI harness to automatic checks.
2. Fix reauthentication without losing conversation state, and recovery exit/diagnostic behavior.
3. Build the source-grounded quality comparison and stage timing measurements.
4. Use those measurements to choose a latency improvement; rehearse owner-data restoration.
5. Consolidate status documentation as part of each reviewed release.

## Verification actually performed

- Fresh local GETs: model selection ready, selected 3.8 online/full GPU; station health had only the retained scan warning.
- Canonical checkout test command: failed at complexity gate before unit discovery. No full-checkout Python pass is claimed.
- All eight existing Node harnesses passed when explicitly invoked, including model-switch UI.
- Public tracked-file inventory passed. This is not secret-content scanning.
- Synthetic recovery failure probes confirmed missing diagnostics and normal CLI return despite failed state.
- Compared owned checkout directories against the active payload; no private downloaded repository instructions were read or executed.
- No GPU answer benchmark, rendered browser acceptance, reboot/restore drill, hosted CI run or exhaustive security assessment was performed.

## Follow-up delivery

The first four approved fixes were implemented and activated in release `a4b76072c191467b86de8dac5eced963` after the owner saved/exported the LAN chat. See [reliability delivery evidence](RELIABILITY_2026_10_17.md). The quality-comparison and latency-measurement recommendations remain later work.
