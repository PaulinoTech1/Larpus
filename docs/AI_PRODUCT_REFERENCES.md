# AI product references

Reviewed and cached on **2026-10-09** from official publisher pages. The home
assistant prefers these references; every configured persona can retrieve them.
Full snapshots stay under ignored `data/knowledge/originals`, with hashes in
`knowledge/sources.json`; compact original factual briefs are labelled separately.
These are documentation entries, not cloud clients or connected accounts.

## Subscriptions

| Product | Published monthly USD price | Official reference |
|---|---:|---|
| ChatGPT Plus, including Codex allowance | 20 | [ChatGPT Learn pricing](https://learn.chatgpt.com/docs/pricing) |
| Claude Pro, including Claude Code access | 20 US | [Claude Pro](https://support.claude.com/en/articles/8325606-what-is-the-pro-plan) |
| SuperGrok | 30 | [Grok pricing](https://x.ai/pricing) |
| SuperGrok Plus | 100 | [Grok pricing](https://x.ai/pricing) |

Subscription allowances are not separate API credits or unlimited usage. Region,
taxes, billing channel, rollout and account eligibility can change availability.
Codex/Work share plan usage. Grok Bot uses a persistent hosted computer and is
included with eligible subscriptions, with weekly usage and possible additional
token charges; see [official Bot documentation](https://x.ai/bot).

## OpenAI models

Standard text API USD per **one million tokens**:

| Official API ID | Input | Cached input | Cache write | Output |
|---|---:|---:|---:|---:|
| `gpt-6.1-sol` | 2.00 | 0.10 | 2.50 | 10.00 |
| `gpt-6-astra` | 10.00 | 1.00 | 12.50 | 50.00 |

“Astra 6.0” maps to the published GPT-6 Astra reference, not an invented API ID.
Long-context, speed, batch/flex and regional conditions can alter the base price.
See [Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol) and
[Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) for exact terms.
Both models have dated capability/context/cutoff notes in the local briefs.

## DeepSeek

API USD per **one million tokens**, as reviewed on 2026-10-09:

| Model and period | Cached input | Uncached input | Output |
|---|---:|---:|---:|
| V4 Pro peak | 0.044 | 1.32 | 3.96 |
| V4 Pro off-peak | 0.022 | 0.66 | 1.98 |
| Flash peak | 0.006 | 0.30 | 1.20 |
| Flash off-peak | 0.003 | 0.15 | 0.60 |

The old V4 Flash aliases route to V4.1 Flash (`deepseek-flash`); Pro is
`deepseek-v4-pro`. Peak hours are 01:00–04:00 and 06:00–10:00 UTC on weekdays,
excluding Chinese public holidays. Other hours are off-peak. The archived
[official table](https://api-docs.deepseek.com/quick_start/pricing/) records these
conditions and model capabilities together.

## Meta Muse and Muse Spark

Muse is now identified as **Meta Muse**, a personal AI agent. Meta describes a
cloud Secure VM, browser/connected-app tasks, background work and a separate
Sentinel that approves outbound activity. It has free usage with optional paid
plans; free usage is limited. These are vendor claims, not a local integration.
See [Meta launch](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/).

The owner reported a **1 billion Muse token referral reward** for recommendations.
Secondary reports describe both inviter and eligible new user receiving one
billion tokens after code redemption, with a 48-hour signup window. The linked
[primary announcement](https://x.com/alexandr_wang/status/2100256890559308197)
was inaccessible (403), so the local brief explicitly marks these detailed terms
as not independently primary-source verified. Check the offer in the app before
recommending it on that basis. No referral code is stored or endorsed. The reward
is conditional agent usage, not cash, API credit, unlimited usage or context size.
Code caps and expiry are not guaranteed by the archive.
The discovery trail includes [HuggingNews's announcement attribution](https://huggingnews.com/ai/update-muse-grants-1-billion-token-rewards-for-biggest-ai-launch-since-c-8061d2cf)
and [All Things Muse's redemption description](https://www.allthingsmuse.com/articles/muse-invite-codes/).
Those third-party sites are not imported as approved publisher snapshots, and
their referral codes are not used.

Muse Spark is the **model family**, not the Muse agent product. The reviewed
[Meta model catalogue](https://dev.meta.ai/docs/models) lists Spark 1.3 (recommended),
1.2 and 1.1 with a 1,048,576-token context. Spark 1.3 audio understanding is
incomplete; the catalogue recommends 1.2 or Voice Transcribe for audio.
Standard excludes prompts/completions from training; 1.3/1.2 Contributor variants
permit training for lower prices. Related families are Muse Image, Muse Voice
Transcribe (STT, not TTS), SAM segmentation and self-hosted open-weight Muse
Glimmer. None has been installed or connected to Larpus.

[Meta API prices](https://dev.meta.ai/docs/pricing-rate-limits), USD per million tokens:

| Spark tier | Cached input | Uncached input | Output |
|---|---:|---:|---:|
| Standard 1.3 / 1.2 / 1.1 | 0.15 | 1.25 | 4.25 |
| Contributor 1.3 / 1.2 | 0.002 | 0.10 | 0.20 |

API search adds $2.50 per 1,000 queries; no long-context premium is listed.
Muse agent free/referral balances do not establish API entitlement.

Both **Grok Bot and Muse are agents** with cloud computer workflows. Their
published emphases differ:

| Dimension | Meta Muse | Grok Bot |
|---|---|---|
| Focus | Personal goals, everyday tasks, proactive help | Parallel teammates, collaborative projects, taught routines and scheduled work |
| Compute | Dedicated Secure VM; Sentinel outbound approval | One persistent cloud computer shared by a user's Bots, including files/logins |
| Access/cost | Free usage, paid upgrades; conditional reported referral promotion | Eligible Cursor/SuperGrok/Teams plans include weekly usage; additional token charges |

The comparison uses the [Meta launch](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/)
and [Grok Bot documentation](https://x.ai/bot). These emphases do not prove that
one product cannot perform the other's tasks. Recommendations should consider
actual tasks, eligibility, cost and privacy rather than assume a universal winner.

## Refresh

“Current” means the review date, not live pricing. Offline answers cannot check
today's checkout or account limits. Refresh requires owner review, a deliberate
new checksum pin, index rebuild, sealed-image rebuild and recurring checks.
Use focused questions for comparisons; at most three excerpts fit each request.
Selected references prove the supplied evidence, not every generated inference.
