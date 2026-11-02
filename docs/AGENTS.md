# AEI persona contract

`agents/schema.json` defines v1. `runtime/agents.py` enforces the supported fields
at startup, rejects unknown fields and duplicate IDs, and fails startup on invalid
configs. Reseal the isolated runtime and restart the gateway after edits. Add a JSON file under `agents/personas`
to add another subculture/persona; UI choices are discovered from these files.

| Field | Meaning |
|---|---|
| version | Must be 1 |
| id | Stable lowercase slug, up to 64 characters |
| name / description | UI label and purpose; nonempty text |
| system_prompt | Server-owned persona instructions; nonempty text |
| model | Installed local Ollama tag; no cloud suffix |
| temperature | Number from 0 to 1 |
| voice | Future local voice profile ID or null; currently unused |

The original two reference personas are: `home-assistant` and `it-larp-coach`. Both use
`larpus3.8:27b-q4`. The latter coaches scenarios without presenting fiction as actual
professional experience. Future personas can cover any subculture. Persona
prompts are behavioral guidance, not security controls; tools and network rights
belong to independently enforced sandbox policy.

API: `GET /api/personas`, `GET /api/health`, `POST /api/chat` with
`{"persona":"home-assistant","messages":[{"role":"user","content":"Hello"}]}`.
Conversation must alternate user/assistant and end in user; max 40 messages,
8000 characters each, 64 KiB body. Ollama context 131072 tokens, output max 1024
tokens, 120-second timeout; long histories may be truncated by the model context.
409 signals busy inference, 400 invalid input, 502 local model failure.
`POST /api/voice` returns 501 until capture/STT/TTS integration exists.

Ten additional roles ship; see [persona catalog](PERSONAS.md). All twelve
use larpus3.8:27b-q4 and approved local skill allowlists.
