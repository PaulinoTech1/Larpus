param([switch]$WriteConfig)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$command=Get-Command tailscale.exe -ErrorAction SilentlyContinue
$exe=if ($command) { $command.Source } else { Join-Path $env:ProgramFiles 'Tailscale/tailscale.exe' }
if (-not (Test-Path -LiteralPath $exe)) {
    Write-Output 'Tailscale is not installed. Install the official Windows client and sign in; see docs/TAILSCALE_DEMO.md.'
    exit 1
}
$raw=& $exe status --json
if ($LASTEXITCODE -ne 0) { throw 'Unable to read Tailscale status.' }
$state=$raw | ConvertFrom-Json
if ($state.BackendState -ne 'Running' -or -not $state.Self.Online) { throw 'Sign in to Tailscale and connect this PC first.' }
$hostname=$state.Self.DNSName.TrimEnd('.')
$user=$state.User.PSObject.Properties[[string]$state.Self.UserID].Value
if (-not $user.LoginName) { throw 'Owner login not available. Use an untagged owner device.' }
Write-Output "PC HTTPS name: $hostname"
Write-Output ('PC Tailscale addresses: '+($state.Self.TailscaleIPs -join ', '))
Write-Output 'Review the Pixel-only policy and confirm no broad existing ACL/grant permits other clients.'
Write-Output 'This command does not enable Serve, Funnel, routing or firewall rules.'
if ($WriteConfig) {
    $directory=Join-Path $root 'data/tailscale'
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $path=Join-Path $directory 'bridge.json'
    if (Test-Path -LiteralPath $path) { throw 'Config exists; retained without replacement.' }
    $json=@{hostname=$hostname;owner_login=$user.LoginName;port=8088} | ConvertTo-Json
    [IO.File]::WriteAllText($path,$json+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
    python (Join-Path $root 'scripts/tailscale_bridge.py') --config $path --check
    if ($LASTEXITCODE -ne 0) { throw 'Bridge preflight failed. Config retained for inspection; nothing exposed.' }
}
