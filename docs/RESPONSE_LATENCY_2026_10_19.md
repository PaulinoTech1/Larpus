# Response latency measurements - 2026-10-19

The clean paired comparison reduced median time to first approved text from **5.869 to 5.457 seconds (7.0%)**. This measures the Windows MCP entrypoint including security preflight, MCP connection, retrieval, generation and output screening. It excludes browser paint, HTTP admission and initial module import. It is a small descriptive sample, not a tail-latency guarantee.

| Measurement | Baseline | Candidate | Evidence |
|---|---:|---:|---|
| First approved text, median | 5868.6 ms | 5456.5 ms | 16 measured requests per backend |
| Complete response, median | 7491.0 ms | 6975.6 ms | 32/32 requests successful |
| Linux retrieval, median | 2094.4 ms | 1880.4 ms | 12 measured pairs; identical evidence |
| Fresh complete isolation preflight | 1869.1 ms | 1658.7 ms | 8 component pairs |

Four cases cover Home Assistant greeting, norms, scalar ODE pushback and Cyber Coach SOC advice. One warm-up round was excluded, followed by four measured rounds with alternating backend order. All four case medians improved. The median within-pair first-text difference was 287.1 ms; this differs from the 412.1 ms difference between aggregate medians. Full retrieved source records matched in all 16/16 live pairs. Both arms used original Assembly to isolate the latency changes.

## Changes

Retrieval now borrows one verified, read-only SQLite connection throughout a request, including semantic candidates and continuation lookups. Each new request still verifies the database hash. Connections close on success and failure. A bounded 256 MiB read-only SQLite mapping reduces copying; SQLite may clamp or decline it.

Isolation now collects up to four validated OCI configurations in one fresh WSL process. Strict path, order, count, output-size and JSON validation remain. Image, mount, network, rootless and source-integrity checks remain fresh. No approval cache was added.

A tight-budget Windows replay exposed 194/188 database opens per request, reduced to one. A small completed deterministic replay measured 45.69 to 8.50 seconds, but that edge-case replay uses fixed ranking and is not normal chat latency. An earlier broad replay was stopped without a completed aggregate; its logical bytes read are not physical disk traffic.

## Quality and verification

Model weights, context, sampling, broker prompts, evidence budgets and deployed provenance behavior remain unchanged. Identical evidence supports preservation of retrieval behavior; it does not certify every generated claim. Both arms retained imprecise scalar-ODE stability wording. The citation identifier check does not establish claim support. The broader quality-routing plan remains pending.

The clean candidate passed its local suite, companion contract, ten UI suites, isolation checks and all 70 scan targets, retaining the same 11 reviewed MCP findings. Eleven focused connection/batch regression tests pass, including tampering, cleanup and malformed subprocess output. Two scoped code reviews found no remaining important findings.

Inherited checkout changes were discovered during comparison. Earlier candidates ce9a41052ac44faea274d07fc6320580 and f680649defcf4f30b7970f613854312c were not promoted. Their mixed or confounded results are excluded. The final source was rebuilt from the frozen active release, with only latency edits and the separately approved modular Assembly optimized integration. Existing unrelated checkout changes were preserved.

## Release and availability

Prepared and activated **7df2e957751642d6ace4630fa047fe94**, retaining f08b98ea2f34407cb77dc79aa7d7866a for rollback. Live health, model selection, pipeline selection and HTTP streaming passed. Assembly optimized is selected; original Assembly and NumPy remain available. The existing Larpus 3.8 GPU model, 131072 context, bindings, authentication and CPU voice image were preserved. No power or clock settings changed. Activation briefly rebinds the gateway; this is not zero downtime, and LAN clients require a fresh login.

The station was temporarily started for testing. Initial cold model/broker readiness failed; an idle model reload and broker restart recovered it. That cold-start issue is not claimed fixed. The gateway and all LARPUS containers are stopped, and the Larpus WSL distribution is terminated. The nightly notes task remains disabled. The shutdown receipt confirms completion.

All durable worktree and benchmark artifacts are on E:. The first preparation inherited C: temporary storage before TEMP/TMP were explicitly redirected to E:; temporary fixtures were removed. Subsequent preparations used E:.

## Reproduction artifacts

Worktree: `E:/speedzone_MS/LARPUS-worktrees/latency-quality`.
Receipts under `data/latency-quality/`: `pure-paired-response-report.json`, `pure-paired-response-manifest.json`, `pure-paired-evidence-check.json`, `pure-linux-io-report.json`, `oci-comparison.json`, `preflight-comparison.json`, `windows-replay-report.json`, `activation-check.json`, and `shutdown/`. Raw response receipts are private owner data. The clean source is retained under `data/latency-only-source`. No commit or push was made.
