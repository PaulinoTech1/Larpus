# Execution pipeline and stage classification

Baseline inspection paragraphs below describe the pre-implementation checkout.
The implemented-profile section and 2026-10-20 report supersede earlier timing
status; historical Date.now/no-new-trace observations are not the final result.

## Ordinary streaming request

1. [web/app.js `chat.onsubmit`](../../web/app.js) merges optional user-level
   memory/teaching guidance, performs compression if needed, and posts persona,
   history and optional skill. There is no execution-profile field today.
2. [gateway.Handler](../../runtime/gateway.py) checks peer/Host/Origin, LAN session,
   API rate/route/body schema and readiness/draining. It validates persona/history
   and acquires its lock/cooperative interactive ticket.
3. [mcp_client.call_async](../../runtime/mcp_client.py) builds a fixed, environment-
   constrained child, which runs fresh [isolation.preflight](../../runtime/isolation.py).
   It opens a new SDK stdio session and calls one of three allowlisted tools.
4. [mcp_server.chat_local](../../runtime/mcp_server.py) applies its process-local
   limiter and invokes [inference.chat](../../runtime/inference.py). Streaming
   progress is returned to the gateway only through the approved callback.
5. Inference selects a dictionary persona, constructs/screen-checks messages and
   selected skill, validates context, and calls [knowledge.augment](../../runtime/knowledge.py).
   The latter verifies the approved database, retrieves passages/derived notes,
   classifies trust/provenance, and optionally uses the CPU retrieval worker.
6. Inference selects the approved active model. [local_ollama](../../runtime/local_ollama.py)
   uses the private chat socket. [inference_broker](../../runtime/inference_broker.py)
   checks exact templates/model/options/lane, and [Scheduler.slot](../../runtime/broker_scheduler.py)
   enforces budgets, queueing, preemption/deadline and required idle fencing.
7. The model streams frames. Inference waits for release boundaries and checks
   GPU placement and the entire accumulated prefix using [dlp.gate](../../runtime/dlp.py).
   Later rejection stops further release; earlier partial output is not treated
   as a completed conversation.
8. Inference gates final content and source previews, adds context usage and
   citation-identifier consistency, then returns structured completion. The
   gateway emits NDJSON `done`. The browser commits history only after valid done
   plus nonempty content; speech is a separate client/worker operation.

Ordinary chat has one main answer generation, not a model-based router/critic.
Model status requests and a required one-token scheduler fence may occur too.
Client-requested context compression may add separate model generations; that is
not a redundant answer-quality evaluation. No new trace was collected here.

## A / B / C classification

| Category | Existing work | Profile decision |
| --- | --- | --- |
| A: mandatory runtime enforcement | Host/origin/auth/session, request/tool/role bounds, source/skill/index verification, input/reference scanning, sandbox/OCI checks, fixed transport, broker policy/budgets/fencing, GPU placement, DLP/quarantine and stream completeness | Keep in every profile; failure holds/rejects. A profile cannot select owner raw-model transport |
| A: trust/compatibility contracts | Selected system/skill bytes, provenance/derived-note labels, context limits, explicit model selection, transcript/compression validation | Retain; no automatic smaller context, weaker evidence or hidden persona substitution |
| B: optional retrieval implementation | Semantic neighbors/reranker and assembly scoring, with existing BM25/NumPy failure behavior (`knowledge._engine`, `retrieval.engine`, `Pipeline.score`) | Preserve current settings in comparative modes; being optional on failure is not permission to remove evidence for a speed claim |
| B: user-requested optional features | Speech, teaching, user memory and compression interactions | Existing explicit controls remain; modes must not silently turn off a requested capability |
| B: optional runtime answer critic or multi-persona deliberation | None found in `inference.chat`, `mcp_server.chat_local`, `agents.messages_for` | No evaluator to disable, and no model-call saving can be claimed for disabling one |
| B: diagnostics/identifier analysis | Numeric timing and citation identifiers already collected; health monitoring separate | Preserve existing cheap metadata; detailed new traces can be explicitly opt-in and measured. Citation identifiers are not a truth evaluator |
| C: development/maintenance testing | unittest suite, UI contracts, companion catalog, static scans, performance harnesses, namespace behavior probes | Retain tests. They are not synchronously run for each chat. Health can trigger scans after source changes in a background monitor |
| Outside production profiles | Owner raw Ultra Fast benchmark and direct model lifecycle commands | Owner-authorized experimental/maintenance surface only, never a secure profile implementation |

## Implemented checkout profile boundary

Shared flow: resolve profile/interaction, unchanged mandatory admission/checks,
then shared inference/stream/release. A profile selects fresh observation
acquisition and optional diagnostic detail, not a parallel broker or security
toggle. execution_profiles.resolve validates Verified/Ultra Fast/Diagnostic at
host and child boundaries. Selected frozen production still lacks these controls.
Teaching accepted/trial, scorer selection and model selection are separate.

## Timing definitions and uncertainty

Existing `mcp_client` timings cover preflight/connect; `inference.chat` times input,
retrieval and model selection; `stream_reply` records first model frame and first
checked text. First frame can be empty. `first_checked_text` is nested in the
inference interval, not an additive independent stage. The browser measures from
submit using Date.now before compression/HTTP and updates its display on text.
Sources: [MCP client](../../runtime/mcp_client.py), [inference](../../runtime/inference.py),
[HUD](../../web/app.js), [metrics](../../scripts/performance_metrics.py).

The secure owner-loopback comparison completed 100 attempts/profile. Ultra Fast
mean/p95 was 5.718/7.980s and missed the five-second goal; it was not activated.
See [measurement and quality scope](../EXECUTION_PROFILES_PERFORMANCE_2026_10_20.md).
Diagnostic also records monotonic DOM update/frame opportunity, not physical
paint. Rendered LAN acceptance remains untested.
The attachment's approximately 6.00/7.34 s and rejected 4.869 s figures are
preliminary references, not reproduced measurements. Existing documented runs
use different workloads and must remain separately identified. The new requested
mean/p95 <5 s goal is stricter than the earlier p90 proposal; it is a target,
not a hardware guarantee.
