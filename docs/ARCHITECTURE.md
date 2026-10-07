# Architecture

```text
Browser HUD → Larpus gateway → AEI config runtime → local Ollama
                    ↑                              ↓
Wake word → local STT → user message       text → local TTS → speaker
               VoiceStudio adapter / voice profiles (planned)

Target boundary: OpenShell supervisor → rootless Podman agent sandbox
```

All components stay on the owner's PC. The UI serves its own fonts, scripts,
equation renderer, and animation. The gateway validates messages, injects the
chosen persona's system prompt, bounds body/history/context/output, and serializes
inference. It only calls host-loopback Ollama `/api/chat` with `stream:false`.
The browser never chooses an upstream URL, model, or system instruction.
Errors are explicit; no cloud fallback. Responses use text nodes, not model HTML.
History is session-only; no prompt logging, durable memory, or file/home tools.

AEI here means the project's configurable agent execution interface, not an
implementation of an unspecified external AEI SDK. Add a sandbox executor behind
this interface later; keep persona definition independent of execution backend.
Until then `runtime/agents.py` is config-driven inference only.

## Boundaries and storage

| Component | Bind / port | Storage / mounts | Current status |
|---|---|---|---|
| HUD + Larpus gateway | 127.0.0.1:8080, `LARPUS_PORT` override | reads `web/` and `agents/`; no writable data | implemented |
| Ollama host service | 127.0.0.1:11434 | Windows `%USERPROFILE%\.ollama\models`; Linux `~/.ollama/models` for user service, or explicit `OLLAMA_MODELS` | external prerequisite |
| VoiceStudio adapter | reserve 127.0.0.1:7861 | planned `data/voice/{models,profiles,recordings}` | stub only |
| OpenShell control plane | version-specific local port, record before deployment | dedicated `data/openshell`, Podman user socket | not deployed |
| AEI sandbox | no published ports | `/app` read-only code, `/app/agents` read-only configs; future `/data` scoped writable state | planned |

7861 is Larpus's proposed adapter port, not a claim about VoiceStudio's API port.
No volumes are mounted by the current host slice. Do not mount the home directory,
Podman socket, credential stores, or model cache into the agent. OpenShell owns
its privileged control interfaces outside the workload. Host loopback inside a
container differs from host loopback; a future supervisor-local inference route
must bridge this explicitly, never broaden Ollama to `0.0.0.0` as a shortcut.

## Target isolation and privacy

Use Linux or WSL2 with rootless Podman 5.x and a pinned OpenShell release. WSL2
support is experimental; rootless networking and kernel enforcement need owner
validation. Set `OPENSHELL_TELEMETRY_ENABLED=false` on the gateway. Deny all
outbound traffic except the specific local inference and voice routes, and deny
external DNS. Enforce this at the supervisor and host firewall. Keep tools
disabled until policy denial tests and scoped mounts are verified.

OpenShell deployment is not simulated here: Podman and OpenShell are unavailable
in the kickoff environment. See DEPLOYMENT.md for the acceptance gates. Never
describe the development Python process as an OpenShell sandbox.

References checked 2026-10-07:
- https://docs.ollama.com/api/chat
- https://docs.nvidia.com/openshell/latest/about/support-matrix
- https://github.com/NVIDIA/OpenShell (telemetry opt-out)
