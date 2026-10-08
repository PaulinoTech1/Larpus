# Administrator only. Targets specified Ollama executables, never all Python.
param([Parameter(Mandatory=$true)][string[]]$Executable)
$ErrorActionPreference = 'Stop'
$resolvedPaths = @($Executable | ForEach-Object {
    $resolved = (Resolve-Path -LiteralPath $_).Path
    if ([IO.Path]::GetExtension($resolved) -ne '.exe') { throw 'Specify executable files.' }
    $resolved
})
# Block every IPv4/IPv6 destination except loopback. Block rules take precedence.
$remoteRanges = @('0.0.0.0-126.255.255.255','128.0.0.0-255.255.255.255','::','::2-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')
for ($i = 0; $i -lt $resolvedPaths.Count; $i++) {
    New-NetFirewallRule -Name "Larpus-Ollama-Egress-$i" `
        -DisplayName "Larpus Ollama non-loopback egress $i" `
        -Direction Outbound -Action Block -Program $resolvedPaths[$i] `
        -RemoteAddress $remoteRanges -Protocol Any -Profile Any
}
Write-Host 'Ollama non-loopback egress rules installed. Model downloads are now blocked too.'
Write-Host 'Include every Ollama runner executable in the supplied paths; verify after updates.'
