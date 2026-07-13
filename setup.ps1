[CmdletBinding()]
param(
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Creating Python virtual environment..."
& $PythonCommand -m venv .venv

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
Write-Host "Installing dependencies..."
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt

Write-Host "Building starter output..."
& $Python scripts\validate_content.py
& $Python scripts\make_social.py
& $Python scripts\build_site.py

Write-Host ""
Write-Host "Setup complete."
Write-Host "Preview the site with:"
Write-Host "  .\.venv\Scripts\python.exe -m http.server 8000 --directory public"
Write-Host "Then open http://localhost:8000"
