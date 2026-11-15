$ErrorActionPreference = "Stop"

$taskName = "GHOST Agent"
$installDir = Join-Path $env:LOCALAPPDATA "Programs\GHOST-Agent"

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

if (Test-Path $installDir) {
    Remove-Item -LiteralPath $installDir -Recurse -Force
}

Write-Host "GHOST Agent startup task and installed program removed."
Write-Host "Pairing credentials in %APPDATA%\GHOST were preserved. Remove that folder manually if you also want to unpair this PC."
