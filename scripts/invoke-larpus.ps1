# Run one command in the Larpus distribution as larpus.
# Refuses a restricted Windows token. Codex unelevated and MXC both get
# Wsl/E_ACCESSDENIED from WslService before this command would exist.
param(
    [Parameter(Mandatory = $true, ValueFromRemainingArguments = $true)]
    [string[]]$Command
)

$ErrorActionPreference = 'Stop'

if (-not ('LarpusTokenCheck' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class LarpusTokenCheck {
    [DllImport("advapi32.dll", SetLastError = true)]
    public static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);
    [DllImport("advapi32.dll", SetLastError = true)]
    public static extern bool IsTokenRestricted(IntPtr token);
    [DllImport("kernel32.dll")]
    public static extern IntPtr GetCurrentProcess();
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool CloseHandle(IntPtr handle);
}
'@
}

$token = [IntPtr]::Zero
$opened = [LarpusTokenCheck]::OpenProcessToken([LarpusTokenCheck]::GetCurrentProcess(), 0x0008, [ref]$token)
if (-not $opened) {
    [Console]::Error.WriteLine('WSL launch refused: the process token could not be read. See docs/WSL_SANDBOX_ACCESS.md.')
    exit 2
}
try {
    $restricted = [LarpusTokenCheck]::IsTokenRestricted($token)
} finally {
    [void][LarpusTokenCheck]::CloseHandle($token)
}
if ($restricted) {
    [Console]::Error.WriteLine('WSL launch refused: this process token is restricted. Run scripts/invoke-larpus.ps1 from an owner PowerShell outside the Codex sandbox. See docs/WSL_SANDBOX_ACCESS.md.')
    exit 2
}

$wsl = Join-Path $env:SystemRoot 'System32\wsl.exe'
# Windows PowerShell turns native stderr into a terminating error when
# ErrorActionPreference is Stop. WSL and Python write warnings there while
# the measurement is still running.
$previousPreference = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    & $wsl --distribution Larpus --user larpus --exec @Command
    $code = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $previousPreference
}
if ($null -eq $code) { $code = 1 }
exit $code
