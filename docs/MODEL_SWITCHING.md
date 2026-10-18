# Local model switching

Use the model selector beside the current model, then press Switch. Choosing an entry alone does not switch. The selector is station-wide, so other tabs see the same selection and loading stages. Conversation and browser memory stay in place.

Available identities are Larpus 3.5 27B Q4 (`qwen3.5:27b-q4_K_M`) and Larpus 3.8 27B Q4 (`larpus3.8:27b-q4`). Exact upstream identities and weight hashes are in `config/model-selection.json`. Both have been qualified at 131,072 context tokens with full GPU placement on this station; this is a residency and short functional check, not a filled-context quality benchmark.

Switching pauses new inference, waits for current work, unloads the old model, loads and checks the requested model. This can take a few minutes, especially after a cold start. CPU voice and the gateway remain running. GPU notes maintenance blocks switching. New derived notes record the actual producing model per result; historical notes with unknown producers remain unknown.

A loading failure attempts to restore the previous model. If restoration fails, inference stays blocked and the HUD reports failure. Owner recovery: `python scripts/model-switch.py recover`; inspect with `python scripts/model-switch.py status`. Recovery uses the same fixed allowlist and exclusive maintenance lock. Do not manually edit frozen payloads, deployment pins, or selection files.

The separate `prepare-cache` and `qualify` commands are owner maintenance, not routine app updates. Qualification temporarily pauses chat and restores 3.5; do not run it while work is active. No model download or arbitrary tag is accepted through the HUD or MCP.

Application delivery uses the staged release flow in UPDATES.md. Activation briefly rebinds gateway ports and LAN sessions need a fresh login. Existing scan warnings remain visible. Automated UI harnesses check controls and conversation preservation; they do not establish rendered browser usability.

The owner updater rejects activation or rollback when its prepared model selection differs from the current ready selection. Switch to the matching model first, or prepare a fresh release. This check happens before draining the gateway.

## 2026-10-17 delivery evidence

Active release: `c67982159d99487d8635f362ae673407`. Prepared candidate tests, existing UI harnesses, isolation checks and 70 scan targets passed their release gates; the 11 reviewed MCP findings remain warnings. The new model-control UI harness also passed. The owner-side live preemption harness passed before activation.

Observed switches using already-cached local weights: 3.5 to 3.8 in 17.187 seconds, 3.8 to 3.5 in 21.328 seconds. These are observations, not cold-start guarantees. Each target was verified at 131,072 context tokens and full GPU placement, and accepted the existing chat request body. CPU voice synthesized audio during each switch. Model-server and voice image IDs/start times remained unchanged. LAN unauthenticated model controls returned 401, foreign-origin writes 403, arbitrary model IDs 400.

Final selection is 3.5, ready, with no selection error. Fresh station health has no errors and retains only its security-scan warning. No physical browser or audible playback test was available. Load-failure/restoration paths were checked with controlled fixtures; live fault injection and filled-context benchmarks were not performed. Live receipts are in `data/model-switch/`.

Open a new HUD tab to load the new controls while retaining an existing conversation tab. After the activation, LAN users must sign in again; the new session cookie also serves existing tabs.
