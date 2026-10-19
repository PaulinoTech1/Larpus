# MCP Skills acceptance — 2026-10-19

Implementation is on `codex/mcp-skills-20261019`. The selected station release remains
`7df2e957751642d6ace4630fa047fe94`. Candidate `c7a16c1c9fbc408199b1d05a57d15244`
was staged from that frozen payload plus only the Skills changes. Activation is not authorized by this handoff.

| Check | Status | Evidence / limit |
| --- | --- | --- |
| Original baseline | Pass | 343 tests, two existing skips |
| Regression | Pass | 357 tests, four skips; later focused 16 tests, two platform skips |
| Existing UI contracts | Pass | All ten `scripts.ui_checks.TESTS` suites |
| Broker prompt bytes | Pass | 429 chat and 18 notes approved hashes unchanged |
| Companion catalog | Pass | 37 cases; manual answer scoring remains separate |
| Complexity | Pass | Existing thresholds unchanged |
| Windows modern/legacy stdio | Pass | Full 69-entry pagination; exact approved three-tool descriptors; list/get/read |
| Raw protocol | Pass | Required metadata, cache fields, canonical URI checks and sanitized errors |
| Activation authority | Pass | Reading does not select; persona denial and failed verification reach no model |
| Tamper/reference peer | Pass | Missing/duplicate manifest, wrong digest/size/frontmatter, truncation and foreign origin rejected |
| Linux stdio and symlinks | Pass | 13 actual sealed-agent tests, no skips; SDK 2.3.0 |
| Windows symlink creation | Unverified | OS privilege unavailable; explicit test skips |
| Frozen Linux preparation / isolation / scans | Pending | See preparation receipt; no clean scan claim yet |
| Live matched performance and answer review | Pending | Harness dry-run and metrics tests pass; live results separate |
| Candidate HTTP/browser/second-device acceptance | Unverified | Requires separately authorized activation |

Private raw logs live under `E:\speedzone_MS\LARPUS-worktrees\mcp-skills\data`.
The initial worktree test lacked ignored KaTeX assets; checksum-verified copies fixed it.
An early raw peer closed stdin before resource completion; its failed receipt is retained,
and the fixed peer keeps stdin open until the response. Neither failed run was counted as passing.

Fresh review found and fixed encoded-name normalization and tab-separated YAML ambiguity.
The resource callback now resolves the original request URI, and unsupported frontmatter
is rejected rather than partially interpreted. This is a deliberately narrow local format,
not a general YAML implementation or remote skill importer.

The first candidate `651658465bf54e5e9298c7d34a7082f6` failed its frozen test gate:
three metrics-test import errors exposed a missing older-baseline helper. It remains
staged, never prepared or activated. The replacement adds only the required unchanged
metrics helper and existing eight-case catalog, plus the final bounded-environment tests.
The baseline's initial readiness failed while its existing model was unloaded; after warming
the already selected 3.8, all functional/security/voice checks passed, retaining the prior
static-scan warning. No warning was relabeled or suppressed.

The second snapshot `361141c79568447b8ccc11df39b596f0` prepared successfully,
retaining all 11 reviewed MCP findings. The final snapshot supersedes its benchmark
harness: fresh review required A/B workload equality, verified fingerprints and
instruction hashes, correct partial/citation metrics and durable failure reports.
All seven metrics tests pass and reviewer re-review approved those fixes.
