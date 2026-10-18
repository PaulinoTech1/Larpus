# Larpus model selector design

Date: 2026-10-17. Status: approved by the owner; implementation planning in progress.

## Intended result

The existing HUD gets a station-wide selector for **Larpus 3.5 27B Q4** and **Larpus 3.8 27B Q4**, plus an explicit **Switch model** button. Selecting an option alone does not change the running model. The selected model serves every persona. Conversation messages and local saved chats stay intact; changing weights does not increase the conversation context or erase its limits.

Before switching, display: **Switching models pauses chat while the current work finishes and the new model loads. This can take a few minutes, especially after a cold start. Voice remains available. Your conversation stays here.** Do not show a fabricated countdown or promise a fixed load time. Display the current model separately from the requested model.

## Approach and alternatives

Use the existing Ollama server and inference broker, with an owner-controlled switch operation restricted to these two pinned local models. Extend their current policies and status contracts rather than allowing the agent to choose arbitrary model tags. A browser-only label change would not switch inference. Restarting a different frozen release for each model would be heavier, would invalidate LAN login sessions and would conflate model changes with application updates; it is not the proposed approach.

The 24 GiB GPU cannot keep both 27B models loaded. Switching therefore explicitly unloads one before loading the other. No fallback to CPU or cloud is introduced.

## Owner control and state

The authenticated, same-origin HUD may request only a catalog ID, never a command, path, download URL, model parameters or an arbitrary Ollama tag. Preserve existing password, LAN binding, rate limits and CSRF/origin checks. Add no model-control MCP tool and expose no owner Podman capability to the model or agent image.

The Windows owner side executes a fixed local operation with a persisted journal and a single-operation lock. The broker admits only the selected, approved model and blocks new inference during a switch. Read-only status remains available. Existing tabs and older API clients remain compatible; they use the station's current selection without needing a new chat-request field. UI status is polled and survives page refresh.

The model catalog records the display name separately from upstream identity, exact local tag and checksum. Both models must be installed from verified local artifacts before being offered as available. Downloads are outside the switch operation. Importing the existing 3.8 artifact into the shared offline cache is a separate, recorded owner maintenance step using the existing pinned images and dependencies.

## Switching sequence

1. Validate the requested ID, installed/pinned artifact, operation lock and available services. Requesting the already active model is a no-op.
2. Refuse a new switch during a GPU notes maintenance job, stating why. Do not cancel notes or silently change their model.
3. Wait for active inference to finish; block new chat/compression/notes requests with an explicit retry/status response. Keep gateway and CPU voice running.
4. Record the previous selection, unload its GPU weights and load the target through the fixed owner path with the approved context and bounded warm-up request.
5. Verify the exact target model, full GPU residency, functional response and applicable readiness checks. Publish the new active selection only after these pass.
6. On failure, unload the candidate and restore/verify the prior model. Report the failure honestly; if restoration fails, retain an actionable failed state and recovery instructions rather than reporting ready.

Show real stages: **Waiting for current reply**, **Unloading current model**, **Loading selected model**, **Checking model**, **Ready**, or **Restoring previous model / Failed**. Disable duplicate switch submissions and chat submission during the operation. Readiness derives from live checks, not a timer.

## Integration constraints

The current broker policy and personas assume only qwen3.5:27b-q4_K_M; inference, GPU placement checks, health reporting and system-prompt approval must agree on the selected model. Expand only the fixed local allowlist and preserve bounded context/output controls, prompt hashes, filtering, note preemption and the absence of direct inference fallback. Never add an arbitrary model field that the agent can exploit.

Initially retain the established 131,072-token chat context for both models only if 3.8 passes an actual full-GPU allocation/warm-up check at that setting. A failure blocks its availability at that context; do not silently reduce the existing context meter or claim an 8,192-token notes probe proves 131,072-token chat readiness. Voice settings remain independent.

## Validation and delivery

Write focused failing tests first for allowed IDs, duplicate/concurrent requests, busy-note refusal, current-request completion, unload/load ordering, failure restoration, persisted status, refreshed tabs, source/tag display and conversation preservation. Verify the old chat API remains compatible and that neither MCP nor model text can trigger switching. Test both switch directions locally, verify actual GPU residency, and check voice service continuity. Record observed load durations with their scope.

Keep production available during implementation and preparation. Preserve unrelated working changes; assemble an isolated candidate based on the active frozen release. Use the established stage/prepare/activate flow with complete regression/static checks and retained warnings. Model-cache maintenance and live switching tests have their own scoped interruption/restoration record. Do not change frozen active payloads, shared dependencies, bindings, authentication or images. Do not commit or push without a request.

## Current evidence

The private GPU notes batch finished with 102 saved facts, nine complete windows and eleven held windows. Its automatic restoration completed: 3.5 served a successful chat and was verified fully GPU-resident at 131,072 tokens; required health checks passed and voice stayed running. The 3.8 notes run demonstrated full GPU residency at 8,192 tokens only. This proposal does not imply the notes have been published or every generated claim independently verified.
