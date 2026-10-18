$ErrorActionPreference='Continue'
Set-Location 'E:\speedzone_MS\LARPUS'
do {
    "study-notes continuous starting at $([DateTimeOffset]::Now.ToString('o'))" | Out-File -Append -Encoding utf8 data\study-notes.log
    python scripts\study-notes.py generate --hours 24 2>&1 | Out-File -Append -Encoding utf8 data\study-notes.log
    $result=$LASTEXITCODE
    if ($result -eq 0) {
        $status=python scripts\study-notes.py status | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and $status.windows_pending -eq 0) {
            python scripts\study-notes.py publish 2>&1 | Out-File -Append -Encoding utf8 data\study-notes.log
            if ($LASTEXITCODE -ne 0) { throw 'Study-note publication failed; see data/study-notes.log' }
            break
        }
    }
    Start-Sleep -Seconds 30
} while ($true)
