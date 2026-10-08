# larpus

**LARP: Larp, Always Ready Prep.** LARPs all the way down.

A local-first home AI station: a practical home assistant and a LARP partner for
any subculture, including rehearsing life as an IT/cybersecurity professional.
Personas are swappable configs. Privacy is the feature: no cloud APIs, accounts,
remote fonts, analytics, or fallback inference. Single box, single owner.

The visual identity is a rotating torus beneath **∭ₜ dV = 2π²Rr²**.
The canvas torus fills in a repeating six-second sweep, holds for one second,
then starts again. The forming percentage is decorative, not inference progress.
Reduced motion shows a static, fully formed torus. Reference dimensions R = 2
and r = 0.8 give the displayed approximate volume of 25.266.

## Current access and decisions

Local: **http://127.0.0.1:8080**, no password.
LAN: **https://192.168.1.2:8080**, password required.
Use [restart instructions](docs/DEPLOYMENT.md) and [CA trust setup](docs/HTTPS.md).
Twelve [personas](docs/PERSONAS.md) are available. The
[decision record](docs/DECISIONS.md) explains accepted choices and pending work.

## First slice

The owner's Windows 11 Home station now defaults to the dedicated WSL2/rootless
Podman executor. For normal use, initialize the password with `python -m runtime.auth`
and launch `./scripts/run-isolated.ps1`; see [Windows Home isolation](docs/WINDOWS-HOME-ISOLATION.md).
The instructions below are an explicit **unsandboxed host development** alternative.
They are not the isolated deployment.

Python 3.10+ runs the gateway; Node 22+ is only needed to prepare local KaTeX assets.
Install Ollama separately. Initial downloads need internet; runtime needs none.

```powershell
npm.cmd ci --ignore-scripts
npm.cmd run vendor
python -m pip install -r requirements.txt
ollama pull qwen2.5:14b
# Start Ollama if its desktop service is not already running:
ollama serve
```

In another terminal:

```powershell
python -m runtime.auth
$env:LARPUS_ISOLATION='host' # Development only; explicitly bypasses container isolation.
python -m runtime.gateway
```

Open **http://127.0.0.1:8080** without a password; LAN HTTPS requires it. See
[password setup and rate limits](docs/AUTH.md). Select a persona and send a message.
Responses render as plain text; the torus accelerates while thinking. The mic button calls
the voice stub and reports that capture is not yet enabled. History lives only
in browser memory and is reset on reload or persona change. No tools execute.

```powershell
python -m unittest discover -s tests -v
```

`LARPUS_PORT` optionally changes the UI port. Ollama is deliberately fixed at
`127.0.0.1:11434`, ignoring proxy variables. Use local model tags only, disable
Ollama cloud features (`OLLAMA_NO_CLOUD=1` in the Ollama service environment), and
apply an outbound firewall deny rule for inference processes. A loopback URL
alone cannot prove the model server never uses external services.

## Runtime roadmap

For the owner's Windows 11 Home station, use the
[dedicated WSL2/rootless Podman isolation deployment](docs/WINDOWS-HOME-ISOLATION.md).
Its sealed stdio executor refuses host fallback. Windows Sandbox is unavailable
on Home. The dedicated distro and containers are installed; real network-denial,
GPU inference and DLP-quarantine checks passed. See the guide for remaining gates.

Target hardware: RTX 3090 Ti / 24 GB, Ryzen 9 5900X, 64 GB RAM. The
host development slice remains available explicitly. **OpenShell remains a target
layer; the Windows Home deployment currently enforces rootless Podman boundaries
without OpenShell.** See [architecture](docs/ARCHITECTURE.md),
[deployment gates](docs/DEPLOYMENT.md), [voice plan](docs/VOICE_INTEGRATION.md), and
[persona format](docs/AGENTS.md). For trusted home-network access, see
[LAN setup](docs/LAN.md).

Chat now passes through the pinned Steganography/stegdetect Unicode inspector
and local override/role-marker filters before inference. See
[text filtering and its limits](docs/TEXT_FILTER.md). This reduces exposure to
some prompt attacks; it does not guarantee prompt-injection prevention.

The HUD now routes chat and model status through a local stdio MCP server with
three fixed operations and no direct-inference fallback. See
[MCP setup and network isolation limits](docs/MCP.md). MCP exposes no internet
tools; an OS firewall/sandbox is still required for enforced egress denial.

The Windows Home default supplies that boundary through its tested network-disabled
rootless Podman pod; the explicit host developer mode remains unverified.

## Local skills, models and health

Generated chat passes through [local output DLP and owner quarantine](docs/OUTPUT-DLP.md)
before reaching MCP or the HUD. Held replies remain outside web access; inspection
is available only through the local owner CLI. The deployed private quarantine is inside the isolated runtime and is never
mounted into the model container.

The HUD offers four [locally authored, hash-checked prompt skills](docs/SKILLS.md).
No downloaded or executable skills are accepted. [Model selection and benchmarking](docs/MODELS.md)
recommend Qwen3 14B for the 3090 Ti, keeping the existing baseline until tested locally.
The gateway runs [continuous local health checks](docs/HEALTH.md), including
OWASP-recommended SkillSpector static scans and exact MCP tool-schema drift checks.
Health appears in the HUD; missing services and unverified containment
remain visible. No cloud scanner is used.

## Licensing

Larpus source retains the repository's [MIT license](LICENSE). KaTeX is MIT and
its license is copied beside the locally prepared assets. VoiceStudio is not
bundled: it is AGPL-3.0-only. Personal home use is compatible with this plan;
redistributing it or a combined/modified application can require corresponding
source and preservation of notices. Modified versions offered over a network
must offer their corresponding source to those users. A sidecar boundary does
not automatically exempt an integrated product from copyleft. Review the exact
combination before distribution; model weights have separate terms.
See [third-party notices](LICENSE-NOTICE.md) and
[VoiceStudio's license notice](https://github.com/debpalash/VoiceStudio/blob/main/LICENSE-NOTICE.md).

No mobile app, multi-user service, cloud account, or remote telemetry is planned.
