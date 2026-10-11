$ErrorActionPreference='Continue'
Set-Location 'E:\speedzone_MS\LARPUS'
$exceptionFile='data\study-notes-exception.json'
$deadline=$null
if (Test-Path -LiteralPath $exceptionFile) {
    $exception=Get-Content -Raw -LiteralPath $exceptionFile | ConvertFrom-Json
    $parsed=[DateTimeOffset]::Parse($exception.until)
    if ($parsed -gt [DateTimeOffset]::Now) { $deadline=$parsed }
}
try {
    do {
        $hours=13.75
        if ($null -ne $deadline) {
            $hours=($deadline-[DateTimeOffset]::Now).TotalHours
            if ($hours -le 0) { break }
        }
        "study-notes starting at $([DateTimeOffset]::Now.ToString('o')); hours=$hours; exception_until=$deadline" | Out-File -Append -Encoding utf8 data\study-notes.log
        python scripts\study-notes.py generate --hours $hours 2>&1 | Out-File -Append -Encoding utf8 data\study-notes.log
        if ($null -eq $deadline -or [DateTimeOffset]::Now -ge $deadline) { break }
        # An interrupted worker can resume committed windows during this exception.
        Start-Sleep -Seconds 30
    } while ($true)
    python scripts\study-notes.py publish 2>&1 | Out-File -Append -Encoding utf8 data\study-notes.log
} finally {
    if ($null -ne $deadline) {
        $task=Get-ScheduledTask -TaskName 'LARPUS Study Notes'
        $task.Settings.ExecutionTimeLimit='PT14H'
        Set-ScheduledTask -TaskName $task.TaskName -Settings $task.Settings | Out-Null
    }
}
