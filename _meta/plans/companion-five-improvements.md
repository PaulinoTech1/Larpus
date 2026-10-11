# Five companion improvements
Goal: responsive CPU voice, opt-in local memory, better evidence, role evaluations and usable HUD.
Constraint: no action tools, cloud, model change or auth/binding change; preserve production and old tabs.
Inputs: existing CPU speech models, screened immutable index, local persona configs and browser history.
Outputs: persistent voice sidecar, saved chats/owner notes, expanded evidence cards, offline eval runner and controls.
Done: focused regressions and release gates pass, candidate measured, activated with rollback, limits documented.
Alternatives: server-wide history storage would mix local and LAN sessions and add sensitive shared state; use opt-in bounded browser storage with export/delete instead.
Alternatives: new speech engines/vector service/framework add dependencies; cache existing speech models and extend SQLite retrieval and vanilla HUD instead.
Voice maintenance: build a separate network-none, CPU-only persistent Unix-socket worker from cached image/artifacts. Pin its name/image/hash per release; never replace active voice or global profile. Keep both workers for rollback.
Memory: save completed turns and explicit dated owner notes locally; no automatic inferred memory, no new filesystem or MCP tool. Notes are bounded user data, never system instructions.
Retrieval: prefer content matches, assemble adjacent same-source passages within existing context budget, attach screened previews and dates, validate claimed source IDs.
Evaluations: authored scenarios for all 12 roles, deterministic contract checks plus optional local-model run with explicit rubric and retained failures; no fake expertise scores.
HUD: quiet technical cyan; chat gets more space, torus stays identity. Search skills, stop, stage indicators and expandable sources; preserve reduced motion and old stream events.
Validation: meaningful edge/failure tests, role/retrieval scenarios, live voice timing and network checks; rendered QA if browser tools available.
Commit boundary: no commit or push requested for this work.
AgentDB is unavailable in this environment; repository instructions and checked-in evidence are the working context.

Completed: active runtime 74bbaa7883bd4fe2807fb0aa5ec7e61a, previous retained.
Evidence: docs/COMPANION.md; 113 Python, 4 Node, 6 isolation; 70 scanned targets,
8 unchanged MCP warnings; 29 local-model scenarios reviewed with explicit gaps.
Owner restart selector fixed in working-checkout tooling, 12 focused tests pass.
Limits: no rendered browser or physical audio/reboot acceptance; changes uncommitted.
