$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$env:LARPUS_ISOLATION='wsl-podman'
python -m runtime.isolation check
if ($LASTEXITCODE -ne 0) { throw 'Isolation preflight failed. Host fallback is prohibited.' }
python -m runtime.gateway
exit $LASTEXITCODE
