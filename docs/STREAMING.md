# Local sentence streaming

The HUD uses `POST /api/chat/stream` rather than waiting for a complete reply and
its complete WAV. Ollama generates locally on the GPU; the isolated MCP agent
stages and inspects generated prefixes before releasing complete sentences.
MCP progress notifications carry approved text over the existing stdio channel.
The gateway immediately flushes newline-delimited JSON to the browser. No ports,
tools, model downloads, mounts or external services were added. The original
`POST /api/chat` whole-response interface remains available.

## Output inspection and interruptions

Each release passes the **entire generated prefix**, including available
lookahead, through the existing owner-only quarantine/DLP gate. Checks are not
applied to independent token fragments. Cuts require sentence punctuation plus
whitespace, or a blank line, so unfinished addresses and tokens remain buffered.
Incomplete protected phrases, including base64 and hex forms, remain buffered;
credential introductions switch to whole-reply buffering. GPU placement is
verified before first release and at completion. NDJSON frame, aggregate byte,
frame-count and request-time limits bound generation. Model thinking is disabled
and never forwarded.

Streaming cannot retract a sentence already displayed or heard. If a later
prefix fails DLP, that generated prefix is retained as an inert incident and
further release stops. The browser stops/discards remaining queued audio, marks
the partial reply incomplete, disables its replay button and excludes it from
conversation history. Already approved sentences may remain visible. These are
deterministic pattern protections, not a guarantee against every paraphrase or
encoding of sensitive information. Whole-response `/api/chat` retains its
atomic release behavior for callers requiring that contract.

## Speech

With **Speak replies** checked, each approved sentence enters a FIFO playback
queue. Text reading continues independently of synthesis and playback. Existing
bounded `/api/voice` synthesis rechecks client-supplied text before the CPU-only
Piper worker speaks it. At most one WAV is prepared ahead while the current one
plays. Mic capture stays suspended through generation, queued synthesis, playback
and paused audio. Pause/resume retains position; REPEAT LAST and per-message
replay use the completed full response. Muting speech or starting a replay
invalidates the automatic queue and discards late synthesis results.

There is still a first-sentence generation/inspection delay and a CPU speech
startup delay. Speech is sentence-based, rather than token-by-token, and the
worker currently loads its model per synthesis call. Short replies and passages
without sentence breaks benefit less; unusually many short sentences can reach
the existing 30 requests/minute gateway limit. Text remains available if voice
requests fail. No model speed improvement is claimed from streaming alone.

## Verification, 2026-10-09

The sealed agent emitted six approved chunks in a local MCP probe: first text
at **4.513 seconds**, final completion at **8.246 seconds**. This measures text
availability for one prompt, not physical speaker latency or general throughput.
The MCP tool descriptors exactly matched the approved baseline and all six
network/namespace/quarantine isolation checks passed after the offline rebuild.

A subsequent live HTTP gateway probe delivered first text at **3.136 seconds**,
first-sentence CPU-synthesized audio at **5.936 seconds**, and stream completion
at **6.190 seconds**. Synthesis ran concurrently with continued text delivery.
This measured WAV availability, not physical speaker onset. Local root and persona
requests returned 200 without login; unauthenticated LAN HTTPS returned 401 using
the local CA. Health passed GPU placement, CPU voice, DLP and egress checks.
The matching [offline scan receipt](STREAMING-SCAN-RECEIPT.json) records 64 clean
skills and eight retained MCP findings (MEDIUM); overall health stays degraded
for those warnings rather than claiming a clean security audit.

Regression coverage includes split credentials, addresses and paths; protected
phrases across sentence boundaries and encoded forms; a later DLP hold; GPU
placement; bounded/truncated NDJSON; MCP progress; gateway flushing before
completion; browser incremental rendering and speech enqueueing; interrupted
history; FIFO speech, one-sentence prefetch, pause, replay and cancellation.

Run `npm run test`, `npm run test:voice-ui`, and `npm run test:chat-ui`.
Physical mic/speaker and second-device LAN acceptance remain owner checks.
