# Rebuild and deployment gates

Windows 11 Home deployment is now implemented separately in
[WINDOWS-HOME-ISOLATION.md](WINDOWS-HOME-ISOLATION.md): a dedicated WSL2 distro,
rootless network-disabled Podman pod, sealed stdio MCP executor and quarantine
volume excluded from the model container. It is now provisioned on this machine
and passed live denial, DLP and GPU checks. OpenShell below remains an additional
unimplemented layer; backend restart after owner-reported Windows reboot is verified; physically
disconnected reboot and second-device UI acceptance remain pending.

## Restart deployed station

```powershell
wsl --distribution Larpus --user larpus --exec env XDG_RUNTIME_DIR=/run/user/1000 podman pod start larpus-offline
python -m runtime.isolation check
# Continue only after a successful check:
.\scripts\start-lan.ps1
```

Preserve data/password.json, data/tls and the Linux quarantine volume. Local HTTP
has no password; LAN HTTPS requires it. Missing TLS credentials stop LAN startup.
Reseal runtime after source/persona edits before restarting. No autostart is installed.
See [HTTPS](HTTPS.md) and [decisions](DECISIONS.md).

## Rebuild explicit unsandboxed host slice

Clone this repo; install Python 3.10+, Node 22+, and Ollama. Run `npm ci
--ignore-scripts`, `npm run vendor`, and `ollama pull qwen2.5:14b` during the
online preparation window. Start Ollama with cloud disabled, then run
`python -m runtime.auth`, explicitly set `LARPUS_ISOLATION=host`, then run
`python -m runtime.gateway`. Preserve `web/vendor/katex` and the Ollama model
cache to rebuild/run offline. Install the pinned Python dependency from
`requirements.txt`; cache its wheel as described in TEXT_FILTER.md.
Only gateway 8080 and Ollama 11434 listen, both on loopback. No container volume
mounts exist in this slice. GPU drivers and Ollama CUDA support remain external
prerequisites. Query `ollama list` and record each model digest; tags can change.

## OpenShell / rootless Podman target (unrun)

1. Prepare Linux/WSL2, Podman 5.x rootless user socket, compatible kernel, and
   GPU driver. Confirm rootless with `podman info`. Use the upstream support
   matrix; Windows + rootless Podman must be tested, not inferred from Docker.
2. Pin OpenShell CLI/gateway/sandbox to the same stable release. Download and
   verify its release checksums and OCI image digests during preparation.
   Never use upstream cloud-provider quickstarts for Larpus.
3. Configure local control plane with telemetry disabled. Record its actual
   loopback port, data directory and socket path in `data/deployment.json`.
   The control plane port is release-specific and is deliberately not guessed.
4. Build an agent workload containing Python + this runtime, with code/config
   read-only. No published workload ports, no home/socket/credential mounts.
   Expose chat through the trusted host gateway/supervisor route; container
   `127.0.0.1` is not the host. Implement that executor before switching modes.
5. Configure deny-by-default filesystem/network policy and local Ollama/voice
   routes. Host firewall denies all external egress, including DNS. Check
   telemetry settings on the running gateway, not only the shell launching it.
6. Record every resolved port, mount source/target/mode, binary version, image
   digest, model digest, and license in the manifest; export/cache all artifacts.
7. Verify sandbox enforcement with deliberate denied external URL, DNS, home
   file and Podman socket accesses; then reboot offline and run chat + voice.

There is no runnable OpenShell deployment script until these host/version choices
are verified. The development gateway must not be called sandboxed or released
as a hardened station. Target acceptance includes an owner-run local-model chat,
offline reboot, privacy/egress check, and later wake-word/STT/TTS cycle.

Reference: https://docs.nvidia.com/openshell/latest/about/support-matrix
