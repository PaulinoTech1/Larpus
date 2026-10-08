# Local MCP inference boundary

The Windows Home default now executes MCP inside a dedicated WSL2/rootless Podman
deployment. Its network-disabled pod enforces external egress denial, and the
model container cannot mount quarantine or Windows home files. See
[Windows Home isolation](WINDOWS-HOME-ISOLATION.md) for the deployed executor,
driver/mount allowlists, behavioral checks and remaining acceptance limits.
Host firewall advice below applies to the explicit unsandboxed developer mode.

```text
Home-LAN browser
  → password + rate-limited HTTP gateway
  → fixed Python child over stdio MCP (no listening port)
  → server-owned persona + local text filter
  → fixed 127.0.0.1:11434 Ollama endpoint
```

The gateway now uses MCP for chat and model status. If MCP fails, the gateway
returns an error; it never falls back to calling Ollama directly. Its existing
authentication, LAN subnet/Origin checks, filtering and rate limits remain.
The server independently validates/filters all incoming history, including calls
from a different local MCP client. Model and system prompt come from persona
configs, never caller-supplied model/URL/system instructions.

## Available operations

| Tool | Input | Capability |
|---|---|---|
| list_personas | none | read configured persona summaries |
| local_status | none | fixed local `/api/tags` check |
| chat_local | persona ID, alternating messages | bounded filtered local inference |

No URL fetch, browser, shell, file access, model pull, model create, remote sampling,
or dynamic tool execution is exposed. Caller extra tool fields cannot change the
fixed destination or model; SDK may ignore fields not in a tool signature. Ollama
receives no tool definitions, and its output is text, never executable commands.
The network adapter accepts only `/api/chat` and `/api/tags`, ignores proxy env
variables, disables HTTP redirects and uses a numeric loopback address (no DNS).
Inference has a 120-second timeout and a 2 MB upstream response cap. The client
has a 140-second overall timeout and no configurable remote server option.

## Run/rebuild

```powershell
python -m pip install -r requirements.txt
& .\scripts\start-lan.ps1
```

The HUD launches a child for each chat/status operation and cleans it up when
done. This prioritizes a small, fixed process lifecycle over a persistent pool;
there is process startup overhead and no cross-child inference lock. The HTTP
gateway still serializes chats within its process. MCP direct clients have a
30-call/minute process-local limit for chat/status and a per-process lock.
Separate clients/processes do not share rate limits. Ollama GPU concurrency
limits remain a separate owner-configured control.

To attach another **local** MCP host, adapt `config/mcp.example.json` to its
configuration format and your actual Python/repo paths. `scripts/run_mcp.py`
works from any client working directory. Alternatively launch
`python -m runtime.mcp_server` from this repo. It waits for protocol input on
stdin; it is not a web page. Only JSON-RPC goes to stdout; prompts are not logged.
Stdio access uses the launching OS account, not the LAN password. Any local
program with permission to run this code can launch its own server.

The gateway child gets a limited environment without inherited API keys, proxy
settings or OpenTelemetry exporter configuration. OpenTelemetry SDK is disabled
there explicitly. No exporter is configured in Larpus. Third-party hosts must
control their own environment and telemetry; the example is not an OS sandbox.

Official Python MCP SDK is pinned to 2.3.0 (MIT). Cache all resolved dependency
wheels during online preparation:

```powershell
python -m pip wheel -r requirements.txt --wheel-dir data/wheels
```

Retain a manifest of wheel names, versions and SHA256 hashes and third-party
licenses. On the same offline OS/Python version:

```powershell
python -m pip install --no-index --find-links data/wheels mcp==2.3.0 stegdetect==0.2.0
```

Use the Stegdetect wheel built from the pinned Git commit, not a different wheel
with the same package version. Cache compatible wheels separately for Linux.
No runtime dependency installer or auto-update operation exists.

## Network enforcement (separate from MCP)

MCP restricts the interface; it does **not** prohibit Python, an unrelated agent,
or Ollama from opening sockets. The server has no internet operations, but it runs
with the owner's normal OS permissions. The model could still output unsafe text.
Existing text heuristics and persona reminders are not an enforced sandbox.

For Windows, prepare models first, configure Ollama itself with
`OLLAMA_NO_CLOUD=1`, restart it, and keep `OLLAMA_HOST=127.0.0.1:11434`. Setting
this in an MCP child does not reconfigure an already-running Ollama service.
Then run the following in **Administrator PowerShell**, specifying the actual
Ollama executable **and every runner executable**:

```powershell
& .\scripts\isolate-ollama.ps1 -Executable @(
    'C:\path\to\ollama.exe',
    'C:\path\to\ollama_llama_server.exe'
)
```

These are placeholders; installed names/paths vary. The script refuses missing
paths and blocks all non-loopback IPv4/IPv6 destinations for the supplied binaries
on every profile. Downloads/updates from those processes are blocked as well.
Recheck runner paths/rules after upgrades. It does not block the PC's other apps
or modify router settings. Undo the exact created rules as Administrator:

```powershell
Get-NetFirewallRule -Name 'Larpus-Ollama-Egress-*' | Remove-NetFirewallRule
```

This environment has no Ollama executable and lacks Administrator rights; the
rule has **not been applied or behaviorally verified**. Windows firewall rules
are program-scoped, not a complete malicious-process containment guarantee.
OpenShell/rootless Podman remains the target for OS-enforced agent policy; its
deployment and outbound-denial gates are still unrun. Do not claim MCP alone
isolates a hostile agent from the internet.

Owner acceptance: confirm local model chat succeeds, then confirm denied
non-loopback IPv4/IPv6 connections from each protected executable; verify cloud
and model-download paths fail, with no fallback. Reboot offline and repeat chat.
Verify the actual running firewall policy and executable paths before treating
the network boundary as enforced.

## Validation

29 local tests pass: authentication and filters, server-owned inference payload,
MCP tool allowlist, process-local limits, route/redirect rejection, child env,
real SDK stdio handshake/discovery/filter hold, and a real child round-trip to a
mock Ollama HTTP service on loopback. This is protocol/integration evidence,
not a live model, GPU, external-egress or sandbox test.

References:
- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- https://github.com/modelcontextprotocol/python-sdk
# Local skill and health additions

chat_local accepts an optional registered skill ID, validated against the selected
persona on both sides of the child boundary. Discovery remains three fixed tools.
config/mcp-approved.json is the reviewed descriptor snapshot: the health monitor
compares actual stdio discovery against it every cycle. See [health](HEALTH.md)
for source scanning and [skills](SKILLS.md) for the local authoring policy.
