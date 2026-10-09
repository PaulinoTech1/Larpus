Goal: current Larpus remains usable during checkout edits, builds, tests and static scans; controlled cutover with rollback.
Constraints: Windows 11 Home, fixed local/LAN auth/TLS, same offline model/CPU voice, no new ports/cloud or duplicate GPU model, preserve owner data.
Inputs: current known-good deployed source and scan; working checkout; rootless Podman cache.
Outputs: frozen source/UI/index releases, separate candidate agent/scan/health/profile, owner CLI stage/prepare/activate/rollback/start/status, graceful drain and startup gates.
Done when: live chat remains available during source drift and preparation; invalid candidate rejected without stopping active; candidate/rollback verified live; all tests/scan/isolation pass with retained known warnings.
Approaches: stop/rebuild in place (long outage, reject); reverse proxy plus two full serving stacks (more moving parts/ports, reject); frozen releases + side-by-side stdio agents and brief drain/rebind (selected, standard library, no proxy).
One shared data junction preserves password/TLS/voice profile; per-release deployment.json and release-state isolate mutable health/scan. Model/voice and quarantine remain existing services/volume.
Bootstrap current release already copied before source edits. Candidate files are hash-pinned; not a new ACL/host-adversary claim. Preparation does not activate. Owner recovery command handles interrupted cutover journal. No commits/push requested. AgentDB unavailable.

Completed: live chat during edits and candidate scan, prepared offline candidate,
successful activation, live stream drain/rollback, forced candidate startup exit
with automatic restoration, and unprepared release rejection without active PID
change. Corrected functional readiness endpoint and stale-journal PID recovery.
Active 4055b4e81b204952b30b5acb2b54a8d7; previous frozen legacy retained.
Evidence docs/AVAILABLE-UPDATES-PROBES.json and scan receipt. No pending journal.
