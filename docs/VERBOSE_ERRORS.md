# Verbose owner error diagnostics

Errors retain the existing public boundary code and HUD correlation ID. Owner stderr now records an exact reviewed message, specific reason and recovery action for known authored failures, alongside exception types, cause links, frame locations and numeric OS/process codes. This extends the existing diagnostic schema additively; it does not expose detailed setup errors through the LAN or model.

## Debug workflow

1. Copy the diagnostic ID shown by the HUD.
2. From any PowerShell folder, run `python "E:\speedzone_MS\LARPUS\scripts\errors.py" "YOUR_ACTUAL_ERROR_ID"`, replacing the quoted placeholder with the real 16-character diagnostic ID. Do not use angle brackets. It finds exact and linked records in fixed owner gateway/notes logs, including the notes-worker cause link.
3. Start with the innermost cause: read `reason`, `message`, `action`, frames and errno/returncode. Check readiness and pins before retrying.
4. If lookup finds nothing, inspect capture/permissions and older retained logs. Missing records are not proof that no failure occurred.

Lookup examines only the last 16 MiB per fixed gateway/notes log and returns at most 50 records. Exit status 0 means found, 1 means no recent match, 2 means invalid ID or lookup failure. It does not start services, access the corpus or expose an HTTP endpoint. Existing logs are owner data; do not publish them unchanged.

A diagnostic ID exists only when the instrumented LARPUS runtime reports a failure. PowerShell parser errors and Python launch errors do not receive LARPUS IDs. Repository changes require the staged release workflow before the live station uses them.

## Exactness and limits

Only exact matches against fixed, reviewed literals are recorded. Arbitrary exception args, subprocess commands/stdout/stderr, model replies, prompts and credentials remain withheld. Adding a secret to a known message makes it unclassified rather than allowing it through. JSON decoding errors include line/column but omit document content; timeouts, permission denials and connection failures have stable classifications. Unknown errors explicitly say that no reviewed exact message exists. Classification describes the observed failure, not its root cause. No automatic repair, retry or sandbox weakening is introduced.

This catalog covers authored voice, MCP, inference transport, notes-worker and inference validation failures. It does not instrument every error in every component. Expected broker rejections retain their existing domain codes; voice busy now receives a diagnostic ID too. A broken stderr sink can still lose the record, and Windows kernel crashes require separate incident evidence.

## Reviewed message catalog

| Exact owner-log message | Reason |
| --- | --- |
| Compression batch exceeds context | INFERENCE-COMPRESSION-BATCH-EXCEEDS-CONTEXT |
| Empty model response | INFERENCE-EMPTY-MODEL-RESPONSE |
| Incomplete local MCP stream | MCP_CLIENT-INCOMPLETE-LOCAL-MCP-STREAM |
| Inference broker is required | LOCAL_OLLAMA-INFERENCE-BROKER-IS-REQUIRED |
| Inference redirects are disabled | LOCAL_OLLAMA-INFERENCE-REDIRECTS-ARE-DISABLED |
| Inference route is not allowed | LOCAL_OLLAMA-INFERENCE-ROUTE-IS-NOT-ALLOWED |
| Input too large | INFERENCE-INPUT-TOO-LARGE |
| Invalid GPU placement report | INFERENCE-INVALID-GPU-PLACEMENT-REPORT |
| Invalid approved chunk | MCP_CLIENT-INVALID-APPROVED-CHUNK |
| Invalid broker readiness | LOCAL_OLLAMA-INVALID-BROKER-READINESS |
| Invalid job | NOTES_WORKER-INVALID-JOB |
| Invalid model content | INFERENCE-INVALID-MODEL-CONTENT |
| Invalid model stream | LOCAL_OLLAMA-INVALID-MODEL-STREAM |
| Invalid private inference socket | LOCAL_OLLAMA-INVALID-PRIVATE-INFERENCE-SOCKET |
| Invalid voice identity | VOICE-INVALID-VOICE-IDENTITY |
| Invalid voice response | VOICE-INVALID-VOICE-RESPONSE |
| Job too large | NOTES_WORKER-JOB-TOO-LARGE |
| LARP-MCP-STREAM | MCP_CLIENT-LARP-MCP-STREAM |
| LARP-MCP-UNAVAILABLE | MCP_CLIENT-LARP-MCP-UNAVAILABLE |
| LARP-VOICE-UNAVAILABLE | VOICE-LARP-VOICE-UNAVAILABLE |
| Local MCP operation failed | MCP_CLIENT-LOCAL-MCP-OPERATION-FAILED |
| MCP tool is not allowed | MCP_CLIENT-MCP-TOOL-IS-NOT-ALLOWED |
| Model response too large | LOCAL_OLLAMA-MODEL-RESPONSE-TOO-LARGE |
| Model stream ended without completion | LOCAL_OLLAMA-MODEL-STREAM-ENDED-WITHOUT-COMPLETION |
| Model stream exceeded limits | LOCAL_OLLAMA-MODEL-STREAM-EXCEEDED-LIMITS |
| Notes DNS/UDP reachable | NOTES_WORKER-NOTES-DNS-UDP-REACHABLE |
| Notes broker unavailable | NOTES_WORKER-NOTES-BROKER-UNAVAILABLE |
| Notes identity/network drift | NOTES_WORKER-NOTES-IDENTITY-NETWORK-DRIFT |
| Notes privilege drift | NOTES_WORKER-NOTES-PRIVILEGE-DRIFT |
| Notes raw network reachable | NOTES_WORKER-NOTES-RAW-NETWORK-REACHABLE |
| Oversized broker status | LOCAL_OLLAMA-OVERSIZED-BROKER-STATUS |
| Too many model frames | LOCAL_OLLAMA-TOO-MANY-MODEL-FRAMES |
| Unexpected notes capability | NOTES_WORKER-UNEXPECTED-NOTES-CAPABILITY |
| Unexpected voice mounts | VOICE-UNEXPECTED-VOICE-MOUNTS |
| Unknown inference capability | LOCAL_OLLAMA-UNKNOWN-INFERENCE-CAPABILITY |
| Unknown persona | INFERENCE-UNKNOWN-PERSONA |
| Voice boundary violated | VOICE-VOICE-BOUNDARY-VIOLATED |
| Voice host devices prohibited | VOICE-VOICE-HOST-DEVICES-PROHIBITED |
| Voice identity/resource limits missing | VOICE-VOICE-IDENTITY-RESOURCE-LIMITS-MISSING |
| Voice image drift or stopped worker | VOICE-VOICE-IMAGE-DRIFT-OR-STOPPED-WORKER |
| Voice privileges violated | VOICE-VOICE-PRIVILEGES-VIOLATED |
| Voice response too large | VOICE-VOICE-RESPONSE-TOO-LARGE |
| Voice worker busy | VOICE-VOICE-WORKER-BUSY |
| Voice worker source changed; rebuild voice image | VOICE-VOICE-WORKER-SOURCE-CHANGED--REBUILD-VOICE-IMAGE |

## Checkout validation

211 isolated tests reported OK, with two skips. Tests cover exact-message matching, secret-bearing unknown messages, JSON coordinate privacy, subprocess timeout privacy, protocol-only stdout and linked-ID lookup. Diagnostic HUD check and the existing complexity gate passed without changing baseline allowances. This validation covers the checkout, not a production activation; no frozen release or service was modified.
