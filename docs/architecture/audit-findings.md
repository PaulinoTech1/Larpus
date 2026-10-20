# Prioritized architectural findings - phases 1 and 2

Baseline: `64e49c7`, 414 tests passed with four skips (isolated test run;
`data/modularity-baseline-tests.log`). The selected gateway/WSL remained stopped.
The initial table is a historical baseline; final status is in Resolved and deferred audit work below.
Priorities below describe engineering work, not validated vulnerability severity.
No exploitable vulnerability is asserted solely from a dependency diagram.

| ID / priority | Verified evidence | Why it matters / recommendation | Confidence |
| --- | --- | --- | --- |
| M01 / high functional gap | No execution-profile resolver in `gateway.do_POST`, `mcp_server.chat_local`, `inference.chat`; only teaching/model/scorer choices | Add a strict request-scoped profile separate from interaction, with a compatibility default and shared mandatory core. Do not equate conversation with slow mode | High |
| M02 / medium | `isolation.preflight → security_scan.fingerprint → mcp_client.child_parameters → isolation.child_args` | Pure source hashing is coupled to SDK/discovery orchestration. Extract a dependency-light fresh hash function, keep compatibility wrapper and exact scope semantics; prove no SDK/process initialization is needed to hash | High for coupling; saving unknown |
| M03 / medium | `knowledge._retrieve` calls `agents.load_personas`, which verifies all skills; gateway and child also construct/filter messages | Some repetition is intentional cross-boundary enforcement; inside-layer registry coupling is a candidate to profile. Do not delete gateway/child validation or weaken complete-catalog approval to gain speed | High for calls; exclusive cost unknown |
| M04 / medium | `inference_broker.generation_body` inspects `CONVERSATION PROGRESS:` and adds repeat options | Prompt content influences backend generation behavior. Ordinary persona additions may work without broker edits, but changed template conventions can alter sampling. Document as protected policy coupling; moving it needs template/options compatibility tests, not an unrelated cleanup | High |
| M05 / medium | `mcp_server.CALLS/WINDOW_START` are child-process state; `mcp_client.call_async` creates a fresh client each call | Persistent reuse would change limiter lifetime, cancellation/progress state and source freshness. Do not adopt the older connection-reuse idea without its own supported-SDK lifecycle design and tests | High |
| M06 / medium requirement gap | `isolation.mode` and `local_ollama.local_response` support explicit owner/fixture host mode; production uses sealed deployment | A new secure profile must not select host/direct transport or claim identical isolation there. Preserve intentional owner tests separately; test all production profiles against fixed sealed deployment policy. Trusted owner maintenance remains outside model authority | High |
| M07 / medium | Existing collector experiment's pacing confirmation failed despite lower first-text latency (`RESPONSE_CONSISTENCY_2026_10_19.md`) | Candidate is not promotion-ready. Reuse only its bounded fresh observations with unchanged validators; distinguish model frame, gate and release gaps using identical-output replay and live pairs | High for recorded rejection; cause unresolved |
| M08 / medium validation gap | `skills.load_skills` validates full registered catalog; missing/corrupted file prevents registry load | Catalog-wide fail-closed behavior is intentional for tampering, but independent optional removal needs a consistent reviewed registry/persona update and dedicated test. Do not silently ignore unknown/missing hashes | High |
| M09 / low | `knowledge/retrieval/retrieval_worker` and `model_backend/releases` have deferred import cycles | Separate protocol/owner lifecycle only when a measured or independent-test benefit exists. No observed deadlock or need for a broad rewrite | High for static cycles |
| M10 / medium evidence gap | Current performance summaries mostly median/p90; no new secure profile timings, task-quality equivalence or live hardware correlation | Add mean/std/min/max/p95/p99 with failures and precise first-visible definitions; at least 100 measured requests/configuration, paired workload and scoped telemetry. Report unknowns explicitly | High |
| M11 / low naming risk | Owner `benchmark_ultra_fast` intentionally skips application gates; proposed production profile must preserve them | Keep benchmark CLI outside profile resolver, label the UI profile secure and reject raw/bypass flags. No normal request may reach the owner Backend direct client | High |

## Strengths to preserve

- Actual scorer substitution/fallback exists (`scoring_pipeline.Pipeline`) and
  local/remote retrieval share a concrete engine contract.
- `ModelSwitch` injects owner backend/lifecycle seams and models restoration;
  core chat cannot obtain those powers from persona/skill instructions.
- Fixed tool descriptors/routes, exact system-template policy and broker socket
  lanes provide enforceable authority boundaries distinct from prompt guidance.
- Filtering, quarantine, protocol, partial-stream, model-switch, scheduler and
  Skills tests already exercise meaningful failures; keep rather than replace them.

## No claimed optional-evaluator speedup

Ordinary `inference.chat` has no second-model critic or multi-persona deliberation.
There is therefore nothing of that kind to switch off. Metadata status calls,
required scheduler fence, retrieval reranking and explicit compression requests
are different operations with different contracts. An Ultra Fast label alone
does not prove less runtime work or genuine modularity.

## Raw benchmark is not the secure comparison

The direct owner benchmark skips `inference_broker.generation_body` as well as
screening and preparation timing. Consequently it also does not traverse the
broker's anti-repetition-option injection. This reinforces the already stated
absence of a quality-equivalence claim; its timing cannot isolate mandatory
security cost or validate a production profile. Use matched secure execution
with the same broker/model/options for the new comparison.

## Scope limits

No new security findings were suppressed, dependency/clock/power settings changed,
or frozen payloads modified. Source-based failure contracts are not proof of all
hostile-input outcomes. Selected cross-profile faults, sealed preparation,
resource boundary telemetry and the 300-attempt benchmark have now run. Real
LAN/HUD acceptance, exhaustive hostile containment and quality parity remain
unestablished. See [final evidence](engineering-report.md) and
[measurements](../EXECUTION_PROFILES_PERFORMANCE_2026_10_20.md).
The source audit excludes downloaded repositories as executable instructions.


## Resolved and deferred audit work

Pure integrity hashing removes the scanner/MCP import cycle. Strict immutable
request metadata and independent observation/trace seams are implemented and
tested. Source-pinning, exact sample identity and probe scan-coverage review
findings were corrected and independently checked. Two other deferred cycles,
large orchestration handlers and catalog-wide failure scope remain.

Minor benchmark receipt base/interaction verification is deferred; source/model/
profile are checked with strict fixed request generation. Failed requests retain
generic classification rather than an underlying diagnostic. The experiment
failed latency acceptance and did not establish quality parity. These findings
are retained, without weakening gates or resampling until passing.
