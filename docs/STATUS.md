# Operational status

## 2026-10-25 current station and checkout snapshot (20:24 EDT)

This is a read-only observation, not a new release or quality acceptance. Production
runs from frozen release `6200bb30d68348f080f2c1c723ff2fb6`, selected on
2026-10-24; `python scripts/releases.py status` reports it running with no pending
cutover. Release `346773e17fd54b7784fd3148b07a4b0e` is retained as previous.
The recorded gateway PID is 35916. The local `/api/health` response reports
`larpus3.8:27b-q4` online on GPU, and `/api/model-selection` reports
`larpus-3.8` ready with no switch in progress. These endpoint checks do not
measure answer quality, GPU headroom or reboot persistence.

The saved health report (generated 20:24 EDT) has all required checks passing,
including local skills, MCP surface, MCP Skills, model GPU placement, DLP and
voice. Overall health is **degraded** because the selected release's saved scan
receipt is `warning`: 70/70 targets complete, one warning target. This review
did not rerun the scan or independently exercise chat, voice or a live MCP Skills
protocol client. The selected index reports 413 documents and 76,850 passages;
the release contains 69 hash-checked local prompt skills. Its MCP server source
registers the read-only Skills extension. Discovery does not select a skill or
grant execution rights. See [skills](SKILLS.md) and the historical
[MCP Skills acceptance report](MCP_SKILLS_ACCEPTANCE_2026_10_19.md).

The NVIDIA 621.01 update and selected release's read-only WSL driver mount are
documented in [the October 24 update](UPDATES.md#2026-10-24-nvidia-62101-driver-maintenance-and-measured-http-run).
That update records a successful GPU-resident HTTP run and a descriptive timing
comparison, not a driver-only speedup. The retained prior release still pins the
old driver package; a working rollback under 621.01 has **not** been verified.
Do not treat the release manager's ordinary rollback as a tested driver-recovery
path. The owner status journal reports automatic recovery disabled and unarmed;
backups remain synthetic-only.

The checkout is on `feat/habit-source-and-broker-check` at `e64c9b6` with
uncommitted work. Checkout files are not automatically served. Current
development/evaluation state:

| Work | State and limit |
| --- | --- |
| Prompt-only v2 | Prepared release `f46146f28d1742ec87acc4e157322ed3`; not activated. Heuristic dev gains need blinded human review and broader acceptance. |
| QLoRA pilot1 | Trained and evaluated offline against an NF4 base; shelved and rejected for activation after heuristic regressions. It was not exported or served. The owner's blinded review and independent locked tests are outstanding; Grok-derived training rights are unresolved. See [decision record](DECISIONS.md). |
| MTRAGEval-inspired local probes | A/B/C harness and five public synthetic smoke cases exist only in the checkout. The active frozen release lacks `runtime/rag_eval.py`, so the A/B probe cannot run there. Catalog validation and seven focused unit tests passed on October 25; no model-backed A/B/C evaluation or human scoring was performed in this status review. See [local protocol](MTRAGEVAL_LOCAL.md). |
| MCP Skills | Implementation and registry are in the selected release; saved health verifies declaration and resources. The October 19 acceptance work had mixed timing and unresolved human quality review. This status review did not repeat a live protocol handshake or performance comparison. |

The next quality investigation can use the local MTRAGEval-inspired A/B/C split
to distinguish retrieval, fixed-evidence generation and end-to-end failures.
Its five smoke cases cannot establish a system-wide quality score. Any live A/B
probe needs a separately prepared and authorized release containing the evaluator;
that would be a later change, not an effect of this documentation update. Earlier
sections below are dated historical snapshots.

## 2026-10-21 active recovery/owner tools release

Selected `b6dffca22d244953acb3a8574c232e69` is running; previous
`042f91c0a1454887a694c945f49237ad` is retained and no cutover is pending.
Required readiness and idle broker checks pass. The same 11 reviewed MCP scan
warnings keep health degraded. Model/CPU voice images and start times match
the pre-update snapshot. Recovery remains disabled; backups synthetic-only.
See [activation evidence and limits](RECOVERY_ACTIVATION_2026_10_21.md).
Earlier sections are dated historical snapshots.

## 2026-10-21 prepared candidate

Recovery/owner tools candidate `b6dffca22d244953acb3a8574c232e69` is prepared,
not active. Selected `042f91c0a1454887a694c945f49237ad`, previous release and
gateway/model/voice identities remain unchanged. All 70 fresh scan targets
completed with the same 11 reviewed MCP warnings. No supervisor was launched;
backups remain synthetic-only. See the [preparation evidence](RECOVERY_PREPARATION_2026_10_21.md).
The sections below are dated historical snapshots.

## 2026-10-20 owner snapshot and candidate tooling

The selected-release pointer currently names `042f91c0a1454887a694c945f49237ad`,
with previous `7df2e957751642d6ace4630fa047fe94` and no pending cutover in the
read-only snapshot. Saved health reports required checks passing and the retained
scan warning. This is saved evidence, not a new answer, microphone or security test.
Recovery and encrypted-backup tooling are still worktree candidates, not active
production features. The final death-count review is accepted; production
observation, installation and arming have not occurred.

Use `python scripts/owner_status.py` from the candidate worktree for one bounded
owner summary. It distinguishes selection, prepared receipts, checkout/worktrees,
saved readiness, scan warnings and recovery holds. See
[owner operations](OWNER_OPERATIONS.md) for evidence limits and verification.
The October 11 table below remains a historical snapshot, not the latest selection.

Dated snapshot verified on 2026-10-11. This page is the current deployment record for that date; older verification entries are historical observations. Check `python scripts/releases.py status` and station health for later state. Editing or committing this page does not deploy code.

| Item | Verified snapshot |
| --- | --- |
| Active frozen release | `9d76eed753ad4ec9901c8b988e961248`, running |
| Retained previous release | `fb20ec0c6bc0419dbc6a3b298116820d` |
| Model | `qwen3.5:27b-q4_K_M`; health placement check passes |
| Context / normal response limit | 131,072 / 1,024 tokens; 262,144 remains a target, not the deployed setting |
| Personas / authored skills | 12 / 69 |
| Approved indexed library | 404 source IDs / 76,660 passages, counted from the deployed index |
| Access | Local HTTP password bypass; home-LAN HTTPS with password, rate limits and subnet checks |
| Required health | All required checks pass; overall degraded only for reviewed static warnings |
| Scan evidence | 70 complete targets; 69 clean skills; 11 reviewed MCP warnings retained |
| Nightly notes | Restarted through the existing task and confirmed saving new progress; exception ends 2026-10-12 10:00 Eastern |
| Crash investigation | Earlier Windows bugcheck cause unresolved; restart success is not root-cause evidence |
| CI | Public-only hosted workflow authored in checkout; no GitHub run or branch protection verified yet |

The active snapshot includes source chronology/provenance, complexity tracking, verbose diagnostics and the Stegdetect evaluation tool. Detector results remain small authored synthetic measurements, not production false-positive/negative estimates. Read [deployment process](UPDATES.md), [interaction consequences](INTERACTION_CONSEQUENCES.md), [evaluation limits](STEGDETECT_EVALUATION.md) and [CI scope](CI.md).

Verified post-activation observations: HTTP chat 200, completed NDJSON stream, CPU speech synthesis, local persona access without password and CA-validated LAN unauthenticated rejection (401). Physical microphone and second-device acceptance were not performed. The private original data, minidump and numeric logs remain ignored. No durable crash-cause conclusion, filled-context quality guarantee or independent security certification is claimed.
