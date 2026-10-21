# Owner verification, recovery and evidence

This implementation is in the recovery worktree, not the serving frozen release.
Production was not activated, restarted, armed or faulted by this work.

## One local verification command

```powershell
python scripts/verify.py
# Equivalent npm entry point:
npm.cmd test
```

This fails fast on complexity, the isolated Python suite, every UI suite from
`scripts/ui_checks.py`, broker prompt pins and the offline quality catalogue.
The isolated runner independently retains its complexity gate for direct use.
CI invokes this same command, adding its public-file inventory and companion/
detector evaluations. No generation, deployment or live station test is implied.
Node and existing Python dependencies must already be available. Optional
owner-side encryption dependency is pinned in `requirements-backup.txt` and
included explicitly in CI requirements; it is not installed into the model or
agent by these tools. No shared dependency was installed during this execution.

## One owner state snapshot

```powershell
python scripts/owner_status.py
```

The command discovers the owner repository via Git's common directory even when
run from a worktree. It reads selected release, saved health, prepared receipts,
recovery journal, checkout SHA/dirty paths and worktree inventory. Feature rows
distinguish selected-payload presence from checkout presence; presence does not
prove a feature is enabled or accepted. Prepared receipts are not revalidated
pins. No scanner, generation, WSL or container command is run.

Saved health marked `reported-ready-unbound` has passing required checks but
lacks the newer process-bound receipt. It is not freshly probed readiness.
Missing or stale evidence is unknown/stale. Security warnings remain separate
from functional readiness. Recovery status does not claim a supervisor is running.

## Encrypted backup rehearsal — synthetic only

The owner selected `D:\LARPUS-Backups`, three calendar months' retention and
**synthetic-only operation until key storage is decided**. No owner database has
been backed up, restored or replaced. No recovery key was persisted. No scheduled
backup or deletion job was created.

```powershell
python scripts/rehearse_backup.py
```

This creates a protected disposable directory on D:, a two-record synthetic
SQLite database and an ephemeral in-memory key. It exports an encrypted snapshot,
restores it into a separate directory, checks committed record IDs and removes
that run's disposable files. Numeric evidence can be redirected into ignored
owner data. The successful run restored both records and reported cleanup passed.

An earlier run exposed an unclosed SQLite connection and failed cleanup. It is
retained as a failed rehearsal; the connection handling was fixed. Automatic
approval review rejected recursive cleanup of the exact residual directory
`D:\LARPUS-Backups\synthetic-restore-khei8plm` as blocked by policy. That residue
is synthetic, may contain plaintext test rows and remains explicitly uncleaned.

`scripts/backup_store.py` uses AES-256-GCM with random 96-bit nonces and authenticated
format metadata, using the installed cryptography implementation. Its contract
follows the [official AEAD API](https://cryptography.io/en/latest/hazmat/primitives/aead/).
Keys must be exactly 32 random bytes and are supplied by the caller, never logged
or embedded. Wrong keys, modified ciphertext and malformed metadata refuse restore.
This is neither a password-based key-derivation scheme nor a key-custody service.

Snapshots use SQLite's backup API with a 60-second deadline and a 64 MiB database
limit. Larger stores are refused, not truncated. Owner-protected temporary
directories contain the plaintext snapshot; this is not secure erasure or a
claim that plaintext never touches disk. A crash may retain temporary files.
Owner-data use needs key custody, temporary-volume protection and recovery design.

Restore verifies authentication before writing plaintext, then validates SQLite
integrity in a protected temporary target. File fsync precedes create-only
hard-link publication. Existing or concurrently created targets survive. On
unsupported filesystems publication fails; there is no overwrite fallback.
This does not prove directory-metadata durability under sudden power loss.

Retention planning authenticates each explicitly supplied artifact, preserves
the three-calendar-month window and at least the requested minimum of one
verified copy. It returns `retain`/`eligible` paths and never deletes files.
No retention execution is enabled pending owner-data policy approval.

## Evidence-backed quality accounting

`evals/quality-support.json` contains 24 authored synthetic multi-turn cases in
12 families, with four whole families held out. Cases cover corrections, missing
or conflicting evidence, citation overreach, vulnerability triage, alert closure,
metrics, scalar norm/stability claims, time budgets and hardware observability.
They are fixtures, not measured model answers or an exhaustive language benchmark.

`scripts/quality_evaluation.py` binds each attempt to case, answer and selected
evidence hashes. A review labels explicit claims supported, unsupported or
uncertain and names selected evidence. Unknown references, changed bindings,
duplicate reviews and incomplete answers are rejected. Human and agent scores
remain separate; absent review stays null. Failed answers remain in the attempt
denominator. The software validates review provenance/accounting; it does not
automatically determine truth, verify reviewer identity or infer entailment from
citation syntax. `runtime/inference.py` citation checks remain ID checks.

No live answers or human support reviews were collected in this implementation.
No model/prompt/routing change or improved-answer-quality claim is made.

## Timing and promotion boundaries

Diagnostic replies now include separate inference and MCP-parent stage groups.
Inference intervals are adjacent offsets from its own monotonic origin; parent
intervals partition preflight, connection and remaining call/metadata time.
Malformed, missing or backwards intervals are unknown (empty), never zero-filled.
`model_first_text`, screening totals and other overlapping counters remain useful
observations but are excluded from the exclusive sums. Parent call time contains
child work: **never add parent and inference totals**. Existing timing keys stay
compatible; completed streaming frames preserve the new numeric groups.

The benchmark collector retains groups under `clock_stages_ms`. Offline
`scripts/performance_gate.py` checks matched schedules, failed attempts, catalogue
coverage, hash-bound human review, 100-attempt minimum, five-second first-text
mean/p95 and pacing regression. Passing this screen is not deployment permission
or measured-answer quality parity. It always reports `promotion_eligible=false`.
Repeated-run quality reviews of measured answers and controlled live comparison
remain required before choosing a runtime optimization.

No persistent MCP session, weaker preflight, smaller evidence budget or model
fallback was introduced. Live benchmarking and latency optimization remain gated
on quality evidence and a separately authorized measurement window.
