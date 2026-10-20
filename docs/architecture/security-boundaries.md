# Security boundaries and mode-independent invariants

This is source-grounded architectural analysis, not an exhaustive exploit audit.
The untouched baseline suite passed 414 tests with four skips. No live containment,
LAN or attacker evaluation was performed in this audit phase; prior prepared-
release results remain separately scoped in [Skills acceptance](../MCP_SKILLS_ACCEPTANCE_2026_10_19.md).

| Boundary | Actual enforcement | Failure behavior / important limit |
| --- | --- | --- |
| LAN/browser → gateway | `gateway.Handler.trusted/authorized`, `Auth.session/allowed`; configured LAN TLS in `gateway.main` | Nonlocal peer/host/origin and missing session reject. Explicit same-host loopback bypass exists; do not describe it as password-protected remote access |
| Untrusted request → fixed local child | Strict gateway schema/size/persona check; `mcp_client` fixed tool names/argv/environment | Unknown tool/invalid body/child failure rejects; no URL/executable supplied by a request and no direct inference fallback |
| Host → sandbox deployment | `isolation.preflight/validate_container`: source fingerprint, rootless WSL isolation, pinned images, mounts/resources, OCI capabilities/devices, namespaces/pod networking | Drift/unavailable probes fail closed. A profile must not alter `mode()` to host or skip a validator |
| Text/skill/reference → model prompt | `agents.messages_for`, `skills.selected_prompt/load_skills`, `text_filter.inspect_message`, `reference_review.inspect_reference`, `knowledge.database/notes_database` | Persona allowlist + registry hash/path rules; prompt-only local files; scanner/index failures hold. Not a semantic injection guarantee |
| MCP Skills read → activation | `mcp_skills._list/_get/read_skill`, `skill_resources.resolve_skill`; actual selection remains `skills.selected_prompt` | Canonical registered URI and fresh verified resources; metadata/body read grants no skill or tool authority. Origin+URI and digest/size are evidence identities, not permissions |
| Agent → model | `local_ollama.local_response`, broker socket identity, `validate_chat/validate_lane/ensure_selected` | Fixed routes/templates/options, separate notes capability, approved model and bounded messages. No model-callable shell/filesystem/network tools |
| Shared GPU work → serialized execution | `Scheduler.charge/slot/probe`, `Job.cancel`, `idle_fence`; host Admission is cooperative priority | Reject budgets/queue/deadline/switching; failed cancellation confirmation faults generation closed. Do not remove probes as redundant model calls |
| Model frames → displayed/synthesized text | `inference.stream_reply`, `dlp.stream_pending/gate`, `gateway` replay branch, `voice.preflight` | Cumulative prefix, protected fragment hold, staged/fsynced private quarantine and pinned CPU voice. Pattern DLP is not complete semantic confidentiality assurance |
| Incomplete stream → conversation state | MCP final/progress equality, gateway error event, browser done/nonempty checks and atomic compression commit | Incomplete response excluded from saved history; no automatic duplicate inference retry through another backend |
| Failure details → owner/client | `diagnostics.describe/report`; public stable code/ID, redacted stderr records | Unreviewed messages, source lines, locals, prompts and credentials withheld. Sink failure does not permit failed operation |
| Owner maintenance → deployment/model control | `model_routes` authenticated routes, `ModelSwitch` and owner Backend, `releases` fixed lifecycle | Separate owner authority; maintain selection, prepared pins, drain/readiness/rollback. CLI raw model benchmark intentionally bypasses application gates and is not a chat capability |

## Required mode-equivalence matrix

For verified, ultra-fast and diagnostic requests, new tests must demonstrate the
same allow/deny results for unauthorized tools/personas/skills, malformed untrusted
skill content, missing/partial security observations, wrong image/mount/network/
source state, incomplete scanner results, protected data across token boundaries,
changed model selection, failed cancellation and interrupted streams. Test that
profile fields cannot add permissions, select host/direct transport or disable
mandatory modules. Current tests prove bounded existing cases, not this unbuilt
cross-profile matrix.

Relevant existing suites: `tests/test_isolation.py`, `test_isolation_snapshot.py`,
`test_broker_scheduling.py`, `test_streaming.py`, `test_mcp.py`,
`test_mcp_skills.py`, `test_mcp_skills_stdio.py`, `test_skills_health.py`,
`test_quarantine_acl.py` and `test_model_switch_regressions.py`.

## Intentional failure policy versus accidental coupling

An absent optional notes tier returns no derived notes, but a present invalid
manifest rejects (`knowledge.notes_database`). A missing CPU retrieval worker
can fall back to BM25, while required index/scanner failure cannot. A corrupt
registry document, an unnamed extra folder, or a duplicate id rejects the whole
catalog. A named skill file failure rejects that skill only, and a named
persona file failure rejects that persona only. The rejection is returned in
`rejected` and the skill prompt is not loaded. Owner removal
with a consistent newly reviewed registry is different from an unexplained file
disappearance. Optional evaluator failure cannot currently disable a security
check because no runtime evaluator hook was found; new separation still requires
tests when introduced.

## Bounds on assurance

No execution profile exists yet. Therefore mode-independent enforcement is a
design requirement, not a verified implementation result. Existing input regexes,
source metadata, sandboxing and DLP are different layers; no one layer proves
tool authorization, factual support or exfiltration prevention in general.
New prepared scans must retain reviewed warnings and disposition new findings,
not silently change allowances. No model/voice image, binding, auth or source pin
was changed during this audit.
