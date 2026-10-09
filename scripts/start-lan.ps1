param(
    [string]$Address = '192.168.1.2',
    [string]$Subnet = '192.168.1.0/24'
)
$env:LARPUS_HOST = $Address
$env:LARPUS_LAN_CIDR = $Subnet
Set-Location (Split-Path $PSScriptRoot -Parent)
if (Test-Path -LiteralPath 'data/releases/active.json') {
    python scripts/releases.py start
    exit $LASTEXITCODE
}
if (-not (Test-Path -LiteralPath 'data/password.json')) {
    python -m runtime.auth
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
python -m runtime.gateway
