# MCP Skills acceptance — 2026-10-19

Implementation `d14c2b7` was merged into main as `e9de9de`. The selected station release remains
`7df2e957751642d6ace4630fa047fe94`. Candidate `c7a16c1c9fbc408199b1d05a57d15244`
was staged from that frozen payload plus only the Skills changes. Activation is not authorized by this handoff.

| Check | Status | Evidence / limit |
| --- | --- | --- |
| Original baseline | Pass | 343 tests, two existing skips |
| Integrated main regression | Pass | 398 tests, four skips |
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
| Frozen preparation / isolation / scans | Pass with retained findings | Final candidate prepared; 70 targets complete; 11 reviewed MCP findings retained, not a clean scan |
| Focused live performance | Mixed / not accepted for promotion | Two 42-call runs; first Home +11.8%, confirmation math +11.9%; pacing varied |
| Eight-case matched MCP | Not accepted for promotion | Two valid 64-call runs; seven then five cases exceed +5% first-text median; cadence mixed |
| Separate baseline HTTP | Delivery pass | Valid 32-call run; 24 measured replies with complete stage timings; no candidate HTTP comparison |
| Answer quality | Unresolved | All 192 measured answers across five runs received AI rubric review; errors in both snapshots; not independent human validation |
| Controlled baseline restart | Pass within scope | Corrected owner start: exactly six expected containers, full GPU/context readiness, both sockets ready, first chat succeeds; not a Windows cold boot or candidate gate activation |
| Original stopped state | Restored | Gateway absent, no running LARPUS containers before WSL termination, no running distros afterward; nightly notes task Disabled |
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

## Performance decision

No speedup, stable latency neutrality or blanket quality-preservation claim is
accepted. Every run and its registered confirmation is retained in the
[measurement report](MCP_SKILLS_PERFORMANCE_2026_10_19.md). There are no further
retries to seek a pass. No optimization C, approval cache, prompt change or
weakened security guard was introduced. The read-only extension is implemented,
but the prepared candidate remains inactive.

The existing HTTP owner CLI also needed a repository-root import bootstrap when
launched by filename. Its dry-run and full 32-request baseline run passed after
that one-line fix; this does not change frozen application runtime behavior.

## Availability and owner handoff

The final main test run passed 398 tests in 134.025 seconds with four documented
skips. Both selected and candidate frozen payload/fingerprint/deployment/voice/scan
pins were revalidated after testing. Selection and previous release remain
`7df2e957751642d6ace4630fa047fe94` and `f08b98ea2f34407cb77dc79aa7d7866a`.
The original stopped state is restored; no Podman query was made after WSL
termination. Owner data and unrelated untracked files were preserved.

Startup follow-up found whole-pod start reviving old retained containers. The
owner CLI now starts the model and selected services only; focused RED/GREEN
checks, the final full suite and a real start-from-stopped inventory/first-chat
check cover that correction. See [startup evidence](BROKER_COLD_START_RECOVERY_2026_10_19.md).
The first restart, refused cleanup, scoped cleanup and corrected startup receipts
remain private alongside all benchmark/review records on E:.

This handoff does not authorize promotion. If acceptance gaps are addressed and
the owner later explicitly authorizes this prepared candidate, validate its
prepared status and use `python scripts/releases.py activate c7a16c1c9fbc408199b1d05a57d15244`.
Only after such activation, `python scripts/releases.py rollback` returns to the
then-previous release through the normal drain/readiness flow. Do not use rollback
now: no candidate was activated. Rebinding is not zero downtime and LAN sessions
may require login again. `python scripts/releases.py start` restarts the current
selected baseline when the owner wants the station running.
