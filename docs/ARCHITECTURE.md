# Architecture

## Deployed Windows 11 Home station

```text
Local HTTP 127.0.0.1:8080 (no password)
LAN HTTPS 192.168.1.2:8080 (password + subnet checks)
  -> Windows gateway, shared authentication and limits
  -> fixed WSL/Podman stdio MCP
Dedicated Larpus WSL2 / rootless network=none pod:
  trusted persona/skill/MCP runtime -> Ollama loopback :11434
  generated reply -> DLP -> private quarantine -> approved output
```

Only network is shared; PID/IPC/filesystems are separate. No published inference
port. Code/configs/models are read-only. Model gets narrow read-only GPU libraries
and one NVIDIA package plus /dev/dxg; agent gets no GPU, Windows drives, owner
home, passwords or container sockets. Only trusted DLP mounts writable quarantine.
The executor validates sealed source and images and never falls back to host mode.

Browser selects approved personas/skills, never upstream URLs or system prompts.
Inputs are validated/filtered; replies render as text. Chat history is browser
memory only; held output is the intentional persistence exception. AEI is this
project's configurable agent interface, not an external SDK.

VoiceStudio STT/TTS remains planned with AGPL distribution implications. Voice
is a stub; proposed adapter port 7861 is not listening. OpenShell is a future
layer with no deployed control-plane port. Explicit host development mode does
not carry the Podman isolation claims.

See [exact mounts/rebuild](WINDOWS-HOME-ISOLATION.md), [HTTPS](HTTPS.md),
[decisions](DECISIONS.md) and [verification](VERIFICATION.md).
