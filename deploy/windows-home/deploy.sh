#!/usr/bin/env bash
# Run as larpus inside the dedicated WSL2 distro, after offline artifacts are ready.
set -euo pipefail
export XDG_RUNTIME_DIR=/run/user/1000
if [[ $(id -un) != larpus || $(id -u) == 0 ]]; then echo 'Run as the dedicated non-root larpus user' >&2; exit 1; fi
cd "$(dirname "$0")/../.."
if [[ $# != 3 || ! $1 =~ ^docker.io/library/python@sha256:[a-f0-9]{64}$ || ! $2 =~ ^docker.io/ollama/ollama@sha256:[a-f0-9]{64}$ || ! $3 =~ ^[a-f0-9]{64}$ ]]; then
  echo 'Supply cached Python image digest, Ollama image digest and source fingerprint' >&2; exit 1
fi
cmp -s deploy/windows-home/wsl.conf /etc/wsl.conf || { echo 'Dedicated WSL configuration must match and be restarted' >&2; exit 1; }
[[ ! -e /mnt/c && ! -e /mnt/e && ! -e /proc/sys/fs/binfmt_misc/WSLInterop ]] || { echo 'Windows mounts/interop still accessible' >&2; exit 1; }
[[ $(readlink -f /home/larpus/models) == /home/larpus/models && -d /home/larpus/models/blobs && -d /home/larpus/models/manifests ]] || { echo 'Prepared model cache missing or redirected' >&2; exit 1; }
[[ -e /dev/dxg && -d /usr/lib/wsl/lib ]] || { echo 'WSL GPU device/libraries unavailable; no silent CPU deployment' >&2; exit 1; }
mapfile -t gpu_drivers < <(find /usr/lib/wsl/drivers -mindepth 2 -maxdepth 2 -type f -name libcuda.so.1.1 -printf '%h\n')
[[ ${#gpu_drivers[@]} == 1 && ${gpu_drivers[0]} =~ ^/usr/lib/wsl/drivers/nv_[a-z0-9]+\.inf_amd64_[a-f0-9]{16}$ ]] || { echo 'A single verified NVIDIA driver package is required; do not mount the entire DriverStore' >&2; exit 1; }
gpu_driver=${gpu_drivers[0]}
[[ $(podman info --format '{{.Host.Security.Rootless}}') == true ]] || { echo 'Rootless Podman required' >&2; exit 1; }
podman image exists "$1" && podman image exists "$2"
for name in larpus-agent larpus-model; do
  if podman container exists "$name"; then echo 'Existing Larpus deployment preserved; stop/review it before redeploying' >&2; exit 1; fi
done
if podman pod exists larpus-offline; then echo 'Existing Larpus pod preserved' >&2; exit 1; fi
(cd vendor/runtime-wheels && sha256sum --strict --check SHA256SUMS) >&2
(cd vendor/retrieval-models && sha256sum --strict --check --quiet SHA256SUMS) >&2
podman build --pull=never --network=none --build-arg "BASE_IMAGE=$1" -f deploy/windows-home/Containerfile -t localhost/larpus-agent:sealed . >&2
agent_image=$(podman image inspect localhost/larpus-agent:sealed --format '{{.Id}}')
model_image=$(podman image inspect "$2" --format '{{.Id}}')
# Named volume is never mounted into the model container. The image seeds its ownership.
if ! podman volume exists larpus-quarantine; then podman volume create larpus-quarantine >&2; fi
podman pod create --name larpus-offline --network=none --share=net --no-hosts \
  --infra-image="$1" --infra-command='/usr/bin/sleep 2147483647' >&2
podman run --detach --pull=never --name larpus-model --pod larpus-offline \
  --read-only --read-only-tmpfs=false --cap-drop=ALL --security-opt=no-new-privileges \
  --pids-limit=256 --memory=32g --cpus=16 --log-driver=none \
  --tmpfs=/tmp:rw,nosuid,nodev,noexec,size=1g \
  --device=/dev/dxg --mount=type=bind,src=/usr/lib/wsl/lib,dst=/usr/lib/wsl/lib,ro \
  --mount="type=bind,src=$gpu_driver,dst=$gpu_driver,ro" \
  --mount=type=bind,src=/home/larpus/models,dst=/models,ro \
  --env=HOME=/tmp --env=OLLAMA_HOST=127.0.0.1:11434 --env=OLLAMA_MODELS=/models \
  --env=OLLAMA_NO_CLOUD=1 --env=OLLAMA_NOPRUNE=1 --env=LD_LIBRARY_PATH=/usr/lib/wsl/lib \
  --entrypoint=/bin/ollama "$2" serve >&2
podman run --detach --pull=never --name larpus-agent --pod larpus-offline \
  --read-only --read-only-tmpfs=false --user=1000:1000 --cap-drop=ALL --security-opt=no-new-privileges \
  --pids-limit=64 --memory=12g --cpus=8 --log-driver=none \
  --tmpfs=/tmp:rw,nosuid,nodev,noexec,size=128m \
  --volume=larpus-quarantine:/app/data/quarantine:rw,noexec,nosuid,nodev \
  "$agent_image" >&2
printf '{"version":1,"distro":"Larpus","user":"larpus","agent_image":"%s","model_image":"%s","source_fingerprint":"%s","gpu_driver":"%s"}\n' "$agent_image" "$model_image" "$3" "$gpu_driver"
# A failed deployment leaves evidence for inspection; it never starts host inference.
