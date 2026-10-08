# Windows 11 Home isolation

Windows Sandbox is [unsupported on Home](https://learn.microsoft.com/en-us/windows/security/threat-protection/windows-sandbox/windows-sandbox-overview).
[WSL2 supports Home](https://learn.microsoft.com/en-us/windows/wsl/faq).
Larpus therefore uses a dedicated **Larpus** WSL2 distro with rootless Podman.
It does not change Docker Desktop's distro, shut down all WSL instances, require
Hyper-V Manager, install unofficial Sandbox packages, or rely on Pro-only policy UI.

```text
Home LAN -> password/rate-limited Windows gateway :8080
                  -> wsl.exe -> rootless podman exec -> MCP stdio
Dedicated WSL2: network=none pod, only network namespace shared
  trusted agent/MCP/DLP container -> loopback Ollama :11434 -> model container
           |                                          |
   private quarantine volume                    model cache read-only
   no GPU or host files                         WSL GPU device/libraries
```

No inference port is published to Windows or the LAN. The Windows gateway remains
the sole LAN listener, restricted as in LAN.md. No bridge, host network, internet
proxy or owner home mount is used. The model and agent have separate PID/IPC
namespaces, read-only root filesystems, dropped capabilities, no-new-privileges,
resource limits and disabled container logs. Temporary directories are bounded
noexec/nosuid/nodev tmpfs; source/personas/skills/policy are baked into the sealed
image. External network is absent from the shared pod. The model cannot mount
the DLP evidence volume. MCP/DLP is trusted mediation, not model-generated code.

This moves Ollama off Windows into WSL2; it never exposes the Windows host's
loopback endpoint to the container. No host-firewall allowlist is needed for
inference egress in this topology. The Windows gateway/scanner are still trusted
host processes, not globally internet-blocked by this deployment. OpenShell is
not installed here; an additional OpenShell policy/control plane remains a future
integration, not a prerequisite falsely claimed as enforced.

## Dedicated preparation, before going offline

The dedicated Ubuntu 24.04 Larpus distro is now installed alongside docker-desktop,
with a locked-password non-root larpus UID 1000 and subordinate UID/GID ranges.
The sealed containers are running and the behavioral denial/GPU/DLP checks passed.
Password initialization is complete; another LAN device's UI acceptance remains pending. No Windows elevation
was needed to install this distro because WSL2 was already enabled.

1. Obtain an official Ubuntu 24.04 WSL rootfs and verify its published checksum.
   Import it as Larpus using `wsl --import Larpus <new-local-distro-directory>
   <verified-rootfs.tar> --version 2`. Keep this directory separate from Docker
   Desktop. Enabling WSL/Virtual Machine Platform if absent needs an elevated
   Windows terminal and possibly a reboot; the current machine already has WSL2.
2. Inside **only Larpus**, create the non-root larpus user, install Podman,
   uidmap, Python 3.12, pip/venv and rootless prerequisites. Confirm subuid/subgid
   ranges, cgroups v2 and `podman info` reports rootless. Package installation is
   the online preparation phase, not normal operation.
3. Cache a Linux amd64 Python 3.12 slim image and official Ollama image, then
   record their immutable repo digests. These two digests are required arguments;
   deploy.sh refuses floating tags and never pulls images. Select/test versions
   for this WSL kernel/driver and preserve licenses and exported OCI archives.
4. In the Linux environment, build a complete Linux wheel cache for the pinned
   requirements.txt, including stegdetect from the pinned Git commit. Put only
   wheels and SHA256SUMS in vendor/runtime-wheels. Generate hashes with
   `sha256sum *.whl > SHA256SUMS`. Preserve that directory for offline rebuilds.
   Windows wheels are not interchangeable with Linux wheels.
   deploy/windows-home/prepare-cache.sh automates image/wheel/model caching in an
   explicitly online phase, pinning resolved OCI digests afterwards. It downloads
   only persona-configured model tags and passes no conversations or credentials.
5. Prepare the Ollama `blobs`/`manifests` cache at /home/larpus/models during the
   online window. Match both persona model tags, record digests, then stop any
   temporary online preparation server. Do not put passwords or home files there.
6. On Windows run scripts/export-isolation-source.ps1. Transfer its archive and
   fingerprint into /home/larpus/build before disabling drive access. Extract
   there without including private data. Add the prepared Linux wheel cache.
7. Copy deploy/windows-home/wsl.conf to /etc/wsl.conf as distro root. It disables
   drive automount, fstab mounts, Windows interop and Windows PATH inheritance.
   Restart **only Larpus** with `wsl --terminate Larpus`, then relaunch. Do not
   replace global .wslconfig or shut down Docker Desktop. These
   [per-distro controls are documented by Microsoft](https://learn.microsoft.com/en-us/windows/wsl/wsl-config).
   Empty /mnt/c and /mnt/e directories can remain after automount is disabled.
   Verify they are not mountpoints with findmnt, then remove only the empty
   directories with rmdir. Never recursively delete or traverse a mounted drive.

The actual installation uses Ubuntu 24.04, Podman 4.9.3 from Ubuntu's patched
packages, cgroups v2 and UID 1000. It enables that user's linger service. Pro/news
integration, automatic apt/Podman update timers and NTP are disabled in **Larpus
only**; schedule explicit security maintenance. Do not change Docker Desktop units.

The dedicated distro's non-root user must be able to access /dev/dxg and the
Microsoft-provided GPU libraries. Do not install a Linux display driver over the
Windows NVIDIA driver. [Microsoft documents CUDA on WSL2](https://learn.microsoft.com/en-us/windows/ai/directml/gpu-cuda-in-wsl).
The GPU mount recipe was tested on this machine. In addition to /dev/dxg and WSL
libraries, NVIDIA's forwarder needs its specific DriverStore package. Deployment
selects a single nv_*.inf_amd64_* folder containing libcuda.so.1.1 and mounts only
that folder read-only at its original path. It refuses ambiguous packages rather
than mounting the entire DriverStore. The profile pins that path; driver updates
require review/redeployment. This matches
[NVIDIA's explanation of WSL driver forwarding](https://developer.nvidia.com/blog/?p=18337).

## Offline deployment and Windows connection

Inside /home/larpus/build, as larpus:

```bash
bash deploy/windows-home/deploy.sh \
  docker.io/library/python@sha256:<cached-python-digest> \
  docker.io/ollama/ollama@sha256:<cached-ollama-digest> \
  <fingerprint-from-Windows-export> > /home/larpus/deployment.json
```

All status goes to stderr; stdout is the profile JSON. Retrieve only that JSON to
the Windows repo's **data/isolated-deployment.json** using WSL stdio, then run:

```powershell
# In the Windows repo (ASCII JSON is safe through this pipeline):
wsl --distribution Larpus --user larpus --exec cat /home/larpus/deployment.json |
  Set-Content -LiteralPath data/isolated-deployment.json -Encoding utf8
python -m runtime.auth
./scripts/run-isolated.ps1
```

Use PowerShell 7 UTF-8 output or remove the UTF-8 BOM emitted by Windows PowerShell
5.1: the profile loader accepts UTF-8 with BOM. Keep LAN bind/CIDR configured using
the existing LAN startup environment before launching. No credentials are copied
into WSL or either image. The source archive excludes data entirely.

config/isolation.json selects wsl-podman by default, including when the deployment
profile is missing: missing prerequisites fail closed. An explicit
LARPUS_ISOLATION=host is available only for unsandboxed developer tests. After
hardening, transfer new exported source using `python scripts/transfer-isolation-source.py`;
it sends the fixed tar archive through binary stdin without enabling drive mounts.
The deployed OCI configuration is also inspected: rootless Podman records its
GPU device as a bind mount rather than HostConfig.Devices. Both representations
are verified against the narrow allowlist, including zero OCI capabilities.

Startup and each MCP invocation validate rootless status, immutable image IDs,
source fingerprint, actual mount sources/destinations, namespace sharing, no ports,
read-only rootfs, capability drops, devices and resource limits. Unknown modes,
missing distro, drift or failed Podman inspection do not fall back to host Python.
After any relevant source/skill/policy change, reseal and redeploy deliberately;
deploy.sh refuses to replace existing containers/pod. Review and stop only the
named Larpus deployment; do not delete its quarantine volume automatically.

## Ports, storage and investigation

| Component | Port/mount | Access |
|---|---|---|
| Windows HUD gateway | HTTP loopback and HTTPS LAN, port 8080 | Local bypass; LAN password + shared limits |
| Ollama in isolated pod | 127.0.0.1:11434, no published port | Shared pod loopback only |
| MCP | stdio through wsl/podman exec | No listening port |
| Model cache | /home/larpus/models -> /models | Model only, read-only |
| GPU libraries | /usr/lib/wsl/lib -> same path | Model only, read-only |
| NVIDIA driver package | One pinned /usr/lib/wsl/drivers/nv_*.inf_amd64_* -> same path | Model only, read-only |
| GPU device | /dev/dxg | Model only |
| Quarantine | larpus-quarantine -> /app/data/quarantine | Trusted MCP/DLP only, writable, noexec/nosuid/nodev |
| Model temporary files | /tmp, 1 GiB | Ephemeral tmpfs |
| Agent temporary files | /tmp, 128 MiB | Ephemeral tmpfs |

The Windows data/quarantine folder belongs to host development mode; it is not
the isolated evidence store. Investigate the Linux volume through trusted stdio:

```powershell
python -m runtime.isolation quarantine list
python -m runtime.isolation quarantine inspect <incident-id>
python -m runtime.isolation quarantine delete <incident-id>
```

No model/API release or investigation tool is added. Windows owner/admin and WSL
root can administer Podman and evidence; this boundary does not defend against
the owner, host administrator, kernel/GPU-driver compromise or a trusted guard exploit.

## Acceptance before calling it deployed

Run `python -m runtime.isolation check`: it inspects actual configuration and
checks external/LAN TCP denial, owner-drive/socket absence and local inference
reachability, plus DNS/UDP denial, kernel capability zeros and owner-only quarantine.
Continuous health repeats these checks in isolated mode. Also test
a real model response and held DLP output, evidence inaccessible
from the model container, GPU utilization via Ollama, offline reboot/restart and
another LAN device's password-protected chat. Save all versions, OCI/model digests
and results locally. The code/config tests here do not establish these live gates.
WSL2 provides a Linux VM; rootless Podman supplies workload boundaries within it.
Its security depends on an updated Windows/WSL/kernel/driver and tested runtime,
not merely on being a separate distro.

Restart the isolated backend after a distro/Windows restart using
`wsl --distribution Larpus --user larpus --exec env XDG_RUNTIME_DIR=/run/user/1000 podman pod start larpus-offline`,
then run the Windows isolation check before the gateway. Nothing automatically
falls back to Windows Ollama. The deployment preserves existing quarantine volumes
on rebuild, and fails if existing named containers/pod have not been reviewed/stopped.
Its infra container uses the cached Python image and sleep, publishing no services;
only net is shared, not PID/IPC. Ollama pruning is disabled so model storage stays
read-only. Do not enable model downloads on the production pod.
