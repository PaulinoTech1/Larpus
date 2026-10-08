#!/usr/bin/env bash
# Explicit ONLINE preparation only; no user prompts or credentials enter this phase.
set -euo pipefail
export XDG_RUNTIME_DIR=/run/user/1000
[[ $(id -un) == larpus && $(id -u) == 1000 ]] || { echo 'Dedicated larpus UID 1000 required' >&2; exit 1; }
cd "$(dirname "$0")/../.."
podman pull docker.io/library/python:3.12-slim-bookworm
podman pull docker.io/ollama/ollama:latest
mkdir -p vendor/runtime-wheels /home/larpus/models
python3 -m venv vendor/build-env
vendor/build-env/bin/python -m pip wheel -r requirements.txt --wheel-dir vendor/runtime-wheels
(cd vendor/runtime-wheels && sha256sum *.whl > SHA256SUMS)
podman run --detach --name larpus-prepare --cap-drop=ALL --security-opt=no-new-privileges \
  --read-only --read-only-tmpfs=false --tmpfs=/tmp:rw,nosuid,nodev,noexec,size=1g \
  --env=HOME=/tmp --env=OLLAMA_MODELS=/models --env=OLLAMA_NO_CLOUD=1 \
  --mount=type=bind,src=/home/larpus/models,dst=/models \
  docker.io/ollama/ollama:latest
# No ports published; this temporary server receives only public model downloads.
trap 'podman stop larpus-prepare >/dev/null 2>&1 || true' EXIT
sleep 3
mapfile -t tags < <(python3 -c "import json,pathlib;print('\n'.join(sorted({json.loads(p.read_text())['model'] for p in pathlib.Path('agents/personas').glob('*.json')})))")
for tag in "${tags[@]}"; do podman exec larpus-prepare /bin/ollama pull "$tag"; done
podman exec larpus-prepare /bin/ollama list
podman stop larpus-prepare
trap - EXIT
podman rm larpus-prepare
python_digest=$(podman image inspect docker.io/library/python:3.12-slim-bookworm --format '{{index .RepoDigests 0}}')
ollama_digest=$(podman image inspect docker.io/ollama/ollama:latest --format '{{index .RepoDigests 0}}')
printf '%s\n%s\n' "$python_digest" "$ollama_digest" > /home/larpus/image-digests.txt
echo 'Online preparation complete. Keep image-digests.txt, wheel hashes and model cache.'
