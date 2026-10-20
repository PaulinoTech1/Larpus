# Modularity engineering report

2026-10-20. The approved modular implementation, bounded fault tests, prepared
candidate and 300-attempt live comparison are complete. **Production acceptance
is rejected:** Ultra Fast is faster on this workload, but misses the five-second
mean/p95 target and quality parity is unestablished. No activation, commit or
push was performed. The initially stopped station was restored.

## Outcome and evidence

| Requirement | Result and evidence |
| --- | --- |
| Source-based modularity audit | [Inventory](module-inventory.md), [dependencies](dependency-map.md), [pipeline](execution-pipeline.md), [boundaries](security-boundaries.md), [contracts](module-contracts.md), [findings](audit-findings.md), [12-dimension before/after scorecard](modularity-scorecard.md) |
| Narrow independent interfaces | Pure fresh hashing; immutable profile resolver; bounded observation acquisition; request-local numeric trace. Orchestration retains policy ownership. |
| Compatible secure modes | Verified default, experimental Ultra Fast fresh observations, Diagnostic with explicit base; separate interaction labels. Old request omission/tool descriptors remain compatible. No permission, URL, model-option or bypass fields accepted. |
| Mandatory security independent of profile | One shared path and validators; selected scanner/evidence/storage/policy/source/stream/cancellation faults and observation mutation matrix. No allow-verdict cache, relaxed quota or reduced retrieval/model quality settings. |
| Optional component behavior | Reviewed skill removal distinguished from catalog corruption; absent derived notes and existing BM25/NumPy fallback tests. No fictional runtime critic was added. |
| Reproducible timing | 20 cases x 5 rounds x 3 profiles, exact identities/session partitions, fixed seed, frozen served receipts, model/scorer checks, excluded warm-ups and no replacement of failures. |
| At least 100 measured calls/configuration | 100 attempts/profile over two invocations; 97 Verified, 100 Ultra Fast, 98 Diagnostic replies. Five failures retained. |
| Mean and p95 first text below 5s | Failed. Ultra Fast 5.718/7.980s; Verified 6.703/9.045s; Diagnostic 6.602/8.788s. Owner HTTP only. |
| Output consistency | Passed registered maximum-gap median/p95 ratio ceiling 1.10: Ultra Fast ratios 0.918/0.983. No conditional confirmation required. |
| Answer quality | All295 successful replies assessed blind, five0-2 dimensions; 12 critical flags. Useful-answer mean drop and unmatched baseline failures prevent a parity claim. Agent review is not human certification. |
| Stock hardware/resource evidence | Read-only host/GPU boundary telemetry, no power/clock changes; CPU temperature/effective clocks not captured. No silicon-lottery conclusion. |
| Availability and release discipline | Narrow candidate prepared without changing selected7df2 or frozen pins. Original warnings retained. Owner-loopback-only temporary gateway; stopped state independently verified after run. |

See the [full measured acceptance report](../EXECUTION_PROFILES_PERFORMANCE_2026_10_20.md)
for all latency/resource statistics, paired deltas, rubric scores and limits.

## Baseline and final verification

Base checkout `64e49c731f142a4403cba8ab02801bcb9592b3ad`: 414 tests with four
skips in 152.897s (`data/modularity-baseline-tests.log`). Static inventory initially
covered 98 owned Python modules; checkout/frozen differences and source hashes are
in `data/modularity-audit/source-map.json`. Static syntax is not a dynamic call
graph. Downloaded repository instructions were excluded.

Final isolated checkout suite: **457 tests, four skips, 203.862s**, process exit0;
wall 208.461s. Receipt: `data/execution-profiles/final-suite.json` and matching log.
TEMP/TMP stayed under E:/speedzone_MS/LARPUS/data/tmp; tests used synthetic corpus
and no private owner index. All 11 JavaScript UI suites passed, recorded in
`data/execution-profiles/final-ui.json`. Mock DOM tests are not rendered-device
acceptance. The after inventory has 104 owned modules. The pure hashing extraction
breaks the isolation/scanner/MCP import cycle; knowledge/retrieval/worker and owner
model/release cycles remain. Three specific import-count allowances were reviewed;
no global/function complexity ceiling was raised.

Independent whole-change review identified served-system pinning, exact sample
identity validation and scanner coverage issues. Their focused regression fixes
were verified by the same reviewer, with no remaining Important issue in those
scoped fixes. Deferred minor: benchmark receipt checking compares source/model/
profile, but not returned Diagnostic base/interaction; strict transport resolution
and fixed request generation still apply. Generic failed-request records also
lack underlying diagnostic classification. These limits are not waived.

## Preparation and stopped-state restoration

Production continues to select `7df2e957751642d6ace4630fa047fe94`. Candidate
`dc74ddc8315d4fdaa6349c72fc40bc46` uses that payload plus 31 scoped files, excluding
unrelated inactive Skills/CI/startup/UI additions. Exact corpus/provenance was
retained without rebuild. Preparation exit0 in 650.956s, 70 scan targets complete,
same 11 reviewed warnings. Original HIGH/MEDIUM/LOW warnings were not suppressed.
The earlier 9ed01f2 snapshot failed a diagnostics UI harness check and remained
frozen; its replacement passed. No activation/rollback was attempted.

The authorized window ran the frozen candidate on 127.0.0.1 only and retained
stock settings, 20-processor WSL ceiling, model 3.8, Assembly optimized and original
CPU voice image. Supervisor finally stopped its gateway/containers, pod and Larpus
WSL. Saved cleanup state reports no remaining containers. Independent external
checks found no WSL instance and no 8080/11434 listener; notes task Disabled.
Active pointer unchanged. Original owner files New Text Document.txt and
larpus-sensors.csv were preserved. All new artifacts stayed on E:.

Owner-local originals: `data/execution-profiles/live-20261020-dc74ddc8/`.
Design: [approved spec](../superpowers/specs/2026-10-19-secure-execution-profiles-design.md).
Plan: [execution plan](../superpowers/plans/2026-10-19-secure-execution-profiles.md).
Ledger: `data/execution-profiles/progress.md`.

## Next decisions

Retain current production. Fresh preflight collection saved about 1s median, but
MCP setup and retrieval remain substantial; no second-model deliberation exists
to disable. Any further startup/transport reuse needs explicit freshness,
cancellation, rate-limit and authority design. Do not silently keep sessions or
cache approval to chase five seconds.

Prioritize correcting uncertainty/stability/validation-metric/source-attribution
failures before claiming quality parity. Investigate the uncertainty-case failures
with bounded diagnostics in a separate experiment. Live logging-on/off causal
controls, long-history/concurrent/cold-cache and rendered HUD/LAN acceptance were
not established by this fixed sequential workload. The recorded synthetic trace
control measures wrapper cost only. No further live run was used to retry until
passing. Any later activation requires fresh prepared validation and the staged
updater; LAN re-login and brief port rebinding must be disclosed.
