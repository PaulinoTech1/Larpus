# Run once in an Administrator PowerShell. Does not change the network profile.
param(
    [string]$Address = '192.168.1.2',
    [string]$Subnet = '192.168.1.0/24',
    [string]$Interface = 'Wi-Fi 2'
)
$ErrorActionPreference = 'Stop'
$pythonPath = (Get-Command python -CommandType Application | Select-Object -First 1).Source
New-NetFirewallRule -Name 'Larpus-Home-LAN' -DisplayName 'Larpus home LAN only' `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080 `
    -LocalAddress $Address -RemoteAddress $Subnet -InterfaceAlias $Interface `
    -Program $pythonPath -Profile Any -EdgeTraversalPolicy Block
