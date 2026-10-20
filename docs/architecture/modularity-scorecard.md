# Modularity scorecard - before implementation

Criteria: 0 no meaningful separation/evidence; 1 major coupling; 2 partial
separation with important limits; 3 functional separation with documented
weaknesses; 4 strong separation with repeatable supporting tests; 5 demonstrated
independence, contracts, fault tolerance and reproducible evidence. These are
engineering judgments, not accuracy percentages. No weighted overall rating.

| Dimension | Score | Source/test evidence and strengths | Weakness / next improvement | Confidence |
| --- | ---: | --- | --- | --- |
| Separation of concerns | 3 | `auth.Auth`, `scoring_pipeline.Pipeline`, `local_ollama`, `ModelSwitch` have distinct responsibilities | `gateway.Handler.do_POST` and `inference.chat` aggregate many features; add narrow execution context, not another application pipeline | Medium-high |
| Dependency direction | 2 | Static source map exposes three SCCs; transport/worker/owner processes have boundaries | Hashing imports scanner/MCP orchestration; isolate pure integrity calculation first | High |
| Interface clarity | 3 | Fixed MCP tool descriptors, engine/scorer methods and broker strict schemas | Many result dictionaries and status/exception conventions; document ownership and maintain compatible result shape | Medium-high |
| Independent testability | 3 | 414-test baseline; injected model-switch Backend and synthetic stream/protocol tests | Global persona/catalog and environment/import initialization remain; new profile tests need no live services | Medium |
| Component replaceability | 3 | Actual NumPy/Assembly choices and Engine/RemoteEngine contract, with tests | Ordinary provider adapter is pinned, not arbitrarily swappable; do not weaken transport policy to claim portability | Medium-high |
| Failure containment | 3 | Broker fault-closed cancellation, streaming partial-state exclusion, model restoration, NumPy/BM25 fallbacks | Catalog-wide approval failure and process-global caches have wider scope; optional removal and recovery need targeted tests | Medium |
| Security-boundary independence | 3 | Fixed broker lanes, explicit DLP, auth and isolation; no runtime critic dependency found | No new profile-equivalence matrix yet; lexical defenses are bounded and host fixture path must remain outside secure production profiles | Medium |
| Configuration independence | 2 | Separate persona/model/scorer/teaching configuration | ROOT borrowed from skills, env controls, global registries and broker prompt marker affect unrelated layers; introduce resolved immutable profile only | Medium-high |
| Observability | 3 | `diagnostics.report`, stage timings and background health are explicit/redacted | Missing complete nonoverlapping trace and new mean/std/p99/resource comparison; first frame differs from first text | Medium-high |
| Performance isolation | 2 | Persistent CPU worker, broker queue/budgets, private evidence receipts | Shared GPU cache/background probes, mutable worker state and deadline-sensitive reranking complicate attribution; controlled interleaving and replay needed | Medium |
| Extensibility | 3 | Local JSON personas and registered prompt-only skills avoid per-persona broker branches; read-only extension is additive in checkout | Registration/allowlists/template pins intentionally need resealing; executable/tool-granting skills are unsupported | Medium-high |
| Maintenance complexity | 3 | Standard library/functions, fixed adapters and staged updater; no generic orchestration framework | Existing deferred cycles/large handlers and dual checkout/frozen provenance require care; prefer two small boundaries over broad rewrite | Medium |

Relevant evidence: [inventory](module-inventory.md), [dependency map](dependency-map.md),
[contracts](module-contracts.md), [findings](audit-findings.md), source-map JSON and
`data/modularity-baseline-tests.log`. Existing suites include `test_isolation`,
`test_broker_scheduling`, `test_streaming`, `test_mcp_skills*`, `test_model_switch*`,
`test_retrieval_worker`, `test_assembly_pipeline` and `test_optimized_pipeline`.

Assessment: LARPUS has meaningful component/process boundaries and demonstrated
substitution in retrieval/scoring, but is only partially modular at the request
orchestration/configuration layer. Separate files and selectable flags do not
establish fully independent modules. No dimension receives 5; no after-score is
assigned before implementation/fault/benchmark evidence. Higher scores require
the specific new tests, not merely new interfaces or documentation.

## Checkout implementation evidence

The original table remains the before assessment. Fresh hashing now imports no
scanner/MCP orchestration, and strict immutable profile values and bounded numeric
tracing have independent unit tests. Both observation bases use the same policy
validators; a seven-mutation matrix tests those decisions. Selected streaming,
storage, optional-removal and fallback cases run across profiles.

These support narrower improvements in interfaces, testability and observability;
they do not establish all-component replacement or general live fault containment.
The 300-attempt comparison and 295 blind answer assessments are now available.
The candidate failed latency acceptance and quality parity remains unestablished.
Scores below assess checkout architecture, not production readiness or model
accuracy. The selected release remains unchanged.

| Dimension | Before -> after | Demonstrated change / retained limit | Confidence |
| --- | ---: | --- | --- |
| Separation of concerns | 3 -> 3 | Four narrow runtime seams; large request orchestration remains | Medium-high |
| Dependency direction | 2 -> 3 | Pure hash extraction breaks one SCC; two deferred cycles remain | High |
| Interface clarity | 3 -> 4 | Frozen strict context, canonical wire contract, independently validated metadata; legacy tools unchanged | High |
| Independent testability | 3 -> 4 | Import independence, fake-clock, injected observation runner and per-profile fault tests; globals remain | Medium-high |
| Component replaceability | 3 -> 3 | NumPy/Assembly substitution preserved; ordinary provider remains pinned | Medium-high |
| Failure containment | 3 -> 3 | Cancellation/truncation recovery and optional-removal/fallback tests. The 2026-10-20 checkout scopes a named skill or persona failure to that entry, retries a retrieval open, and retries a failed scorer after 30 seconds. The score stays 3 because a registry-document failure and the broker fence still stop more than one request. | Medium |
| Security-boundary independence | 3 -> 4 | Shared validators and mutation/fault matrix across profiles; not exhaustive hostile testing | Medium-high |
| Configuration independence | 2 -> 3 | Request-local immutable selection; deployment environment/global registries still authoritative | Medium-high |
| Observability | 3 -> 4 | Numeric bounded traces, receipt-pinned benchmark, failures and independent quality records; no physical paint/CPU thermal proof | Medium-high |
| Performance isolation | 2 -> 3 | Matched/interleaved fixed workload, telemetry and pacing analysis; stochastic/shared-cache effects and five failures remain | Medium |
| Extensibility | 3 -> 3 | Additive controls and metadata; no new executable skill/provider authority | Medium-high |
| Maintenance complexity | 3 -> 3 | Small standard-library seams and complexity gate; six owned modules added, broad coupling deferred | Medium |

Confidence is high for pure import direction and interface assertions, medium-high
for test/trace evidence, and medium for failure/performance isolation. There is
no weighted aggregate, and no dimension receives 5. Evidence: 457 tests/four skips,
11 UI suites, prepared scanner receipts and the
[live acceptance report](../EXECUTION_PROFILES_PERFORMANCE_2026_10_20.md).
