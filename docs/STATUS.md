# Operational status

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
