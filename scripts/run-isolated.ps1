$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (Test-Path -LiteralPath 'data/releases/active.json') {
    python scripts/releases.py start
    exit $LASTEXITCODE
}
$env:LARPUS_ISOLATION='wsl-podman'
python -m runtime.isolation check
if ($LASTEXITCODE -ne 0) { throw 'Isolation preflight failed. Host fallback is prohibited.' }
python -m runtime.gateway
exit $LASTEXITCODE
