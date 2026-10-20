# Practical module contracts

This documents existing contracts and the implemented checkout profile boundary. It does not
create a universal plugin interface. Source responsibilities are in
[inventory](module-inventory.md); stage categories are in
[pipeline](execution-pipeline.md).

## Implemented profile seams (not activated)

- `source_integrity.fingerprint(root: Path) -> str`: fresh stdlib-only source
  hashing. Scanner wrapper preserves its root; isolation no longer imports scanner
  orchestration. Golden legacy-scope/freshness/size/symlink and clean-import tests
  are in `test_source_integrity.py`.
- `execution_profiles.resolve(value=None) -> ExecutionContext` and
  `to_wire(context) -> dict`: immutable canonical request values, no environment,
  model, transport or permission state. Strict defaults and negative-value tests
  run independently of live services.
- `execution_preflight.observe(names, command, run) -> dict`: one bounded fresh
  acquisition with injected launcher; no cached verdict. `isolation.read_snapshot`
  validates identities, and the same `isolation.preflight` policy validators own
  approval in both bases. The probe and all new runtime modules are included in
  the fixed scanner source-copy inventory.
- `execution_trace.Trace`: request-local numeric points, cumulative gate duration,
  gate count and maximum approved-release gap. Screening callbacks still run
  exactly once; clock failure cannot turn a rejection into approval. Disabled
  detailed tracing does not sample its clock. No prompt/answer storage.
- MCP's three argument schemas remain unchanged. Canonical `larpus_execution`
  metadata is revalidated in the child; optional trailing internal execution
  parameters preserve callers. Explicit client profiles require sealed isolation;
  owner host fixtures remain outside that production guarantee.

Gateway admission timing is labeled separately from child clock measurements.
Browser Diagnostic records monotonic DOM-update and frame-opportunity durations
in reply element numeric dataset fields, without exporting content. A frame
callback does not prove physical screen paint. Real rendered acceptance is pending.

The complexity baseline explicitly records three new dependency edges groups:
gateway +1 profile import, inference +2 profile/trace imports, MCP client +1
profile import. Function/global decision and length ceilings were not raised;
chat-request validation was extracted from the large handler. These are auditable
dependency costs rather than a claim that adding files alone creates modularity.

## Existing distinct contracts

| Boundary | Input → output | Owner, failure and test seam |
| --- | --- | --- |
| Gateway admission | JSON persona/history/skill/speak → bounded validated operation or HTTP error | `gateway.Handler`, Auth and Admission own external framing/identity/priority; test with fake MCP, never an arbitrary user backend |
| Persona construction | `agents.messages_for(persona, history, skill=None)` → system/user/assistant list | Trusted persona config + untrusted filtered history; invalid role/skill fails before model handoff; no tool grant in persona text |
| Skill activation | `skills.selected_prompt(persona, identifier)` → exact approved prompt suffix | Persona membership + fresh registered catalog; `None` yields no skill text; read-only discovery does not activate |
| Skill discovery | `verified_catalog`, `skill_entry`, `resolve_skill` → exact URI/frontmatter/hash/size/body | Fixed prompt-only capability, local-authored provenance. Ancillary executable/path/privilege content rejected; no need to invent an executable skill runner |
| Evidence | `knowledge.augment(prepared, persona)` → prepared messages + selected source records | Read-only hash-verified original passages and trust labels; required failures reject, optional engine absence degrades only as declared |
| Retrieval engine | `neighbors(question, limit)`, `rerank(question, passages, deadline)` → row IDs/scores | Engine and RemoteEngine already share this shape; worker protocol bounds inputs/results. Unavailable enhancement keeps BM25 |
| Scorer | `Pipeline.score(query, limit=18)` → NumPy-compatible score array | Actual kernel replacement, same vector/index ownership; close/failure/ambiguity behavior tested, NumPy fallback visible |
| Model stream | `local_ollama.chat_stream(payload, timeout)` → bounded model frames | Fixed broker socket/routes, approved selected model/options. Test via adapter/HTTP fixtures; do not make production accept arbitrary provider URLs |
| Broker admission | socket-derived lane + exact system/options → slot/job or `Refused` | Scheduler owns token/request/deadline/cancellation state; optional quality code cannot grant a slot or clear a fault |
| Output release | `dlp.gate(text, system_prompt)` → approved content or held result | Entire prefix and protected lookahead, private staged storage; failed policy/storage rejects. A token-by-token no-op replacement is not equivalent |
| Model maintenance | ModelSwitch backend methods `read`, `publish`, `idle`, `load`, `verify`, `unload`, `exclusive` → state stages | Owner backend is already injected for tests; rollback/recovery explicit. This does not establish ordinary inference provider portability |
| Diagnostics | `diagnostics.report(code, exception)` → bounded public ID + redacted owner record | Observability cannot convert a failed required operation into allow; no exception locals/prompts in public telemetry |

## Minimum characteristics for new independently replaceable work

Each component must name: accepted input shape and authority, result/failure
shape, resource/state owner, direct dependencies, timeout/cancellation behavior,
trust boundary, and observable duration. Use existing functions/protocols where
they suffice. Separate dependency injection for tests from permission to select
an arbitrary production transport.

Request-scoped information must not be stored in module globals. Immutable
profile/routing metadata can describe policy; only fresh current checks authorize
a request. Parsed file caches must not reuse an allow verdict after source,
registry, permissions, model or deployment state changes.

## Implemented checkout execution contract

One internal immutable execution context carries resolved profile, interaction
type and optional diagnostic base. A strict resolver accepts only known names;
it cannot carry permissions, URLs/executables, isolation mode, security toggles,
model options, source/evidence limits or cache-approval settings. Missing context
maps to the current behavior. Both gateway and MCP child validate external
metadata independently; old tool arguments remain unchanged. The internal
`larpus_execution` metadata never expands tool authority. Explicit profiles
require the sealed deployment; host inference fixtures are outside this contract.

`source_integrity.fingerprint(root)` owns fresh byte acquisition and hashing,
using only the standard library. It has no scanner/MCP initialization dependency.
`execution_preflight.observe(names, command, run)` acquires bounded fresh
observations with an injected runner; it cannot issue an allow verdict. Isolation
owns validation, identity/pin checks and child launch. Missing/malformed current
observations reject. The standard acquisition path remains the default.

`execution_trace.Trace` owns numeric request-local events, cumulative gate time
and approved-release gaps. It invokes the supplied mandatory gate exactly once;
trace/clock failure cannot turn rejection into approval. It stores no prompt,
answer, credentials or private path. Host/child/browser clocks remain separate.
The host attaches the sealed source receipt after fresh preflight, since a
deployment file containing its image identity cannot be baked into that image.

HUD selection is additive: Verified is the default; Ultra Fast selects fresh
batch observations; Diagnostic records timings using the independently selected
Verified or Ultra Fast base. Conversation/analysis/coding are interaction labels,
not permissions or model sampling changes. Existing tabs may omit execution and
retain their conversation. These controls are in checkout and the unactivated
candidate, not the selected production HUD. Ultra Fast remains experimental.

Mandatory boundaries remain outside any optional-stage decision. An optional
evaluator, if a real one is introduced later, may return advisory scores or fail
independently; it cannot approve tools, clear scheduler faults, waive DLP or widen
model input. No runtime critic exists today, so this audit does not add an empty
production evaluator framework to make an independence test look convincing.

Skill capability metadata is currently enforced by code/registry constraints:
prompt-only, local-authored, exact reviewed bytes, persona allowlist and no
executable/tool permissions. Document those facts; do not add permission-bearing
frontmatter to the narrow two-field format just to satisfy a generic metadata
checklist. Future executable skills require a different reviewed contract.

## Independent tests and acceptance limit

Use synthetic dependencies for routing/model/gate boundaries and actual isolated
protocol tests where the boundary matters. Cover valid/invalid inputs, unexpected
results, timeout/EOF/cancellation, optional engine/cache failure, skill discovery
failure, consistent owner persona/skill removal, and required scan/gate failures.
Distinguish consistent optional removal from tampering with an approved catalog.
Assert that failed work neither leaks chunks nor contaminates the next request.

The selected tests above now run in the isolated regression suite, alongside a
seven-mutation comparison of fresh observation validation. Final checkout suite:
457 tests/four skips, 11 UI suites. Live comparison completed 100 attempts/profile,
but failed the five-second target and did not establish quality parity. No
profile is promoted on that evidence. See the
[acceptance report](../EXECUTION_PROFILES_PERFORMANCE_2026_10_20.md).
