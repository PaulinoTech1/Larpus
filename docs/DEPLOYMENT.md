# Rebuild and deployment gates

## Rebuild current host slice

Clone this repo; install Python 3.10+, Node 22+, and Ollama. Run `npm ci
--ignore-scripts`, `npm run vendor`, and `ollama pull qwen2.5:14b` during the
online preparation window. Start Ollama with cloud disabled, then run
`python -m runtime.gateway`. Preserve `web/vendor/katex` and the Ollama model
cache to rebuild/run offline. There are no Python package dependencies.
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
