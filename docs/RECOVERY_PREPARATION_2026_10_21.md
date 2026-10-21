# Recovery and owner tools — production preparation

2026-10-21. Preparation only; no activation, installation, observation window,
arming, owner-data backup or live answer benchmark is authorized by this record.

## Source and scope

Current candidate: `b6dffca22d244953acb3a8574c232e69`.
Rejected candidate retained: `ff5b15198b8943548b92177673dcf716`.
Baseline selected release: `042f91c0a1454887a694c945f49237ad`.
Existing previous release: `7df2e957751642d6ace4630fa047fe94`.

The candidate is a separate source variant built from the active payload,
not the full experimental checkout. Its 40 changed payload files add generation-
bound gateway health, startup admission, private-socket failure normalization,
gateway recovery and owner backup/status/quality/verification tools and tests.
The production complexity policy is unchanged. Corpus, prompts, skill registry,
HUD and configuration match the active payload byte for byte. Inference and
MCP-client transport match exactly. Execution profiles and the MCP Skills
extension are absent, not promoted by preparation or by the source commit.

Profile-dependent runtime timing instrumentation remains in the source branch
for later acceptance. The candidate's benchmark module contains only the pure
numeric accounting functions needed by the offline performance gate: no profile
selection, HTTP benchmark runner or live-measurement CLI. Backup remains
synthetic-only pending key custody; retention is plan-only. Recovery is disabled
by default and no production supervisor was launched.

The normalized public source delta is
[recovery-owner-tools-2026-10-21.patch](releases/recovery-owner-tools-2026-10-21.patch),
SHA256 `d6dc7fd3b6ceccb3cfea362b5860f0abd9f4c568a69807e46c0d8abfb98000a0`.
It applies to a separate copy of the baseline, never to frozen release files.
Replay in a disposable copy reproduced all 40 changed files as normalized text
(UTF-8 BOM and CRLF ignored). Frozen hashes, rather than this normalized patch,
bind the actual bytes.
Frozen `release.json` file hashes and receipt pins remain authoritative for the
actual candidate bytes. The source commit also retains experimental features
already present on main; committing does not activate them.

## Checks and retained failures

The initial scoped preflight reported 71 passing checks and one missing producer
method: patch application had skipped the copied source. Explicit source-builder
changes corrected it; the producer regression then passed. The main checkout
and serving frozen payload were not edited by that correction.

Initial staging refused provenance drift because the copied source lacked the
source-only reviewed research catalog used to reproduce existing metadata. Copying
the owner's unchanged catalog made the provenance check pass. No indexed corpus,
provenance entry, original document or frozen file was regenerated or modified.

Staging used the existing owner command:

```powershell
python scripts/releases.py stage --source data/recovery-production-20261021/source
python scripts/releases.py prepare b6dffca22d244953acb3a8574c232e69
```

The isolated candidate uses its own execution containers and release-local scan
data, sharing existing pinned model and CPU voice. Optional encryption requirement
pinning remains owner-checkout provisioning metadata, not a model/agent dependency
installation. No shared Python/scanner dependency was changed.

Fresh-context independent review `/root/production_candidate_review` approved
the scoped public source with no critical/important finding. It confirmed the
runtime delta is limited to gateway, health, local model transport and model route
startup guard; authentication precedes gating and POST drain checks remain.
This is source review, not live device or exhaustive security acceptance.

First frozen preparation refused the candidate after 413 tests, one error and
two skips. Its copied streaming mock still asserted execution-profile metadata
that production deliberately does not send. The mutable source now retains the
baseline mock signature/contract while keeping the added truncation checks.
Three focused streaming/producer checks passed. No frozen file was edited.
Only the failed candidate's exact agent, broker and notes containers were stopped;
the gateway, model and CPU voice stayed running. The rejected snapshot, image
artifacts and log remain available. A fresh snapshot independently repeats all
preparation gates; it does not inherit the failed run as approval.

Independent review compared the second candidate with the first and confirmed
this test adaptation is their sole public-source difference. Review remains
approved; no runtime or policy code changed to obtain a passing test.

Owner-private receipts are under `data/recovery-production-20261021`: source and
variant manifests, before/after identity evidence, preparation log/result and
bounded availability samples. Availability sampling covers only its recorded
window; it is not a claim of zero downtime or complete uptime coverage.

## Preparation outcome

Candidate `b6dffca22d244953acb3a8574c232e69` is **prepared, not activated**.
The ordinary preparation command exited 0. Frozen Python tests, unchanged
complexity limits (724 functions / 91 modules), companion contracts, broker
prompt pins, all ten production UI suites, scorer switching and isolation checks
passed. The successful wrapper retains stdout; unittest's successful stderr
summary is not retained by the updater. The preceding rejected run recorded
413 tests and two skips; the fresh run changed only that fixture's contract.

Fresh static scanning completed all 70 targets: 69 clean skills and MCP warning
status, HIGH severity, score 66, 11 issues. MCP issue signatures exactly match
the active release's retained reviewed inventory. Warnings are not clean-scan
claims. Source fingerprint:
`27aedf79f77abd06582fedac3650d2215b71e8450ecec1a7b79127124b17aa12`.
Fresh `releases.validate()` verified payload, deployment, voice and scan pins.

Post-preparation identity checks confirmed the selected/previous releases remain
unchanged, gateway PID 27572 and creation identity match, every active payload
hash matches, model/voice image IDs and start times match, both remain running,
and there is no pending cutover. Twelve saved-health samples in the first
preparation window and one during the fresh scan all returned HTTP 200. These
bounded observations do not prove uninterrupted availability or live answer
quality. Private `after.json` and `prepare-result-b6dffca2.json` retain results.

The public-source whitespace check excludes the patch's syntactic context spaces
and ignores existing extra blank lines at test-file EOF; it reports no other
whitespace errors. No source policy or frozen receipt was changed for that check.

## Separate rollout gates

Even a prepared candidate is not activated or accepted. A later activation needs
explicit owner authorization and the normal draining updater. LAN sessions need
a fresh login after gateway replacement; brief rebinding is not zero downtime.
Supervisor observation and installation/arming remain separate authorized steps.
Key custody and an owner-data restore rehearsal remain undecided. Human answer
review and live latency evaluation remain unperformed. No push is part of this
request.
