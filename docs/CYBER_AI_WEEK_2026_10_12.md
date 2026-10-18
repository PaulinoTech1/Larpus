# IT / Cyber coach: weekly AI sources and model labels

Review window: Monday 12 October through Friday 16 October 2026, America/New_York. Publication dates are distinct from retrieval dates and incident/event dates.

Eight sources add 66 screened passages for the IT / Cyber coach. Existing approved passages and embeddings are preserved. New vectors use the same checksum-pinned CPU embedder; no model or Python dependency was replaced.

| Published | Source | Evidence scope |
|---|---|---|
| 2026-10-15 | [Snyk launches Evo Agentic AppSec](https://snyk.io/news/snyk-launches-evo-agentic-appsec/) | vendor announcement |
| 2026-10-15 | [Understand threat reports with Prime Architect](https://socprime.com/blog/understand-any-threat-report-in-minutes-ai-summaries-and-attack-flow-in-prime-architect/) | vendor workflow |
| 2026-10-12 | [Shaping global governance of AI agents](https://www.brookings.edu/articles/shaping-global-governance-of-ai-agents/) | author policy commentary |
| 2026-10-13 | [4 priorities for implementing AI agents](https://www.servicenow.com/uk/blogs/2026/4-priorities-for-implementing-ai-agents) | vendor workflow |
| 2026-10-14 | [The blind spots of agentic pentesting and how to close them](https://www.bleepingcomputer.com/news/security/the-blind-spots-of-agentic-pentesting-and-how-to-close-them/) | vendor-authored technical commentary published by BleepingComputer |
| 2026-10-13 | [Beyond the hype: what Mythos actually means for security teams](https://health-isac.org/beyond-the-hype-what-mythos-actually-means-for-security-teams/) | session description only; linked recording not transcribed |
| 2026-10-13 | [AI pentesting or AI-powered AppSec?](https://health-isac.org/ai-pentesting-or-ai-powered-appsec/) | resource description only; linked material not assumed read |
| 2026-10-15 | [Unit 42: AI-assisted Linux espionage and SOC detection (2026-10-15)](https://unit42.paloaltonetworks.com/ai-campaign-targets-linux-infrastructure/) | primary vendor threat research; owner defensive summary |

The ServiceNow and Unit 42 entries are owner-reviewed summaries, labeled as such. Original publisher HTML for the other six is retained privately with SHA-256 pins in data/knowledge/originals. Health-ISAC resource descriptions do not establish the contents of linked recordings or presentations; those media were not transcribed. Vendor performance assertions are not independent benchmarks. Brookings is author policy commentary, not binding law.

## Coaching coverage

- Tools and workflows: Snyk Evo agents operating deterministic analysis tools; SOC Prime Prime Architect threat summaries and Attack Flow; ServiceNow flow actions, RAG, scripts, AI skills and subflows; Picus exposure validation and authorized pentesting coverage.
- Throughput: faster code/finding generation creates pressure on triage, independent verification, remediation and regression testing. The Snyk release describes eight vulnerabilities introduced per one remediated in its data; attribute this to the vendor and its sample, never a universal ratio or a station benchmark. Practice measuring validated fixes/day, backlog growth, analyst review time, false positives, service latency and API/token budgets. These practice metrics are owner coaching suggestions, not measured source results.
- Governance: named ownership, scoped permissions, runtime monitoring, traceable evidence, intervention thresholds and bounded costs/time. Separate policy recommendations from enacted requirements.
- SOC: converting threat reports into candidate detection logic requires analyst validation against actual telemetry. Detecting malicious behavior is different from attributing code to AI. Unit 42 reports suggestive script artifacts; they do not identify the model or prove autonomous operation. Activity occurred October 2025-April 2026; the report was published this week.
- Mythos: the October 13 Health-ISAC/Bishop Fox description discusses SDLC fit, costs at scale and expertise. It is not a new Mythos release announcement or an independently verified capability evaluation.

## Model download and identity

Display names: **Larpus 3.5 27B Q4** for existing `qwen3.5:27b-q4_K_M`; **Larpus 3.8 27B Q4** for the requested new download. The tooltip retains the actual runtime tag. Branding does not change upstream identity.

Qwen3.8 artifact: `unsloth/Qwen3.8-27B-GGUF`, revision `4ca720788d1e01f1bff70c033e0d0028fd02e502`, file `Qwen3.8-27B-UD-Q4_K_M.gguf`, 16,464,440,224 bytes. Upstream model: `Qwen/Qwen3.8-27B`. Quantization is Unsloth dynamic Q4_K_M, not an official Qwen-produced quantization. Expected SHA-256: `322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482`.

Private download/verification receipt: `data/model-downloads/larpus-3.8.json`; final owner-side filename `Larpus-3.8-27B-Q4.gguf`. This download does not select or load the new model. Offline Ollama compatibility, GPU residency, quality and latency require a separately scoped model-maintenance evaluation. The running Qwen3.5 model remains selected.

## Release evidence

Candidate `a6455f8078d14a28889b08fec1565fc5` is based on active frozen release `b5a6e9fc6b5f40b4af7d89870d784369`. Only eight-source library additions/embeddings, exact owner-curation URL approvals, model display metadata and HUD labels changed. Unrelated working changes were excluded.

The working checkout catalog/briefs/URL approvals were merged without replacing its unrelated in-progress database and provenance changes. Its derived knowledge artifacts need a normal rebuild as part of that separate work; the isolated release contains a matched, hash-verified database, embeddings and provenance.

Preparation, activation and download completion results are recorded below after verification. No commit or push requested.


Verified outcome: candidate activated successfully as `a6455f8078d14a28889b08fec1565fc5`; prior release `b5a6e9fc6b5f40b4af7d89870d784369` retained. Preparation passed the full Python/HUD checks, isolation checks and all 70 scan targets; the same 11 reviewed MCP warnings remain. This is focused regression evidence, not an independent audit.

Live broker test passed preemption and resumption (chat after preemption 3.297 seconds). Serving HTTP returned 200 for a new IT/Cyber question, citing the new October 15 SOC Prime source with no unknown citation IDs (12.125 seconds total). Seven direct retrieval probes returned the intended weekly sources; older unrelated results can still be included by retrieval, so this does not establish perfect precision. All required station-health checks pass; overall remains degraded for retained scan warnings. CA-verified unauthenticated LAN access returns 401. Model and selected voice container IDs and start times are unchanged across activation.

The gateway drained and briefly rebound listeners; this was not zero downtime. LAN sessions require a fresh login; refresh the HUD to load the new display label. No actual rollback, physical browser/speaker acceptance or Qwen3.8 runtime evaluation was performed. The already-stopped owner notes writer was not restarted.

Qwen3.8 download completed: 16,464,440,224-byte GGUF matched the expected SHA-256. Temporary range-download parts were removed after verification; the named model file and provenance receipt remain. No active model cache or model container was replaced.

Private receipts: `data/cyber-week-validation.json`, `data/cyber-week-broker-live.json`, `data/cyber-week-production.json`, `data/cyber-week-services-before.json`, `data/model-downloads/larpus-3.8.json`.
