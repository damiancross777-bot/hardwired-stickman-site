[CmdletBinding()]
param(
    [string]$EpisodeFile = "",
    [string]$CommitMessage = "",
    [switch]$NoGit,
    [switch]$Preview
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run .\setup.ps1 first."
}

if ($EpisodeFile -and -not (Test-Path $EpisodeFile)) {
    throw "Episode file not found: $EpisodeFile"
}

Write-Host "Validating content..."
& $Python scripts\validate_content.py

Write-Host "Generating Pinterest and Instagram assets..."
& $Python scripts\make_social.py

Write-Host "Building the website..."
& $Python scripts\build_site.py

if ($Preview) {
    Write-Host "Starting preview at http://localhost:8000"
    & $Python -m http.server 8000 --directory public
    exit
}

if (-not $NoGit) {
    $insideGit = git rev-parse --is-inside-work-tree 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "This folder is not a Git repository. Run 'git init' or use -NoGit."
    }

    if (-not $CommitMessage) {
        if ($EpisodeFile) {
            $slug = [System.IO.Path]::GetFileNameWithoutExtension($EpisodeFile)
            $CommitMessage = "Publish Hardwired Stickman episode: $slug"
        } else {
            $CommitMessage = "Build Hardwired Stickman site"
        }
    }

    git add .
    $changes = git status --porcelain
    if ($changes) {
        git commit -m $CommitMessage
        git push
        Write-Host "Pushed changes. Cloudflare Pages will deploy from GitHub."
    } else {
        Write-Host "No Git changes to commit."
    }
}

Write-Host "Done. Built site: .\public"
Write-Host "Social package: .\output\social"
