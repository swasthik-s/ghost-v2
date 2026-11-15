$ErrorActionPreference = "Stop"

$taskName = "GHOST Agent"
$sourceDir = Join-Path $PSScriptRoot "dist\GHOST-Agent"
$exeName = "GHOST-Agent.exe"
$sourceExe = Join-Path $sourceDir $exeName
$installDir = Join-Path $env:LOCALAPPDATA "Programs\GHOST-Agent"
$targetExe = Join-Path $installDir $exeName

if (-not (Test-Path $sourceExe)) {
    throw "GHOST Agent executable not found. Run .\build_windows.ps1 first. Expected: $sourceExe"
}

New-Item -ItemType Directory -Force -Path $installDir | Out-Null
Copy-Item -Path (Join-Path $sourceDir "*") -Destination $installDir -Recurse -Force

$action = New-ScheduledTaskAction -Execute $targetExe -WorkingDirectory $installDir
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "GHOST local MT5 telemetry agent and outbound cloud sync." -Force | Out-Null
Start-ScheduledTask -TaskName $taskName

Write-Host "GHOST Agent installed and started."
Write-Host "Executable: $targetExe"
Write-Host "Starts automatically when $env:USERNAME logs into Windows."
Write-Host "The agent waits safely when MT5 is unavailable. It does not place or modify trades."
Write-Host "Pairing configuration: $env:APPDATA\GHOST\agent.json"
