# Broker scheduling, scoped capabilities and reproducible verification
Goal: prevent long background inference from monopolizing chat; independently
restrict caller capabilities and instruction templates; reproduce evidence.
Constraints: frozen production unchanged while building/preparing, existing model
and CPU voice stay loaded, offline runtime, no owner data publication, no commit.
Inputs: approved chat/notes payloads over physically separate Unix socket volumes.
Outputs: broker scheduler/cancellation, pinned prompt hashes, rate/token budgets,
minimal isolated notes worker, release checks, local synthetic/live report CLI.
Done when: deterministic stalled-background cancellation (and failed cancellation),
priority/rate/template/role/mount negatives, real CPU/GPU-backed cancellation and
HUD chat/stream/notes saves, full release gates and controlled activation pass.
Choose stdlib scheduler and two socket capabilities, separate notes container;
reject tokens co-located with agent, untrusted priority headers, longer chat waits.
Global one-inference slot; note cancellation disconnects upstream and verifies a
one-token completion on pinned parallel=1 runner before releasing it. Failure is
closed, never just unlock. Bound total job lifetimes with shutdown timers.
Chat/notes have independent request and reserved-output budgets; status separate.
Hash-pin allowed system templates, not semantic guarantees; malicious user prose
and trusted host/broker compromise remain limits. Interrupted notes stay pending.
Verification defaults local, no cloud CI without owner exception; JSON reports
bind commit/policy/test hashes and mark synthetic vs deployment evidence clearly.
Maintenance: stage new broker+agent+minimal notes service beside current release;
pause only notes around cutover, preserve deadline/progress; no model replacement.
Retained brokers cannot enforce one global scheduler across release generations:
only active/candidate authorized probes; stop previous note service at cutover.
Contract: runtime broker/scheduler/client/notes/prompt constants, config manifests,
scripts releases/study notes/verification, deploy recipes, tests and related docs.

Completed 2026-10-11: release fb20ec0c6bc0419dbc6a3b298116820d active;
local synthetic/real-model/HUD checks passed, notes saved again, model/voice
unchanged. Ten static warnings retained; no cloud CI, commit or push. Evidence:
docs/BROKER_HARDENING.md and docs/verification/.
