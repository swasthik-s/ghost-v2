$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    py -3.12 -m venv .venv
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt pyinstaller

& $venvPython -m PyInstaller --noconfirm --clean --onedir --name GHOST-Agent --collect-all fastapi --collect-all starlette --collect-all uvicorn --collect-all httpx agent_entry.py

Write-Host ""
Write-Host "GHOST Agent build output:"
Write-Host (Join-Path $PSScriptRoot "dist\GHOST-Agent\GHOST-Agent.exe")
Write-Host "Keep the complete dist\GHOST-Agent folder together when moving the application."
