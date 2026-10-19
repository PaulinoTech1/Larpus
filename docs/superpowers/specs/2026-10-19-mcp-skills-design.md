# MCP Skills extension design

Date: 2026-10-19. Status: proposed architecture, awaiting owner review. This is a design, not an implementation or release approval. Evidence and limitations: [compatibility review](../../MCP_SKILLS_COMPATIBILITY_2026_10_19.md).

## Intended outcome and scope

Expose the 69 currently registered, locally authored prompt skills through io.modelcontextprotocol/skills on the existing stdio MCP server. Preserve the three existing tools and owner-selected skill activation, prompt bytes, model/retrieval/broker/voice/DLP/HUD behavior. Improve interoperability without adding execution capability, automatic skill selection, remote ingestion, dependencies or per-chat discovery round trips.

The pinned SDK has the relevant public extension, resource and protocol-version APIs. Existing-client discovery succeeded at 2026-07-28 and forced legacy 2025-11-25, but new extension conformance and Linux parity are not yet established. Use SDK 2.3.0 unchanged initially; do not patch its private internals. If public hooks cannot satisfy the wire tests, stop and document the concrete incompatibility.

## Chosen components

1. A small deterministic registry/resource layer, sharing current authorization and raw-byte verification. It accepts only registered local-authored IDs and the existing single SKILL.md layout, at most 128 skills and 16000 bytes each. Reject symlinks, non-regular/extra files, traversal, unknown entries, duplicates, malformed UTF-8/frontmatter and digest/size inconsistency. Bound reads before consuming oversized data. Keep validation before returning any bytes.
2. A read-only SDK Extension contributes skills/list and skills/get using public MethodBinding, version-gated to 2026-07-28. Register a standard resource handler for canonical skill URIs. No additional tool decorator, process, listener, network destination, mount, directory-read feature or executable attachment.
3. Protocol-only integration into the existing MCPServer. Keep chat_local, local_status and list_personas descriptors byte-equivalent to the approved snapshot. The existing gateway client continues calling the same tools. It neither fetches a skill over MCP on every chat nor promotes externally supplied content.
4. Genuine modern/legacy test clients and owner-only benchmark harnesses. These are test code, not a general-purpose agent framework or remote skill host.

Do not introduce a second running MCP server, generic execution engine or persistent permission cache.

## Wire profile

Follow the pinned stable specification and base schema cited in the compatibility review. Advertise the extension with no optional settings and Resources support. Never advertise directoryRead=true. Tests must observe actual wire behavior, including version-gating and malformed/missing metadata; Python model acceptance alone is insufficient.

Use exactly `skill://<registered-id>/SKILL.md`. Resolve it by exact canonical registry lookup, never DNS, percent-decoded path joining or caller-controlled filenames. Reject other schemes, query/fragment/encoded or noncanonical variants. Unknown skill/resource is -32602 for modern requests; internal verification failures map to a generic -32603 without workstation paths. Test legacy base-resource errors according to the selected revision rather than hard-coding modern behavior for old clients.

List/get entries expose frontmatter parsed from the underlying verified bytes plus a complete one-file manifest (canonical URI, sha256-prefixed lowercase digest, raw byte size). No file body in listing responses. A list page contains at most 16 whole entries, sorted by registered ID. Use a bounded opaque cursor bound to catalog content and position; invalid/stale cursors reject, and an entry is never split. The cursor is not an authorization token.

Explicitly serialize modern resultType=complete, ttlMs=0 and cacheScope=private where required, including resource reads. Zero TTL avoids introducing a freshness or permission cache. Discovery may transfer metadata/manifests; SKILL.md content transfers only when requested. No client-side persisted content cache in the initial implementation.

## Frontmatter choice

All current authored files use exactly name and description as unquoted plain strings. Initially support that existing, explicit local authoring grammar and validate every file fits it; preserve both values exactly. Do not use friendly registry labels as frontmatter. Reject duplicate keys, YAML tags/aliases, quoted/structured/multiline/ambiguous scalar forms and unsupported additional fields, rather than inventing their parsed meaning or dropping them silently. All served files remain valid skills with unchanged raw bytes.

This is not a general YAML implementation. A future richer authoring format requires a reviewed parser/dependency decision. Unsupported privilege fields are rejected; permitted frontmatter can never widen permissions. Tests attempt allowed-tools, shell hooks and forged grants and prove none reach an executor or bypass persona authorization. No shared dependency install is part of this design.

## Authorization and origin

Registry authorization remains separate from protocol discovery. Resource get/read does not activate anything or inject a system instruction. Only the current selected_prompt/persona allowlist path can activate a local skill, with the exact existing prefix and raw instruction text. A missing or failed skill never substitutes another.

Keep host-assigned server identity together with URI in test-client identities and any future cache/approval representation. Self-declared server names and matching skill names/URIs from another server do not establish local provenance. LARPUS adds no foreign-server ingestion path; collision tests must show foreign resource text cannot be passed as an approved local skill. A trusted expected digest establishes byte consistency, not authorship, benign intent or guaranteed model obedience.

## Performance and loading experiment

Configuration A: exact selected frozen baseline and current loader. B: read-only protocol surface, unchanged normal-chat loader and instruction bytes. C: a separate, explicitly validated optimization only if profiling demonstrates redundant work within a safely bounded trust scope.

Preserve full-catalog verification in B. Do not reuse startup or periodically checked mutable catalogs as per-request permission approval. An optimization may share already verified bytes only inside one operation/request with an explicit verified object; never deduplicate checks across gateway/agent trust boundaries. Any proposal for protected release-bound snapshots needs proof of immutability and invalidation on release/registry/persona changes. No unprotected cross-request cache. If no safe meaningful improvement exists, retain B and mark C not adopted.

Measure complete catalog/selected-skill handling separately in Windows and isolated Linux. The initial Windows full-catalog median was 180.9 ms; that is not an end-to-end optimization opportunity estimate. Run A/B/C with identical selected skills and the same model/corpus/options, excluded warmups and balanced alternating order. Include the existing eight-case suite, focused skill cases, first/final latency, p90/p95 when sample size supports them, per-stage timings, cold observations, approved chunk gaps, failures and retrieved evidence. Review grounding with the existing explicit rubric. More than roughly 5 percent median first-text regression blocks performance acceptance for review. Do not claim gain from reduced verification, shorter outputs, different workloads or additional inference calls.

## Verification matrix and release gate

- Genuine protocol clients: modern extension/resources discovery, metadata, typed list/get/read, all pages and invalid cursors, digest/size/frontmatter equality, exact cache/result fields, unknown URI errors, missing/invalid metadata, unsupported revision behavior and old three-tool path.
- Security negatives: modified bytes/registry/manifest, truncation, oversize, invalid UTF-8/frontmatter/duplicates, unknown and encoded traversal URIs, symlink/nonregular/extra files, origin/cross-server collision, privilege fields, scanner failure and incorrect persona pairing. Assert rejected activation attempts make zero calls to the model and reveal no private paths.
- Regression: approved tools unchanged, output DLP and streaming intact, evidence/knowledge functional, source/image/OCI/network checks still fresh, no listener/mount/tool/privilege additions; local Python, UI, companion, isolation and static gates.
- Performance and behavior acceptance: preserve selected instruction bytes and security decisions; controlled timing and cadence report, raw receipts, manual grounding review and explicit unresolved limits. Do not relabel new scan findings accepted merely to make a gate green.

Do not count planned tests as passed. A successful generic JSON-RPC call is not a conformance report. The existing SDK resource capability advertisement is not proof that Skills is implemented.

## Staging, owner boundaries and rollback

Keep all owned artifacts and temporaries on E:. Keep the selected release, corpus, model selection and owner data intact. Current station is stopped; no services are started during design review. Do not bundle the non-promoted latency collector or unrelated worktree changes into Skills.

After design approval, write and review the implementation plan before code. Implement and test the minimum surface first, then any independent loading experiment. Build from the selected frozen base with the explicit approved delta; use releases.py stage/prepare and retain separate scan/health receipts. Keep a written inventory of changed files and any warnings. No dependency/model/OS maintenance as a side effect.

Prepare a separately identified candidate only after the relevant test gates. Live GPU benchmarking and activation must remain within owner-authorized scope; report any remaining live steps. Activation is not approved merely by reviewing this architecture. When authorized, validate prepared state and activate through the owner CLI, preserving drain/readiness/automatic restoration. Rebinding is not zero downtime; LAN sessions need login again. Keep the old frozen release and MCP client path for rollback; no data migration is required. Return a temporary test station to its prior stopped state.

## Completion definition

Deliver the narrowly scoped implementation diff, real-client interoperability report, security-negative matrix, regression/isolation/static evidence, A/B/C performance receipts (or justified non-adoption), updated Skills/MCP documentation and a concrete prepared release/rollback procedure. Final claims distinguish observed facts, inferences and unverified platforms/live behavior. This proposed design does not claim those deliverables have already been achieved.
