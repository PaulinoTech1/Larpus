# Six improvements — implementation record

2026-10-21 update: the scoped production candidate is now prepared, not activated.
Source commit was authorized separately. See [preparation and retained failures](RECOVERY_PREPARATION_2026_10_21.md).
Earlier entries below remain dated implementation evidence; their staging/commit
status is historical. Recovery remains disabled and backups synthetic-only.

Worktree: `E:\speedzone_MS\LARPUS-worktrees\recovery-supervisor`.
Native execution; source remains uncommitted. Serving frozen release is separate.

## 1. Recovery acceptance

Independent `/root/death_count_review` accepted final `_stored_deaths` alignment:
19 focused tests plus 864 disposable observation sequences and simulated watch
restart; no launches. Same/new identity, healthy, busy, held and reused cases
covered. The original final-alignment review gate is closed. Production
observation, installation, arming and broader live acceptance remain unperformed.
See `RECOVERY_EXECUTION_LEDGER_2026_10_20.md` for the prior review history.

## 2. Encrypted restore workflow

New `scripts/backup_store.py` provides versioned AES-256-GCM snapshots of committed
SQLite state, protected staging, bounded reads and time, private plaintext file
permissions and create-only publication. It never overwrites an existing or
concurrently published destination. Wrong keys, changed ciphertext, failed
publication and malformed formats refuse recovery. Retention is an authenticated
plan, not deletion: three calendar months and at least one verified copy.

Owner chose `D:\LARPUS-Backups` and explicitly kept operation synthetic-only
pending key custody. No owner data or persistent keys were read/written.
Successful D: rehearsal preserved IDs 1 and 2 (two committed records), restored
into a separate directory in 2.688 seconds and cleaned up that run's files.
This time is a tiny-fixture observation, not a recovery-time guarantee.

An initial rehearsal failed cleanup because SQLite context managers commit but
do not close connections. Explicit closing fixed that defect. The failed run is
retained in the record. Exact initial fixture residue remains because automatic
approval review blocked recursive cleanup as policy-disallowed. See
`OWNER_OPERATIONS.md`; no cleanup success is claimed for that failed run.

Limits: 64 MiB database bound; no power-loss proof or secure deletion; hard-link
publication requires filesystem support. Plaintext temporary snapshots exist
inside protected staging. No owner-data backup/restore or scheduled retention.
Optional cryptography dependency was already installed; a separate owner/test
requirement pins that version without changing shared runtime dependencies.

## 3. Answer support evidence

24 synthetic multi-turn cases in 12 families (four whole families held out),
covering corrections, unsupported premises, citations, uncertainty, security,
metrics, norms, conflicting sources, time budgets and hardware observations.
Review accounting binds case, answer and evidence hashes, keeps human/agent
scores separate, refuses stale/duplicate/unknown review bindings and incomplete
answers, and preserves missing reviews as null. No runtime model/prompt/routing
change. No live answers generated or improved quality demonstrated here.

## 4. Owner status

Read-only `scripts/owner_status.py` finds the real owner release store via Git
common directory and reports selected, prepared receipts, checkout/worktrees,
feature file presence, saved readiness, scan age/completeness/warning targets
and recovery holds. No WSL boot, scanner, live service probe or state mutation.
Legacy producer-less saved passes are `reported-ready-unbound`. Snapshot found
selected `042f91c0a1454887a694c945f49237ad`, no pending cutover, passing required
saved checks and retained scan warning. Old STATUS table is labeled historical.

## 5. Shared verification

`python scripts/verify.py` / `npm.cmd test` runs complexity, isolated Python,
the shared 11-suite UI manifest, broker prompt pins and the offline quality
catalogue. CI reuses it, retaining CI-only public inventory and evaluations.
Failure stops subsequent gates. The existing isolated runner keeps its direct
complexity guard. Recovery fixture Node execution now discovers the platform
executable. Exact process fixture uses Windows CIM and is explicitly Windows-only;
POSIX permission changes were reviewed statically on this Windows host.

## 6. Quality-gated performance investigation

Separate diagnostic inference and MCP-parent clock groups now survive completed
HTTP streaming and the benchmark collector. Adjacent monotonic inference stages
exclude overlapping model-first-text and screening counters. Parent call time
contains child work and must not be added to child totals. Invalid or missing
intervals are unknown. No persistent connection, weakened security or latency
optimization was enabled.

Offline timing admission requires matched schedules, all failures in denominators,
full human-reviewed quality catalogue coverage, 100 attempts, complete pacing
and first-text measurements, mean/p95 <=5 seconds and bounded pacing regression.
It never grants production promotion or establishes measured-answer quality parity.
Live answer review and latency benchmarking remain pending a separate window.

## Independent final review and regressions

`/root/six_improvements_review` found two concrete P2 issues: one pacing sample
could represent 100 answers, and POSIX publication could expose mode-0644 plaintext.
Both reproduced in failing tests, were fixed, and passed ten focused gate/backup
tests on re-review. Reviewer accepted both fixes; POSIX behavior was reviewed
statically, not executed on a POSIX machine. No reviewer touched production.

Source inventory: new owner modules fall inside the release payload's recursive
`scripts` inventory and would be payload-hash checked by ordinary preparation.
Runtime modules and public evaluation JSON are in the existing integrity scope.
No frozen receipt/pin or reviewed warning inventory changed; no new static scan,
release stage or preparation is claimed. Optional owner/test requirements remain
checkout provisioning inputs, not an agent dependency installation.

First integrated pipeline: 550 Python tests passed, four skips; all 11 UI suites,
prompt pins and quality catalogue passed. Later review/transport/status changes
require the final run recorded below; the earlier result is not reused for them.

The next full run reported 556 tests, four skips and one error: the existing
`ci.UI_TESTS` compatibility export had been removed during consolidation. It
was restored from the shared verifier, preserving one manifest; nine related
tests passed. The failed full run remains `verification-final.log` and is not
relabeled successful. The confirmation run is separate.

Final evidence is retained in ignored `data/six-improvements/verification-confirmed.log`,
`backup-rehearsal.json`, `owner-status.json` and the execution ledger. Failed RED
assertions were observed before each new behavior; function limits were not raised.

Confirmation passed: **556 Python tests, four Windows privilege-related skips,
374.005 seconds**, all **11 UI suites**, broker prompt pins and the 24-case
quality catalogue. Complexity passed at **940 functions / 117 modules** without
allowance changes; whitespace and public tracked-file inventory checks passed.
The catalogue still reports human support null: fixture validation is not answer
quality evidence. No new static scanner or live measurement ran.

Capture note: PowerShell `*>` redirection returned wrapper status 1 for the
confirmation capture despite the inner fail-fast verifier reaching its final
success branch. A separate zero-exit Python stderr probe reproduced that exact
shell behavior; explicitly checking native `$LASTEXITCODE` returned 0. The raw
test summaries and all 11 UI/pin/catalogue checks remain the evidence. Structured
`verification-summary.json` records this distinction rather than hiding it.

## Remaining owner decisions and gates

- Recovery-key custody and offline key recovery; owner-data storage objectives.
- Owner-data backup/restore rehearsal (none performed).
- Human claim-support reviews and live answer-quality comparison (none performed).
- Controlled live latency experiment and selection of an optimization.
- Production observation/installation/arming/deployment (none performed).
- Separate authorizations for later commit/push or release promotion.
