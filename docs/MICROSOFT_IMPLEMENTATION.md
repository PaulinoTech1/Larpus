# Microsoft implementation references and LARPUS conversation controls

Reviewed and snapshotted 2026-10-09. Eleven public Microsoft Learn articles and five locally authored briefs are in the shared screened reference index. Every persona can read them; System Administrator and IT/Cybersecurity LARP Coach prioritise this material and expose five implementation skills.

| Local reference | Official source |
| --- | --- |
| `ms-intune-planning` | [Microsoft Intune deployment planning](https://learn.microsoft.com/en-us/intune/fundamentals/planning-guide) |
| `ms-intune-windows` | [Microsoft Intune Windows deployment](https://learn.microsoft.com/en-us/intune/fundamentals/platform-guide-windows) |
| `ms-intune-enrollment` | [Microsoft Intune enrollment guide](https://learn.microsoft.com/en-us/intune/device-enrollment/guide) |
| `ms-entra-ca` | [Microsoft Entra ID Conditional Access deployment](https://learn.microsoft.com/en-us/entra/identity/conditional-access/plan-conditional-access) |
| `ms-entra-emergency` | [Microsoft Entra ID emergency access accounts](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/security-emergency-access) |
| `ms-azure-landing` | [Microsoft Azure landing zone design areas](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/landing-zone/design-areas) |
| `ms-azure-rbac` | [Microsoft Azure RBAC best practices](https://learn.microsoft.com/en-us/azure/role-based-access-control/best-practices) |
| `ms-m365-deployment` | [Microsoft 365 enterprise deployment](https://learn.microsoft.com/en-us/microsoft-365/enterprise/setup-overview-for-enterprises?view=o365-worldwide) |
| `ms-bitlocker-overview` | [Microsoft BitLocker overview and edition requirements](https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/) |
| `ms-bitlocker-recovery` | [Microsoft BitLocker recovery overview](https://learn.microsoft.com/en-us/windows/security/operating-system-security/data-protection/bitlocker/recovery-overview) |
| `ms-intune-bitlocker` | [Microsoft Intune BitLocker encryption deployment](https://learn.microsoft.com/en-us/intune/device-configuration/endpoint-security/encrypt-bitlocker-windows) |

## Implementation skills

- Intune rollout: inventory, enrollment, compliance, apps, pilot rings and support.
- Entra identity rollout: role boundaries, emergency access, report-only Conditional Access and verification.
- Azure landing zone: identity, subscriptions, networking, governance, scoped RBAC and recovery.
- Microsoft 365 rollout: identity and domains, workload dependencies, pilot, migration and handover.
- BitLocker deployment & recovery: supported editions/hardware, escrow, recovery validation and staged policy.

These are local-authored, SHA-pinned, prompt-only skills. Existing five exclusive specialist skills per role remain. The five Microsoft skills are additionally shared by the two implementation roles; no downloaded skill is installed. Total registry: 69. Proposals do not execute commands or access a tenant. No new credentials, model access, ports or volume mounts are required.

## Local preparation and refresh

Official URLs are individually allowlisted in `scripts/prepare-knowledge.py`; only the reviewed Microsoft 365 URL may include its exact view query. Redirects remain refused. HTTPS, HEAD type/size checks, bounded downloads, pinned hashes, active HTML removal and per-passage screening apply. Raw snapshots live in ignored `data/knowledge/originals`; the runtime reads only the pinned immutable SQLite index. Microsoft retains copyright; review the source terms before redistributing snapshots.

To rebuild from approved cached bytes: `python scripts/prepare-knowledge.py --reuse-research`. Missing newly reviewed sources can be fetched owner-side with `--fetch-reviewed --reuse-research`. Existing pinned sources are deliberately not silently refreshed; review the URL/content, update the approved pin and rebuild for a new snapshot. Never change the active frozen release. Use the staged release procedure in [UPDATES.md](UPDATES.md).

Microsoft cloud services need connectivity when an owner actually deploys them elsewhere. LARPUS remains offline and only coaches from its local snapshots. Windows 11 Home device encryption is distinct from enterprise BitLocker policy management: the documentation does not establish encryption or Intune enrollment on this station. Recovery keys and tenant secrets should never enter chat.

## Conversation and context meter

Changing skill applies the new prompt to the next request without clearing visible messages or browser history. Changing persona also keeps the chat, resets the skill dropdown to Persona only, and uses the new role on the next turn. The selected skill must still be allowed by that persona. In-flight requests disable both selectors. RESET explicitly clears the conversation and meter. History remains memory-only; page reload/closing the tab loses it, and the existing 38-message session guard remains.

The cyan HUD bar shows **latest completed request** input plus output token counts returned by Ollama, against the configured 4,096-token context. Input includes persona, selected skill, defenses, retained conversation and local evidence; output is the generated reply. The request asks for up to 1,024 output tokens. It is not an estimate of the entire visible conversation, a continuously updating tokenizer or VRAM measurement. Before the first measured reply it says No measurement yet. Skill/persona changes leave the previous measured result labelled as the latest request until a new reply finishes.

The gateway still drops whole oldest user/assistant pairs to satisfy its byte budget before inference. The meter reports these omitted messages while retaining them in the visible transcript. Ollama context truncation, if any, is separate from this reported gateway omission count. Token telemetry includes counts only, never prompt or private source text, and is attached only after successful output screening.

## Character

LARPUS is an original eccentric British technical aide and a playful home-station parody. Replies lead with useful answers; occasional theatrical metaphors and dry wit add character. It should challenge flawed assumptions, impossible promises and risky shortcuts, explain the reason and offer a practical alternative. Pushback targets the plan rather than the person. Serious incidents and sensitive situations omit jokes. Role-specific expertise, evidence, uncertainty and sandbox boundaries take precedence over performance. This changes dialogue style, not the underlying CPU voice model.
