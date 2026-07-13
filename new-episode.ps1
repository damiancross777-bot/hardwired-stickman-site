[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Title,

    [ValidateSet("Human Behaviour", "Animal Behaviour")]
    [string]$Category = "Human Behaviour"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run .\setup.ps1 first."
}

& $Python scripts\new_episode.py $Title --category $Category
