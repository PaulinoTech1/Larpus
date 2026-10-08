$ErrorActionPreference='Stop'
$sourceRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $sourceRoot
New-Item -ItemType Directory -Force -Path data | Out-Null
$before=python -c 'from runtime.security_scan import fingerprint; print(fingerprint())'
if ($LASTEXITCODE -ne 0 -or $before -notmatch '^[a-f0-9]{64}$') { throw 'Cannot fingerprint source' }
$archive=Join-Path $sourceRoot 'data/isolated-source.tar'
# Fixed project directories only: no data, owner profile, credentials or recordings.
tar.exe --exclude=__pycache__ -cf $archive runtime agents skills config scripts deploy requirements.txt .containerignore .gitattributes LICENSE LICENSE-NOTICE.md
if ($LASTEXITCODE -ne 0) { throw 'Source archive failed' }
$after=python -c 'from runtime.security_scan import fingerprint; print(fingerprint())'
if ($before -ne $after) { throw 'Source changed during export; discard this archive and repeat' }
$before | Set-Content -LiteralPath data/isolated-source.fingerprint -Encoding ascii
Write-Host "Source archive: $archive"
Write-Host "Build fingerprint: $before"
Write-Host 'Transfer this archive into the dedicated distro before disabling drive automount/interop.'
