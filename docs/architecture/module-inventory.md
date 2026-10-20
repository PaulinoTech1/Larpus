# Module inventory - 2026-10-19

Scope: owned checkout at `64e49c7`, with the selected frozen release
`7df2e957751642d6ace4630fa047fe94` distinguished below. Phase 1 inspection only;
no runtime behavior changed. Evidence is source inspection plus the isolated
baseline: 414 tests, four skips, 152.897 seconds. A passing suite does not prove
semantic prompt-injection resistance or unrestricted backend replaceability.

## Runtime components and contracts

| Component / source functions | Purpose and inputs | Output / dependencies | Failure and replaceability |
| --- | --- | --- | --- |
| [Gateway](../../runtime/gateway.py): `Handler.trusted`, `do_POST`, `authorized` | Fixed HTTP routes, bounded JSON, persona/history and session | HTTP/NDJSON; Auth, admission, MCP, model/voice hooks | Rejects malformed/unauthenticated requests; transport and many feature branches share one handler, so partially separable |
| [Authentication](../../runtime/auth.py): `Auth.login`, `session`, `allowed` | Owner password record, cookie and bounded rate windows | Status/token or authorization result; hashlib/hmac, process-local session state | Invalid credentials/configuration reject; network adapter is separate, but session restart requires fresh login |
| [Host admission](../../runtime/inference_admission.py): `Admission.interactive`, `background` | Owner-host interactive/background lock directory and deadlines | Cooperative lock ticket; OS file locks | Busy/timeouts hold; does not replace the broker's untrusted-process enforcement |
| [MCP client](../../runtime/mcp_client.py): `child_parameters`, `call_async`, `stream_chat` | Three allowlisted operations and bounded request/progress | Fixed child SDK call, structured result; isolation, agents.ROOT, diagnostics | Transport failure rejects without direct-model fallback; new async context/child per call |
| [Isolation](../../runtime/isolation.py): `mode`, `preflight`, `child_args`, `validate_container` | Pinned deployment, source fingerprint, WSL/Podman/OCI state | Validated profile/fixed argv; skills.ROOT, deferred security_scan | Any missing/drifted required state rejects; observation transport and validation are currently intertwined |
| [MCP server](../../runtime/mcp_server.py): `chat_local`, `allowed` | Fixed tool arguments and streaming metadata | Calls inference through a worker thread; SDK, progress callback | Process-local rate limit and cancellation event; not a generic shell/tool orchestrator |
| [Inference](../../runtime/inference.py): `chat`, `stream_reply`, `release` closure | Valid persona, alternating messages, optional skill and approved chunk callback | Filtered result/content/sources/context/timing; agents, knowledge, DLP, local adapter | Evidence, GPU, model, broker and gate failures hold/reject; prompt/retrieval/generation/release sequencing remains concentrated here |
| [Personas](../../runtime/agents.py): `load_personas`, `messages_for` | Local JSON, history, optional registered skill | One system prompt plus filtered history; skills, text_filter | Invalid persona/catalog can prevent whole registry load; dictionary routing, no model deliberation |
| [Skill registry](../../runtime/skills.py): `load_skills`, `selected_prompt`, `summaries` | Exact local registry, regular files, hashes and persona allowlist | Verified prompt-only text/metadata; text_filter | Invalid registered entry fails complete catalog; selective prompt inclusion, not independent per-file approval |
| [Skills resources](../../runtime/skill_resources.py): `verified_catalog`, `resolve_skill`; [extension](../../runtime/mcp_skills.py): `_list`, `_get`, `register_skill_resource` | Exact URI, bounded digest-bound cursor, fresh registry | Read-only metadata/body; SDK modern extension and standard resources | Sanitized protocol errors; reads grant no activation/execution authority; full verification each operation |
| [Knowledge](../../runtime/knowledge.py): `database`, `retrieve`, `_retrieve`, `augment` | Question/persona, bounded evidence budget, approved index | Original passages plus provenance, optional derived notes; SQLite, retrieval, reference_review | Approved index/required scanner failure rejects; no matching evidence gives explicit no-evidence guidance; repeated persona validation couples it to the full skill registry |
| [Retrieval client/models](../../runtime/retrieval.py): `Engine`, `RemoteEngine`, `engine`; [worker](../../runtime/retrieval_worker.py): `call`, `handle`, `serve` | Validated index/model files, bounded neighbors/rerank IPC | Row IDs/scores or unavailable engine; ONNX/tokenizer/NumPy, Unix socket | Optional CPU enhancement falls back to BM25; initialization failure is cached until reset/restart; concrete common interface supports local/remote engines |
| [Scoring](../../runtime/scoring_pipeline.py): `Pipeline.score`, `select`; [optimized](../../runtime/optimized_scoring.py): `OptimizedScorer` | Matrix/query/cutoff and configured scorer | Scores/status; native and optimized kernels, NumPy | Unavailable/failed/ambiguous assembly uses NumPy; a demonstrated implementation substitution boundary, not an authorization boundary |
| [Trust/provenance](../../runtime/text_filter.py): `inspect_message`, `screen_optional_evidence`; [reference review](../../runtime/reference_review.py): `inspect_reference`; [provenance](../../runtime/provenance.py): `read`, `evidence` | Untrusted text, reviewed patterns, index-linked metadata | Allow/hold, excluded optional notes, attribution/freshness signals | Incomplete/unavailable required scan fails closed; lexical defenses and reviewed metadata do not establish truth or semantic injection immunity |
| [DLP](../../runtime/dlp.py): `stream_pending`, `gate`, `inspect_output` | Entire generated prefix/system prompt, policy and private quarantine | Approved content or held incident; disk, ACL/mode protection and fsync | Policy/storage/inspection failures hold; cumulative-prefix and encoded-fragment checks prevent simply substituting an isolated-token filter |
| [Model transport](../../runtime/local_ollama.py): `local_response`, `chat_stream`, `ollama` | Fixed routes/payload, chat/notes capability from process environment | Bounded HTTP/NDJSON through fixed Unix broker socket | Invalid route/socket/framing/timeout rejects; host mode exists for explicit fixtures/owner execution, never an automatic isolated fallback |
| [Broker](../../runtime/inference_broker.py): `validate_chat`, `validate_lane`, `selected_body`, `generation_body`; [scheduler](../../runtime/broker_scheduler.py): `Scheduler.slot`, `probe`, `Job.cancel` | Socket identity/lane, approved templates, model/context/options, bounded workload | Serialized model stream or refusal; HTTP model runner, model selection | Budgets/preemption/deadline/fence state enforced; failed cancellation fences fault closed. Broker also injects anti-repetition options based on a prompt marker |
| [Model lifecycle](../../runtime/model_switch.py): `ModelSwitch.request`, `run`, `restore`; [owner backend](../../runtime/model_backend.py): `Backend` | Owner-approved model ID and maintenance state | Observable switch/restore stages; fixed WSL/model operations, releases lock | Refuse busy/unprepared selection; restore previous model or hold failed. Backend is injected in tests, but ordinary inference does not accept an arbitrary provider |
| [Context/session](../../runtime/context.py): `validate_record`, `compression_messages`, `summary_result`; [browser](../../web/conversation.js): `LarpusConversation` | Full browser transcript, untrusted lossy handoff, context pressure | Validated compact record plus recent turns; model compression via gateway | Atomic browser commit retains prior record on failed batch; compression can add model calls, unlike ordinary chat |
| [Teaching/memory](../../runtime/teaching.py): `unpack`; [HUD](../../web/app.js): `chat.onsubmit` | Owner style choices/memory merged into user question | User-level guidance, then normal server screening | Does not grant permissions; client-side optional features remain user choices, not execution profiles |
| [Voice](../../runtime/voice.py): `preflight`, `call`; [HUD](../../web/voice.js) | Explicit speech/recording requests and pinned CPU worker | Offline audio/transcript; isolated voice process | Text can remain displayed if speech fails; replay text is separately screened by gateway. Voice is not a mandatory model-text stage |
| [Observability](../../runtime/diagnostics.py): `report`, `describe`; [health](../../runtime/health.py): `check`, `watch` | Exceptions or scheduled fixed functional/security checks | Redacted diagnostic ID/stderr and health receipt | Diagnostic sink failure cannot turn failure into success; health cycles are background work, not per-answer model critiques |
| [Release/owner tooling](../../scripts/releases.py): `stage`, `prepare`, `validate`, `activate`, `start` | Frozen payload/pins, prepared candidate and explicit owner operations | Staged release, readiness/drain/restore; separate owner process | Failed preparation cannot activate; failed activation restores previous release. Not a model capability |
| [Raw speed experiment](../../scripts/benchmark_ultra_fast.py): `run`; [station](../../scripts/ultra_fast_station.py): `Station` | Owner CLI, stopped station and fixed prompts | Private unscreened model receipts | Explicit application-check bypass outside production; must never be selected by a chat execution profile |

## Performance ownership

Historical selected-release HTTP receipt `f7ebb4535ecc41f387fc2cb84555f4a5`
measured median first approved text 7.210 s, complete reply 9.066 s, preflight
1.954 s, MCP setup 1.204 s and retrieval 2.066 s. These are descriptive,
overlapping stage measurements; not per-module exclusive costs. Source inventory
alone does not measure CPU/GPU time. See [existing report](../MCP_SKILLS_PERFORMANCE_2026_10_19.md).

New stage distributions and the secure profile comparison are documented in the
[2026-10-20 report](../EXECUTION_PROFILES_PERFORMANCE_2026_10_20.md). Overlapping
stage durations still do not establish exclusive component costs. CPU thermal
correlation remains unavailable. The owner raw benchmark's 1.256/1.807 s
first-text medians use different timing/security contracts and cannot be used
as a production baseline; see [benchmark scope](../ULTRA_FAST_BENCHMARK.md).

## Checkout versus selected release

The checkout includes read-only MCP Skills and owner startup follow-ups that
were not activated. `data/modularity-audit/source-map.json` records exact file
hashes and byte differences, including new `mcp_skills.py`/`skill_resources.py`.
Byte difference alone is not a behavioral change: `inference_broker.py` compares
AST-equivalent. The audit must not describe all checkout capabilities as deployed.

Confidence: high for the listed source responsibilities and absence of a
configured runtime critic; moderate for end-to-end replaceability, which still
has bounded targeted fault evidence but lacks general replacement proof. No
independent full security audit is claimed. The six new owned Python modules are
`source_integrity`, `execution_profiles`, `execution_preflight`, `execution_trace`,
`benchmark_execution_profiles` and `execution_telemetry` (104 owned modules total).
