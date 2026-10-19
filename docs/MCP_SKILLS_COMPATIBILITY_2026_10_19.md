# MCP Skills: architecture and compatibility review - 2026-10-19

Status: Stage 1 only. The extension is not implemented or advertised. No protocol compliance, Linux interoperability, release acceptance or performance parity is claimed yet.

## Repository and runtime are distinct

At inspection, local and origin main matched at `6138538`. The completed, non-promoted collector experiment was then published as `6ad9290` with its default integration disabled. No unrelated changes were included. The selected frozen application remains `7df2e957751642d6ace4630fa047fe94`, stopped; previous `f08b98ea2f34407cb77dc79aa7d7866a` remains available. The prepared collector experiment `ddf716bcc1f04df891de7545f2052b64` failed pacing acceptance and must not be folded into this integration.

Uncommitted earlier Assembly/UI/native-scoring/release/security-scan changes and profiling artifacts remain in the checkout. There is also an approved but unimplemented quality-routing design. Neither branch name nor git cleanliness proves deployment equivalence. Future candidates must be constructed from the selected frozen release and an explicit reviewed integration delta; preserve its consistent corpus. Do not bundle unrelated checkout or newer GitHub changes implicitly.

Reviewed local paths: runtime/mcp_server.py, mcp_client.py, skills.py, agents.py, inference.py, isolation.py, security_scan.py, health.py; skills/registry.json; config/mcp-approved.json; requirements.txt; SKILLS.md, MCP.md, ARCHITECTURE.md, October 17 baseline, October 19 latency/consistency reports; releases.py, test-local.py, ci.py and performance_suite.py.

## Actual trust boundaries

| Boundary | Current enforcement | Integration requirement |
|---|---|---|
| LAN HUD to Windows gateway | HTTPS password, subnet/origin checks, bounded messages and admission | No HUD/auth/binding changes |
| Gateway to MCP child | Fixed executor and environment allowlist; fresh source, distro, rootless, image, OCI, mount and namespace checks | Keep these checks and the three-tool contract |
| MCP child in agent container | Read-only source; separate network=none namespace; local filtering and persona selection | Add read-only protocol methods, never execution tools |
| Agent to broker | Private read-only chat socket mount; broker validates system-template hashes, options, budgets and scheduling | No direct model route or new privileges |
| Broker to model | Offline pod loopback, one GPU generation slot; full GPU placement checked before output | Weights/options/context unchanged |
| Registry to selected prompt | Owner registry, local-authored origin, persona allowlist, raw SHA256, size, path/file and text-filter checks | Resource discovery never authorizes activation |
| Generated output to HUD | Whole-prefix DLP and approved progress chunks | No bypass or chunk-policy tuning |

Normal call path: gateway validates messages; mcp_client constructs child parameters after isolation preflight; SDK connects over fixed stdio; chat_local calls inference.chat; messages_for appends selected_prompt; knowledge augmentation supplies untrusted evidence; broker performs local generation; DLP approves text before progress/final release. load_personas validates skills at import; selected_prompt calls load_skills again. summaries and health also call the full loader. A third-party local MCP client still reaches server-side filtering; discovery does not confer a shell or a persona authorization.

## Protocol and installed SDK evidence

The authoritative [stable Skills specification](https://github.com/modelcontextprotocol/ext-skills/blob/main/specification/stable/skills.mdx) was inspected alongside the [base protocol](https://modelcontextprotocol.io/specification/2026-07-28/basic/index). A pinned copy is recorded locally at https://raw.githubusercontent.com/modelcontextprotocol/ext-skills/4ad2d3a86410ca2e9b494f8a22dac995e7d7b8b4/specification/stable/skills.mdx (SHA256 6e33a33762783a02dc4c13c889dda5b8d7c525649012cf77da12d80c04ce6851). The protocol requires the Skills extension and Resources advertisement, skills/list and skills/get, ordinary resources/read, exact frontmatter plus static URI/digest/size manifests, atomic paginated entries, required result/cache fields and per-request metadata. Unknown skills/resources use -32602; internal faults use -32603. Skill identity is server identity plus URI; TTL is not integrity. Directory reading is optional and excluded. These are protocol facts, not claims that LARPUS implements them.

Installed Windows distributions are mcp==2.3.0 and mcp-types==2.3.0. Source/type inspection found:

| SDK facility | Evidence | Compatibility implication |
|---|---|---|
| Revision registry | Includes 2026-07-28 and older handshake revisions | No major protocol migration is indicated |
| MCPServer(extensions=...) | Public Extension and MethodBinding hooks, with protocol_versions restriction | Add Skills methods through supported APIs |
| Resource handlers | resource decorator, resource manager and standard read path | Serve registered text without a file/shell tool |
| Result/params types | RequestParams, PaginatedRequestParams, CacheableResult, PaginatedResult | Use typed shapes; verify serialized wire fields explicitly |
| Client | modern discovery, forced legacy mode, read_resource, custom typed session requests | Genuine interoperability tests are feasible without installing another SDK |

A real in-memory SDK client connected to the existing server: auto mode negotiated 2026-07-28; forced legacy negotiated 2025-11-25. Both exposed exactly chat_local, local_status and list_personas; modern tool descriptors matched config/mcp-approved.json. Existing SDK capability output already includes Resources even though LARPUS publishes no skills. It does not include the Skills extension. No inference or live containers were used. This is baseline discovery evidence only, not a new-extension conformance test or a Linux/stdio proof.

CacheableResult has SDK defaults ttlMs=0 and cacheScope=private; RequestParams.meta is optional at the Python model level. Those conveniences are not proof that raw requests are compliant or that serialization emits every required field. Real wire tests must assert metadata rejection, modern resultType, explicit cache fields, pagination and error codes, plus legacy behavior. Do not substitute successful generic JSON-RPC for conformance.

## Frontmatter and loading observations

All 69 registered files currently contain only two unquoted plain-scalar frontmatter keys: name and description. No complex YAML was found in that inventory. Registry name is a display label; it must not replace the slug-valued frontmatter name. Frontmatter description must come from the file, not be fabricated from UI registry metadata.

No yaml, ruamel, strictyaml or frontmatter module is installed in this Windows environment. Do not add a shared dependency silently. The proposed initial authoring profile parses the existing exact two-scalar form, rejects duplicate/unsupported YAML forms and never edits raw skill bytes. Future broader YAML support would require separately reviewed parsing/dependency work; it must not be approximated by flattening fields. This is a deliberate local authoring restriction, not a claim of a general YAML parser. Permission-like frontmatter must never grant tools; unsupported forms are rejected, not executed.

Full load_skills on the Windows checkout: 10 measurements after one excluded warm-up, median **180.9 ms**, range **172.7-189.9 ms**. Each run included existing file/digest/filter checks. This is not Linux request-time cost and does not establish an end-to-end gain. No catalog optimization has been implemented. Preserve full verification until a narrowly scoped alternative proves equivalent under explicit trust assumptions.

## Compatibility decision and alternatives

Recommend a minimal opt-in server extension on the existing SDK, preserving all three tools and the current chat client/selected_prompt path. API-level feasibility is verified; extension interoperability remains to be implemented and tested. No SDK upgrade or new listener appears necessary.

Alternative: an adjacent server/adapter duplicates lifecycle, approval and identity handling without a demonstrated benefit; reject initially. Alternative: dependency upgrade/general agent framework expands maintenance and trusted code without a proven blocker; reject initially. If supported SDK hooks fail the real wire tests, stop with an evidenced compatibility blocker rather than patch SDK internals or alter protocol revisions silently.

The proposed design is docs/superpowers/specs/2026-10-19-mcp-skills-design.md. Stage 2 implementation starts only after its review; the written implementation plan follows that approval. No runtime source was changed for Skills during Stage 1.

## Required future evidence and rollback

Protocol: real stdio modern discovery/metadata, full list pagination/get/read, exact SHA256 and byte sizes, frontmatter equality, cache/result fields, malformed metadata/cursors and modern/legacy errors. Negative matrix: tamper, mismatch/truncation/oversize/UTF-8/YAML/duplicates, unknown and encoded traversal URIs, symlinks/unexpected files, forged origin/cross-server collision, privilege-request fields, scanner failure and persona denial. For each activation-path failure, spy at the model boundary and prove no unverified prompt reaches inference.

Regression: all three unchanged descriptors; inference/DLP/streaming/grounding; source/container integrity; no extra listeners, mounts or execution permissions; Python/UI/isolation/static scans. These tests are planned, not passed in Stage 1.

Performance: compare A frozen baseline, B protocol-only and C only an independently validated optimization. Same selected skills/model/corpus/options, alternating order, excluded conditioning, separate cold observations, per-stage skill/isolation/connect/retrieval/model times, first/final latency and delivery gaps, failures/evidence and manual grounding rubric. Run the existing eight-case suite as well as focused skills tests. Treat >5 percent median first-text regression as a review blocker. If no safe useful optimization exists, retain B and report C as not adopted; do not invent a gain.

Prepare a separate frozen candidate after implementation and tests. Do not alter scan acceptance merely to pass. Dependency/model/OS maintenance requires separate authorization. Activation needs owner authorization and prepared validation, uses normal drain/readiness/rollback and may require LAN re-login; never call rebinding zero downtime. Keep the previous frozen release and old MCP client path. A normal rollback selects the previous release; no knowledge, owner-data or model migration should need undoing.

## Receipts and limits

Ignored owner evidence: data/mcp-skills-compatibility-20261019/{existing-sdk-and-loader.json,legacy-discovery.json,spec-source.json,skills-stable.mdx}. No raw downloaded instructions were installed or executed. No dependencies, station services or GPU workloads were started; LARPUS and its WSL remain stopped. The source spec is downloaded reference data, not workspace instructions. Linux SDK parity, extension wire compliance, security-negative tests, A/B/C timing and a new release remain unverified.


## Approved implementation follow-up

The owner approved the architecture and native implementation plan. The isolated branch
now adds the verified resource layer, SDK Extension methods and resource callback without
new tools or a dependency update. Windows stdio interoperability and security negatives,
UI contracts and prompt hash checks have passed; see the current
[acceptance matrix](MCP_SKILLS_ACCEPTANCE_2026_10_19.md). Stage 1's stopped-service
and unverified statements above describe that earlier stage, not the later authorized test window.

Candidate `651658465bf54e5e9298c7d34a7082f6` failed preparation because a benchmark-only
metrics helper was absent from the older frozen source. Its files/receipt were retained.
The next snapshot adds the unchanged helper and eight-case catalog required by the approved
harness. Neither candidate has been activated. Live performance, Linux preparation and
final stopped-state evidence are tracked separately; implementation is not a speedup claim.
