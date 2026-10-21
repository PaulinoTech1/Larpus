# Failure isolation outline — 2026-10-20

Production update: the failure-isolation-only variant was activated as
`042f91c0a1454887a694c945f49237ad`, retaining `7df2e957751642d6ace4630fa047fe94`
for rollback. See the [deployment record](../FAILURE_ISOLATION_RELEASE_2026_10_20.md)
for the exact scoped source, frozen checks, retained warnings and live API evidence.
Execution profiles and MCP Skills remain unpromoted. The handoff statements
below describe the checkout and selected release before that activation;
their earlier test and deployment limits remain historical evidence.

This is a source outline of the working checkout. It names the station’s layers,
the failure standard already present in code, the boundaries that already stop
a fault, and the seams where one fault still widens. It is documentation for
a later refinement. It does not change runtime behavior, release pins, or the
selected station.

At handoff, selected production remained `7df2e957751642d6ace4630fa047fe94`. Checkout
execution profiles, the prepared Assembly optimized snapshot, and the prepared
Verified overlap snapshot are not the running station. `docs/architecture/security-boundaries.md`
still says “No execution profile exists yet.” That sentence describes the audit’s
starting point. The checkout now has Verified, Ultra Fast, and Diagnostic.
Those profiles were not promoted.

Related records: [module inventory](module-inventory.md),
[dependency map](dependency-map.md), [scorecard](modularity-scorecard.md),
[contracts](module-contracts.md), [execution pipeline](execution-pipeline.md),
[security boundaries](security-boundaries.md). Public codes live in
`runtime/diagnostics.py`.

## Applied in the checkout on 2026-10-20

These edits are in the working checkout. They are not in selected release
`7df2e957751642d6ace4630fa047fe94`, and no candidate was staged or activated.
The station was not started. Tests that ran: `tests/test_failure_isolation.py`
and the nearby gateway, retrieval, skill, diagnostic, knowledge, and scorer
suites, 97 tests, 2 skips. `python -c` through `scripts.complexity.regressions`
reported no complexity regression. The live HUD was not opened. `web/pipeline.js`
already prints `status.notice`, so the new NumPy sentence will show there when
the pipeline control is loaded.

| Fault that was spreading | What the checkout does now | What it does not do |
| --- | --- | --- |
| A corrupt skill was reported as HTTP 400 “Invalid persona or conversation”, as `LARP-EVIDENCE-UNAVAILABLE`, or as an uncaught error on `/api/personas`. | `CatalogRejected` is fault-closed HTTP 503 `LARP-CATALOG-REJECTED` with `scope`. A named skill or persona failure leaves the others available. A skill the persona is not allowed to use stays HTTP 400. | A bad registry document, duplicate id, or extra folder is `scope=catalog` and serves no persona. That case still stops process import. The gateway and the MCP child still do not share memory. |
| Evidence retrieval reloaded the skill catalog, so a catalog fault looked like a library fault. | `knowledge._retrieve` calls `persona_known`, which reloads the catalog with scoped rejections. Catalog exceptions keep `LARP-CATALOG-REJECTED` rather than becoming evidence failures. | Registry-document failures still refuse the request; separate processes can observe different disk states between reads. |
| The first CPU-retrieval miss was stored for the life of the process, and the reason kept up to 200 characters of `str(exc)`. | A client miss is remembered for 30 seconds. The reason is the exception type name. The worker retries an OSError on that timer and retries a content rejection when the index stamp changes. | This is not a retry on every request. A down remote worker costs one status probe per 30 seconds. A content rejection does not reread the index until a file name or mtime changes. |
| An author-catalog read failure cached `{}` for the process. | `author_cite` returns no citation for that call and tries again on the next call. A successful read stays cached. | Citations for that one call are still absent. |
| A failed assembly score fell back to NumPy without saying how long the fallback lasts. | `notice` says NumPy is used until the next scorer retry. `numpy_until` is `retry-30s` for 30 seconds, then the kernel is opened once. A close-score recheck leaves `numpy_until` empty. | A kernel that fails again waits another 30 seconds. It is not retried on every query. |

The broker idle fence, the release rollback, the MCP refusal to call the model directly, and the GPU refusal to answer on CPU stay wide on purpose. Their scopes are named below. Failure containment on the scorecard stays 3 because a registry-document failure and the broker fence still stop more than one request.

## Scoped further in the checkout

Each row is the scope that remains after the second pass. These edits are still checkout-only. Selected release `7df2e957751642d6ace4630fa047fe94` does not contain them.

| Failure | Scope now | What still stops a wider area |
| --- | --- | --- |
| Named skill file: hash, extra file, frontmatter, origin, symlink, or scanner error | `scope=skill`. That skill is omitted. Personas that listed it stay, without that skill. A request for it is HTTP 503 `LARP-CATALOG-REJECTED`. The HUD notice counts `rejected` entries; it does not list them. The live HUD was not opened. | A registry that is not JSON, has the wrong shape, has more than 128 entries, has a duplicate or unnamed id, or has an extra folder is `scope=catalog`. No persona is served. Import still stops the process when that happens or when zero personas remain. |
| Named persona file: bad JSON or invalid fields | `scope=persona`. Other personas stay. `require_persona` reloads on chat, compression, voice, and the persona list, so a skill-less chat sees a repaired or newly rejected file. | The gateway process and the MCP child still do not share memory. They both read the same files on the next request. |
| Retrieval worker cannot open the index | OSError retries every 30 seconds. A content rejection waits until the index directory's file names or mtimes change, then retries. The process stays up. The client still remembers its own miss for 30 seconds. | A content rejection does not re-read a large file on every tick while the files are unchanged. Recovery is not instant. |
| Assembly score or load failure | NumPy for 30 seconds (`numpy_until=retry-30s`), then one reopen. A close-score recheck still does not set that flag. | A kernel that keeps failing is retried every 30 seconds, not on every query. |
| Knowledge or notes manifest rejection | Still fault-closed for that request as `LARP-EVIDENCE-UNAVAILABLE`. The owner record now uses the reviewed literal (`EVIDENCE-REJECTED`) instead of `UNCLASSIFIED`. | The request does not answer without the required index. An absent notes manifest still means no notes. |
| Broker cancellation not confirmed | `snapshot()['scope']` is `broker-admission`. Chat and notes admission stay refused until the idle probe succeeds. | Voice, catalog, and retrieval do not read that flag. The fence was not shortened. |
| Knowledge and retrieval root | Both use `runtime/station_paths.py`. The retrieval worker no longer imports `knowledge` to find the index directory. The seven handoff imports now also use `runtime.station_paths.ROOT`. | The directory is identical. `security_scan` still imports `load_skills` from `runtime.skills`; scan behavior is unchanged. `health` still imports the existing `skills.ROOT` alias outside this handoff's scope. |

A catalog `scope` of `catalog` is the document. A scope of `skill` or `persona` is one entry. The public sentences are different. The exception text is still not copied to the client.

## 1. Station outline

One chat answer is a single generation. There is no runtime critic and no
second model that approves the first. Compression, speech, notes, model
switch, and health are side branches with their own failure owners.

### 1.1 Layers, outer to inner

| Layer | Owner | What it may decide | What it must leave alone |
| --- | --- | --- | --- |
| Browser HUD | `web/app.js`, `web/conversation.js`, `web/voice.js` | When to post, when to commit history, optional speech and teaching text | Server gates. A failed batch keeps the previous transcript. Speech is a separate call. |
| Gateway | `runtime/gateway.py` `Handler` | Peer, Host, Origin, session, body size, route, admission, NDJSON framing | Model bytes, skill execution, direct sockets to Ollama |
| Session | `runtime/auth.py` | Password record, cookie, per-address rate window | Request meaning. A gateway process change requires a fresh LAN login. |
| Host admission | `runtime/inference_admission.py` | Cooperative interactive/background file lock | Broker budgets. A host ticket does not clear a broker fault. |
| MCP client | `runtime/mcp_client.py` | One new child, three allowlisted tools, 940 s bound, stream equality | Direct or cloud inference. Any child failure stays on the MCP codes. |
| Isolation | `runtime/isolation.py` plus `runtime/source_integrity.py` | Fresh fingerprint, WSL/Podman/OCI pins, child argv | Allowing a request because an observation was cached earlier. Validators stay on every profile. |
| MCP server | `runtime/mcp_server.py` | Process-local rate window, call into inference on a worker thread | Shell, filesystem, or network tools for the model |
| Personas and skills | `runtime/agents.py`, `runtime/skills.py` | Local JSON roles, prompt-only registered skills | Tool grants. A skill body is text in the system prompt. |
| Evidence | `runtime/knowledge.py` | Approved index, BM25, optional CPU neighbors, optional derived notes, provenance labels | Answering from the model when required evidence fails |
| Retrieval worker | `runtime/retrieval.py`, `runtime/retrieval_worker.py` | Optional semantic neighbors and rerank over a private Unix socket | Replacing the approved index. Failure keeps the BM25 row order. |
| Scorer | `runtime/scoring_pipeline.py`, native and optimized scorers | Assembly optimized, Assembly original, or NumPy on the same matrix | Authorization. A kernel is a substitute implementation. |
| Model transport | `runtime/local_ollama.py` | Fixed routes on the private broker socket | A caller-supplied URL, a redirect, or a host-mode fallback |
| Broker | `runtime/inference_broker.py`, `runtime/broker_scheduler.py` | Lane from the socket, templates, budgets, queue, deadline, idle fence | A quality score or a profile name granting a slot |
| Output gate | `runtime/dlp.py`, `runtime/text_filter.py` | Entire generated prefix, protected fragments, private quarantine | Approving an isolated token and calling that equivalent |
| Voice | `runtime/voice.py` | Pinned CPU synthesize/transcribe | The text answer. A voice failure can sit beside a finished reply. |
| Diagnostics | `runtime/diagnostics.py` | Redacted owner record and a 16-hex `error_id` | Turning a failed operation into success when stderr cannot be written |
| Release | `scripts/releases.py` | Stage, prepare, drain, activate, rollback | Ordinary chat. A failed candidate restores the previous release. |

### 1.2 One streaming chat

1. The HUD posts persona, history, and an optional skill. Checkout profiles may add a sealed execution label. The label selects observation freshness and diagnostic detail.
2. The gateway checks trust, session, size, schema, and readiness, then takes its lock and an interactive admission ticket.
3. The MCP client starts a new constrained child. Isolation preflight rejects drifted source, image, mount, device, or namespace state.
4. The MCP server checks its own limiter and calls `inference.chat`.
5. Inference resolves the persona, screens messages, and attaches the selected skill prompt.
6. Knowledge verifies the approved database and retrieves passages. CPU retrieval and derived notes are optional enhancements around that index.
7. The broker admits one lane on the pinned model. The model streams frames.
8. Inference releases text only after GPU placement and a DLP check of the whole prefix.
9. The gateway emits NDJSON `done` only for status 200. The browser stores history only after that event and nonempty content.

### 1.3 Side branches

- Compression (`/api/context/compress`) is another model generation. A held or invalid summary keeps the original chat.
- Speech is a second request, or a best-effort attach when `speak` is set. Text remains when the voice worker fails.
- Notes run on their own broker lane. A notes failure leaves that window pending and does not rewrite the chat transcript.
- Model switch is an owner route. It restores the previous model or holds. It is not a chat fallback.
- Health and scans run outside the answer. They do not critique the answer.

### 1.4 Two processes, two copies of the same catalogs

`gateway.PERSONAS` and `inference.PERSONAS` are filled by separate `load_personas()` calls at import, in the gateway process and in the MCP child. `_KNOWN_PERSONAS` records the most recent successful identities but does not bypass loading: `require_persona` and `persona_known` reload the catalogs. A skill-less chat therefore sees a repaired or newly rejected file on its next request. Selecting a skill or opening `/api/personas` also reads the registry and fails closed with `LARP-CATALOG-REJECTED` when the registry document fails. The parent and the child can still disagree if files change between their reads.

## 2. Failure standard

Every failure has one disposition, one scope, and one public shape. A neighbor feature may carry a different disposition in the same response. Voice can be isolated while the text answer succeeds. The diagnostic sink can fail while the original operation stays failed.

### 2.1 Dispositions

| Disposition | Meaning | Caller sees | Use it when |
| --- | --- | --- | --- |
| Reject | The request is outside the contract. | 400, 401, 403, or 404. Conversation unchanged. | Bad JSON, unknown route, failed login, wrong host or origin, unknown persona at the gateway schema check. |
| Hold | A required gate refused this attempt. State that must stay is kept. | 409, 413, 422, 429, or 503 with a stable sentence. | Text filter, DLP, context pressure, admission busy, GPU placement, evidence screening, broker queue or budget. |
| Degrade | An optional enhancement is skipped. A declared weaker result continues. | 200, plus a notice or a missing optional field where that notice already exists. | CPU retrieval to BM25, assembly scorer to NumPy, one optional note excluded, author citation missing. |
| Isolate | A neighbor fails and the primary result stands. | 200 with an attached error field, or a pending side window. | Voice beside finished text, notes window pending, compression failure with the original chat retained. |
| Fault-closed | The operation stops. No second path runs. | The code’s own status. Recovery text says which fallback is forbidden. | MCP child down, broker cancellation unconfirmed, incomplete stream, model-switch failure, required index or scanner failure, present-but-invalid notes manifest. |

Startup-closed is fault-closed at process scope: the process refuses to import or bind. Examples already in code: missing password record (`gateway.main` exits), invalid persona or skill catalog at `load_personas()` during import, LAN bind that is not a matching RFC1918 address.

### 2.2 Scope

Scope is who else is affected. Name it every time. A request-scoped hold must not become the next request’s behavior.

| Scope | Dies with | Already true for |
| --- | --- | --- |
| Request | This HTTP call or this stream | Body schema, text hold, DLP hold, one admission timeout |
| Feature | That side path | Voice, one optional note, author-cite cache miss |
| Process | This gateway, child, or worker until recovery | A ready retrieval engine stays cached; retrieval/scorer misses have 30-second retry state; broker `faulted` waits for an idle probe |
| Catalog | Every persona that shares the registry | Registry-document failures in `skills.load_skills`; named skill failures are scoped separately |
| Deployment | The station until an owner repair | Isolation drift, model-weight mismatch, release activation failure |

### 2.3 Public codes

`diagnostics.CODES` is the closed set. `report` raises on an unknown code. `RECOVERY` is the owner sentence. `failure` returns `DiagnosticError` with a 16-hex `error_id`. Unreviewed exception text, paths, source lines, locals, prompts, and credentials stay out of the client and out of the stderr record.

| Code | Disposition | Scope | Recovery already written |
| --- | --- | --- | --- |
| `LARP-MCP-UNAVAILABLE` | Fault-closed | Request, and the child that failed | Inspect gateway stderr and pins. No direct model fallback. |
| `LARP-MCP-STREAM` | Fault-closed | This stream | Keep the transcript. The partial reply is incomplete. |
| `LARP-INFERENCE-UNAVAILABLE` | Fault-closed | Request | Check broker readiness and the pinned model. No direct or cloud fallback. |
| `LARP-CATALOG-REJECTED` | Fault-closed | `catalog`, `persona`, or `skill`, from the `scope` field | Read `scope`. A skill or persona entry stays unavailable. `catalog` means the registry document failed and no persona is served. |
| `LARP-EVIDENCE-UNAVAILABLE` | Fault-closed | Request | Check the approved index, manifest, and screening. Do not infer without evidence. |
| `LARP-EVIDENCE-NOTE-EXCLUDED` | Degrade | Feature | One optional note failed screening and was excluded. Original records stay. |
| `LARP-NOTES-TRANSPORT` | Isolate | Feature | Current notes window stays pending. |
| `LARP-NOTES-WORKER` | Isolate | Feature | Do not save partial notes JSON. |
| `LARP-VOICE-UNAVAILABLE` | Isolate | Feature | Text remains usable. No cloud voice. |
| `LARP-MODEL-MAINTENANCE` | Fault-closed | Deployment | Inspect the model-operation diagnostic. Recover locally without a fallback model. |

`describe` maps an exact string in `KNOWN_MESSAGES` to a reviewed reason and action. JSON errors, timeouts, permission errors, and connection errors have fixed classifications. Anything else is `UNCLASSIFIED`. `UNCLASSIFIED` means the boundary raised a bare `ValueError`, `OSError`, or `Exception` whose text was never reviewed. It is a standardization gap, not a license to copy `str(exc)` into the client.

### 2.4 Required record for a new or changed failure

Add the failure in the same change as its tests. Fill every line. A missing line means the failure is not yet standard.

| Field | Rule |
| --- | --- |
| Name | Stable sentence the owner can say out loud. |
| Disposition | One of reject, hold, degrade, isolate, fault-closed. |
| Scope | Request, feature, process, catalog, or deployment. Say whether the next request inherits it. |
| Code | An existing member of `CODES`, or a new member added together with `RECOVERY`. |
| Literal | If `describe` should recognize it, add the exact message to `KNOWN_MESSAGES`. Otherwise the owner record stays `UNCLASSIFIED` on purpose. |
| Client shape | HTTP status or NDJSON `error` event. Include `error_id` when `report` ran. Do not include exception text. |
| Neighbor | Name the feature that must still succeed, or state that the whole request stops. |
| Forbidden path | Name the fallback that must not run: direct TCP, cloud model, CPU token generation, a second persona, a skipped validator. |
| Stickiness | Cleared at end of request, cleared by an explicit `reset`, or held until process restart. |
| Test | One case for the failure, one case for the neighbor, one case where the diagnostic sink raises and the operation still fails. |

### 2.5 Rules that keep the standard honest

- A degrade continues only on a path that already documents the weaker result. BM25 and NumPy are those paths. Dropping evidence to go faster is not a degrade.
- A fault-closed path does not gain a fallback because a profile is named Ultra Fast.
- Isolate never writes the failed neighbor into saved chat history as a successful turn.
- Catalog tamper stays visible through rejection counts and scoped refusals. A corrupted named skill is omitted, and requesting it stays fault-closed. A registry-document failure still closes the whole catalog.
- A present invalid notes manifest rejects. An absent notes manifest returns no derived notes. Those two outcomes stay different.
- Clock, trace, and stderr failures cannot flip a rejection into an approval.

## 3. Disposition along the chat path

| Step | Function | Current disposition | Sticky? |
| --- | --- | --- | --- |
| Untrusted peer, host, or origin | `Handler.trusted` | Reject 403 | No |
| Login failure or rate limit | `Auth.login`, `Auth.allowed` | Reject 401 / hold 429 | Rate window is process-local |
| Bad chat body or unknown persona in the schema | `validate_chat_request` | Reject 400 | No |
| Input text held | `TextHeld` in gateway or `inference.chat` | Hold 422, or 503 when the filter itself is unavailable | No |
| Gateway lock or admission busy | `LOCK`, `Admission.interactive` | Hold 409 or 503 | No |
| Child, preflight, or tool failure | `mcp_client.call` / `stream_chat` | Fault-closed `LARP-MCP-UNAVAILABLE` or `LARP-MCP-STREAM` | No, beyond this call. A new child is started next time. |
| Bad execution label | `execution_profiles.resolve` | Reject 400 | No |
| Skill the persona is not allowed to use | `selected_prompt` | Reject 400 | No |
| Catalog reload fails | `load_skills` → `CatalogRejected` | Fault-closed 503 `LARP-CATALOG-REJECTED` with `scope` of `skill`, `persona`, or `catalog` | `require_persona` reloads on chat, including a chat with no skill. |
| Required evidence or a present invalid notes manifest | `knowledge.augment` / `retrieve` | Fault-closed 503 `LARP-EVIDENCE-UNAVAILABLE` | No |
| Optional CPU worker missing or scoring throws inside hybrid search | `knowledge._hybrid`, `retrieval.engine` | Degrade to BM25 order for this call | The miss is cached for 30 seconds, then tried again. A ready engine stays cached. |
| Optional note fails screening | `study_notes` | Degrade: that note is skipped | No |
| Author catalog unreadable | `author_cite` | Degrade: that call has no citation | No. The next call reads the file again. |
| Context over the bound | `ContextPressure` | Hold 413 | No |
| Broker budget, queue, deadline, or unconfirmed cancel | `Scheduler.slot` | Hold 409 / 429 / 503, code preserved when it is one of the known broker codes | `faulted` sticks until a later idle probe succeeds |
| GPU placement not fully on GPU | `stream_reply` | Hold 503. CPU token replies stay disabled. | No |
| Empty, oversized, or schema-invalid model output | `stream_reply` / `release` | Hold 422 or fault-closed 502 `LARP-INFERENCE-UNAVAILABLE` | No |
| DLP or quarantine failure | `dlp.gate` | Hold. Partial text is not a completed turn. | No |
| Speak flag and voice worker down | gateway after status 200 | Isolate. `voice_error` is attached. Text status stays 200. | No |
| Stream exception after headers | gateway stream branch | Fault-closed NDJSON error. Partial reply stays incomplete. | No |
| Diagnostic stderr write fails | `diagnostics.report` | The original failure still propagates | No |

Health `OSError` is fault-closed 503 with the MCP sentence. It does not open a direct model socket.

## 4. Boundaries that already contain a fault

These are working modules. A later refinement should keep their dispositions.

**Optional CPU retrieval.** `retrieval_worker.serve` stays alive when `Engine` init fails, so the container does not exit. It retries an OSError every 30 seconds and retries a content rejection when the index stamp changes, then listens. Until then `call` raises `OSError('Retrieval worker error')`. `knowledge._hybrid` catches that and returns the BM25 order. `knowledge._engine` returns `None` on any exception. `retrieval.engine` remembers a failed open for 30 seconds, keeps only the exception type, and then tries again. A ready engine stays cached. Constrained queries never take semantic-only passages.

**Scorer substitution.** `Pipeline` loads the native and optimized backends independently. A load or score failure records a notice and serves NumPy for 30 seconds, then tries that kernel once. Assembly optimized also treats a close cutoff, including duplicate rows, as ambiguous and uses NumPy for that score only. NumPy itself stays available. This is the clearest replaceable module in the station.

**One bad optional note.** `study_notes` skips a note that fails `screen_optional_evidence`. The code `LARP-EVIDENCE-NOTE-EXCLUDED` describes that degrade. The approved passages remain the evidence.

**Voice beside text.** A voice `OSError` sets `voice_error` and still returns the reply. A voice-only request that fails is 503 with no cloud fallback. Text filtering can still hold a transcript at 422.

**Notes beside chat.** Notes transport and worker failures keep the window pending and refuse partial JSON. The chat lane is a different broker lane.

**Incomplete streams.** The gateway emits `type: error` rather than `type: done`. The browser commits only on done plus nonempty content. There is no automatic second generation through another backend.

**Broker fence.** Failed cancel confirmation sets `Scheduler.faulted`. Later `slot` calls raise `Refused(503, 'cancellation_unconfirmed')` until `verify_idle` succeeds. Disconnect alone is not confirmation.

**Model switch.** Busy or unprepared selection is refused. A failed switch restores the previous model or holds. Ordinary inference does not accept another provider.

**Release.** A candidate that fails preparation does not activate. A candidate that fails activation restores the previous release. The working checkout is not what production runs.

**Diagnostic sink.** `report` swallows `OSError` and `ValueError` from stderr and still returns after the caller’s failure has been built. The sink cannot launder a failure into success.

**Profile label.** Checkout `ExecutionContext` carries profile, interaction, and optional diagnostic base. It cannot carry a URL, an executable, an isolation mode, a security toggle, or a cache-approval bit. Missing context keeps current behavior. Ultra Fast’s snapshot path and Verified’s fresh probes use the same validators.

## 5. Seams where one fault still widens

The “Scoped further” section is the current scope of catalog, retrieval-open, and scorer failures. The notes below keep the limits that were not narrowed.

### 5.1 Registry-document failures still close the catalog

A hash change, ancillary file, bad frontmatter, or bad origin is `scope=skill`, described in “Scoped further.” What follows is the document-level stop. `skills.load_skills` raises `CatalogRejected` for an invalid registry or an unregistered folder. `agents.load_personas` rejects a persona referencing an unknown skill, while retaining personas referencing a known rejected skill with that skill removed. Both the gateway and the inference child call `load_personas` at import; a registry-document failure or zero remaining personas is startup-closed for that process.

That width is the tamper rule. The 2026-10-20 change gives it the name `LARP-CATALOG-REJECTED` on the request path. It does not serve the other personas from a partial registry.

What still closes the whole process:

- Import of `gateway` or `inference` still aborts when `load_personas` raises. That raise now means the registry document failed or every persona was rejected. One bad skill file or one bad persona file does not do this. A separate process was not launched to show the abort.
- Persona field errors use the fixed sentence `Invalid persona fields`. The file name is not in the client body.
- The gateway and the MCP child still do not share memory. Each reloads the files on the next `require_persona` or `load_personas` call.

### 5.2 Retrieval timing

`retrieval.engine` keeps a ready engine until `reset()` or process replacement. A failed open stores the exception type and a retry time 30 seconds later. It does not store `str(exc)`. The worker retries an OSError on that same 30-second timer and retries a content rejection when the index directory stamp changes. Until the socket is listening, callers stay on BM25.

### 5.3 Scorer timing

After a score or load error, NumPy is used until `SCORER_RETRY_SECONDS` (30). The next score then tries the kernel once. `numpy_until` is `retry-30s` while that wait is active. A close-score recheck does not start that wait. A kernel that fails again waits another 30 seconds.

### 5.4 Some different faults still share a sentence

Catalog failure, a malformed conversation, and an evidence failure now have different sentences and codes. These still share a sentence:

- Broker refusals share one sentence. The specific code survives only when it is in a fixed allowlist; other `Refused.code` values become `broker_held`.
- `OSError`, `ValueError`, `KeyError`, and `TypeError` from the model path share 502 `LARP-INFERENCE-UNAVAILABLE`. `CatalogRejected` is caught before that arm so a catalog error is not reported as a missing model.
- Any other evidence `Exception` shares 503 `LARP-EVIDENCE-UNAVAILABLE`. A catalog error raised during evidence is caught first and keeps `LARP-CATALOG-REJECTED`.
- MCP still wraps a child that raises, rather than returns, as `LARP-MCP-UNAVAILABLE` or `LARP-MCP-STREAM`. A child that returns the catalog dict keeps that dict. The outer code stays MCP when the child process itself fails.
- The knowledge and notes manifest literals listed in `KNOWN_MESSAGES`, including “Knowledge database hash mismatch”, are reviewed as `EVIDENCE-REJECTED`. Unlisted exception text stays `UNCLASSIFIED` and is not copied.

### 5.5 Process globals make one request the next request’s policy

These are the mutable cells the dependency map already names. A fault written into one of them outlives the request.

| Cell | Written by | Effect on the next request |
| --- | --- | --- |
| `retrieval._ENGINES` / `_RETRY_NOT_BEFORE` | A ready `engine()`, or a failed open | A ready engine stays. A miss stays for 30 seconds, then one retry. The reason is the exception type. |
| `scoring_pipeline.Pipeline.native` / `optimized` / `error` | A failed score | That kernel waits 30 seconds, then one reopen. `numpy_until=retry-30s` names the wait. |
| `broker_scheduler.Scheduler.faulted` | Unconfirmed cancel | Chat and notes admission stay refused. This fence was left in place. |
| `knowledge._AUTHORS` | The first successful `author_cite` read | A failed read does not write the cache. The next call tries again. |
| `mcp_server.WINDOW_START` / `CALLS` | Each child call | Rate window is per child today. Reusing a child would change the limiter’s lifetime. |
| `gateway.PERSONAS`, `inference.PERSONAS`, `_KNOWN_PERSONAS` | Import, then each `require_persona` or `load_personas` | A request reloads the files. The two processes still do not share memory. |
| `model_routes._CONTROLLER` and `ModelSwitch.state` | Owner switch | A held switch blocks later owner operations until restore finishes |

Request-scoped data stays out of these cells. A profile must not store an allow verdict in any of them.

### 5.6 Shared anchors couple unrelated failures

`runtime.station_paths.ROOT` is the shared path anchor for knowledge, retrieval, DLP, isolation, model evaluation, security scanning, the two owner scripts, and the pipeline route test. The handoff changed imports only, preserving the directory and scanner behavior. The existing `skills.ROOT` alias remains for skills and health. Isolation mode, broker lane, and retrieval worker selection also read process environment. Those variables are deployment settings. They are not client profile fields. A future profile resolver must keep reading them from the process, not from the request.

### 5.7 Remaining owner import cycle

The worker no longer imports `knowledge` for its directory. It loads retrieval
through its own engine loader and uses the shared station root. The remaining
owner-path cycle is:

- `model_backend` ↔ `scripts.releases`. This cycle is on the owner path. A release-import error can surface as a model-maintenance failure, and the reverse.

Split them only when a test can load one side without the other. Do not move the integrity decision to get a cleaner graph.

## 6. What a profile is allowed to change

Verified, Ultra Fast, and Diagnostic share admission, skill and index checks, isolation validators, broker policy, GPU placement, DLP, and stream completeness. Ultra Fast may use the fresh batch observation path. Diagnostic may record numeric spans on top of a Verified or Ultra Fast base. A profile must not:

- select host inference or the owner raw-speed benchmark,
- skip a validator because a probe was slow,
- shrink the evidence budget, drop DLP, or swap the persona,
- turn on CPU token generation when GPU placement fails,
- reuse an MCP session or an allow verdict across requests,
- treat an optional CPU or assembly miss as permission to answer with no evidence.

The mode-equivalence matrix in `security-boundaries.md` is still the right test list for a future change: the same allow and deny results for bad tools, bad skills, partial observations, wrong images, incomplete scans, protected text, failed cancellation, and cut streams.

## 7. Owner plane

Owner failures use the same five dispositions.

| Operation | Disposition | Scope |
| --- | --- | --- |
| `releases.stage` / `prepare` finds drift, a scan-inventory change without a source-pinned review, or a failed test | Fault-closed. The candidate stays unactivated. | Deployment. The selected release keeps serving. |
| `activate` fails readiness | Fault-closed, then the previous release is restored. | Deployment |
| Explicit `rollback` | Fault-closed return to the recorded previous release. | Deployment |
| Model switch cannot verify GPU or context | Fault-closed `LARP-MODEL-MAINTENANCE`. Restore or hold. | Deployment |
| Quarantine or DLP storage cannot be written | Hold the output. | Request |
| Password file missing at gateway start | Startup-closed. | Process |

A scan finding whose count changed is a review event. The review names the old count, the new count, and the source hashes. It does not delete the warning to make preparation succeed.

## 8. What remains for a later refinement

Failure containment stays at 3. A registry-document failure and the broker fence still stop more than one request. No dimension is at 5.

Done in this checkout:

1. Named skill and persona failures carry `scope`. Registry-document failures are `scope=catalog`.
2. Chat, compression, voice, and the persona list reload the catalog. Knowledge manifest literals are reviewed.
3. A retrieval client miss waits 30 seconds. The worker retries IO on that timer and retries a content rejection when the index stamp changes.
4. A failed scorer waits 30 seconds, then reopens once.
5. Knowledge and retrieval take their root from `station_paths`. The worker does not import `knowledge` for that path. The seven handoff imports now also use `runtime.station_paths.ROOT` for the identical directory.

Left wide on purpose: broker admission until the idle probe, no direct model fallback, no CPU token replies, release rollback, and a present invalid notes manifest. Those scopes are named in the scoped table.

Out of scope until an owner asks: MCP session reuse, a runtime critic, a retrieval rewrite, a five-second latency plan, and any change that turns a fault-closed path into a degrade.

## 9. Evidence limits

### Handoff verification on 2026-10-20

Before edits, the Windows process inventory contained no Python gateway, the
recorded PID 67244 was absent, and ports 8080 and 11434 had no listener. The
station was not started or stopped. After testing those ports were again free;
`active.json` still selected `7df2e957751642d6ace4630fa047fe94`.

The original `tests.test_mcp.StdioTests.test_real_child_chat_with_mock_loopback_ollama`
failed with HTTP 200 instead of 422. Its mock now matches the user text before
the appended `LOCAL_REFERENCE_DATA` block. The test then passed, including
HTTP 422, no fixture text in the public response, the fixture in the incident
file, and deletion of only that synthetic incident. The existing occupied-port
skip is unchanged; the test did not contact a real Ollama.

Ran:

```text
python -m unittest tests.test_dlp tests.test_dlp_ci_overrides tests.test_isolation tests.test_isolation_snapshot tests.test_model_selection tests.test_source_integrity tests.test_execution_modularity tests.test_broker_scan_review tests.test_pipeline_routes tests.test_mcp tests.test_failure_isolation tests.test_skills_health tests.test_skill_resources tests.test_gateway tests.test_assembly_pipeline tests.test_retrieval_worker
```

That invocation ran 100 entries: 97 passed, two skipped, and one loader error
for the additional `tests.test_execution_modularity` module, whose sibling
imports require the tests directory on the Python path. Reran
`python -m unittest tests.test_execution_modularity` with `PYTHONPATH` set to
the checkout's tests directory: all four tests passed. Across the resolved
modules, 103 actual tests ran: 101 passed and two skipped. The required MCP
DLP test was not skipped.

`python scripts/complexity.py check` passed (758 functions, 105 modules), without
changing the baseline or new-function cap. A direct import check confirmed the
edited runtime modules share `station_paths.ROOT` and that its path equals the
existing skills root. Both edited owner scripts passed AST parsing; they were
not executed. `git diff --check` passed.

The full suite, static security scanner, latency screen, live station, and
rendered HUD were not run. No release was staged, prepared, activated, or
changed; no commit or push was made. Existing frozen scan receipts and their
reviewed warnings were not modified. Failure containment remains 3; no
dimension is 5. Unrelated working changes were preserved.

### Re-check after the handoff edits

The checkout already contained the seven `station_paths.ROOT` imports and the
MCP mock change. This re-check did not stop the running gateway. At the start,
port 8080 was held by pid 27572 for selected release
`042f91c0a1454887a694c945f49237ad`, and port 11434 had no listener. After the
tests, pid 27572 was still listening on 8080 and 11434 was free again.

`python scripts/complexity.py check` passed: 758 functions, 105 modules. The
baseline and new-function cap were not changed. `station_paths.ROOT` equals
`skills.ROOT` (`E:\speedzone_MS\LARPUS`). `runtime/health.py` still imports
`skills.ROOT`; that alias was outside this handoff.

From the checkout root:

```text
python -m unittest tests.test_dlp tests.test_dlp_ci_overrides tests.test_isolation tests.test_isolation_snapshot tests.test_model_selection tests.test_source_integrity tests.test_broker_scan_review tests.test_pipeline_routes tests.test_mcp tests.test_failure_isolation tests.test_skills_health tests.test_skill_resources tests.test_gateway tests.test_assembly_pipeline tests.test_retrieval_worker
```

That run reported 100 tests, 2 skipped, exit 0. The output did not contain the
occupied-port skip, so the MCP DLP case ran against the loopback mock. With
`PYTHONPATH` set to the checkout and its `tests` directory,
`tests.test_execution_modularity` reported 4 tests, exit 0. The full suite,
scanner, latency screen, and rendered HUD were not run. No release, commit, or
push was made.

The scoped section names what was tested. This document does not rerun the station, the scanner, the latency screen, or a live HUD. It does not claim the frozen release `7df2e957751642d6ace4630fa047fe94` contains these checkout edits. A bad registry at import was not launched as its own process.

`describe` still returns `UNCLASSIFIED` for raises whose text is not an exact reviewed literal. Knowledge and notes manifest messages listed in `diagnostics.py` are reviewed. Other bare raises are not. The standard in section 2.4 is the bar for closing each one.
