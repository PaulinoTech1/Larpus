# Six reliability and quality improvements

Native execution of the owner-requested six issues, extending the approved
recovery plan and `PROJECT_IMPROVEMENT_PLAN_2026_10_20.md` on main. No production
activation, observation, arming, dependency installation or live GPU benchmarks.
No commits/push in this execution unless newly requested. Preserve existing work.

1. Independent review of final observe-only death-count transitions; fix any
   concrete findings with failing regressions. Record review source and limits.
2. `scripts/backup_store.py`: AES-256-GCM encrypted, versioned SQLite snapshots;
   validated owner-protected staging; atomic create-only file publication;
   bounded size and SQLite deadline; temporary-target restore; explicit key bytes,
   no key in artifacts; non-destructive authenticated retention planning.
   Keep legacy synthetic HMAC fixture helper explicitly separate. Tests cover
   committed/uncommitted rows, wrong key, tampering, existing target, ENOSPC,
   post-validation publication race, cleanup and separate-directory restoration.
   Owner destination/key custody/RPO/RTO remain a separate pending decision.
3. `scripts/quality_evaluation.py`, `evals/quality-support.json` and tests:
   family-disjoint development/held-out cases, public synthetic sources and
   multi-turn rubric. Hash-bound human/agent claims with supported/unsupported/
   uncertain judgments; completion failure remains in denominator, absent reviews
   remain null. No automatic entailment claim or routing/model behavior change.
4. `scripts/owner_status.py`: bounded read-only selected-release/health/recovery
   evidence, prepared releases, Git checkout/worktree divergence and feature-state
   matrix. Missing/stale evidence never ready. No WSL boot, scan, model generation
   or state mutation. Optional root only injected by tests, not accepted on CLI.
5. `scripts/verify.py`: one fail-fast canonical local command for complexity,
   isolated Python, shared UI manifest, prompt pins and offline quality checks.
   Reuse from CI, retain CI-only inventory/evaluations. Test command ordering and
   no deployment/live control. Document `python scripts/verify.py`.
6. `runtime/execution_trace.py`: derive exclusive sequential inference-stage
   intervals from monotonic local offsets without summing overlapping counters;
   add bounded parent MCP preflight/connect/call exclusive durations; verify
   malformed/backwards/missing timing rejection with fake clocks. Keep ordinary
   generation/security paths unchanged. Add offline performance report admission
   that refuses promotion without completed quality review. Live optimization
   waits for quality gate and authorized measurement window; no fabricated gains.

All new functions retain current complexity limits. RED/GREEN per behavior,
focused tests followed by full canonical validation, independent final review.
Receipts in ignored `data/six-improvements/`; source/docs remain uncommitted.
