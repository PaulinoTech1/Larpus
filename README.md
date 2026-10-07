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

## First slice

Python 3.10+ runs the gateway; Node 22+ is only needed to prepare local KaTeX assets.
Install Ollama separately. Initial downloads need internet; runtime needs none.

```powershell
npm.cmd ci --ignore-scripts
npm.cmd run vendor
ollama pull qwen2.5:14b
# Start Ollama if its desktop service is not already running:
ollama serve
```

In another terminal:

```powershell
python -m runtime.auth
python -m runtime.gateway
```

Open **http://127.0.0.1:8080** and enter the station password; see
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

Target hardware: RTX 3090 Ti / 24 GB, Ryzen 9 5900X, 64 GB RAM. The kickoff is a
host-only development slice. **OpenShell on rootless Podman is the target runtime,
not an enforced boundary in this slice.** See [architecture](docs/ARCHITECTURE.md),
[deployment gates](docs/DEPLOYMENT.md), [voice plan](docs/VOICE_INTEGRATION.md), and
[persona format](docs/AGENTS.md). For trusted home-network access, see
[LAN setup](docs/LAN.md).

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
