#Requires -Version 5.1
$ErrorActionPreference = "Stop"

function Test-Gh {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Write-Host ""
        Write-Host "gh (GitHub CLI) is not installed or not on your PATH." -ForegroundColor Red
        Write-Host ""
        Write-Host "Install it, then run this script again:"
        Write-Host "  • Windows (winget):  winget install GitHub.cli"
        Write-Host "  • Mac (Homebrew):    brew install gh"
        Write-Host "  • Other:             https://cli.github.com/"
        Write-Host ""
        exit 1
    }
    $null = gh auth status 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "gh is not logged in or not set up for this repo." -ForegroundColor Red
        Write-Host ""
        Write-Host "Fix it by running:  gh auth login"
        Write-Host "  Then choose GitHub.com, HTTPS, and authenticate (browser or token)."
        Write-Host ""
        exit 1
    }
}

function Get-LatestReleaseTag {
    try {
        $json = gh release list --limit 1 --json tagName 2>$null | ConvertFrom-Json
        $tag = $json[0].tagName
        if ([string]::IsNullOrWhiteSpace($tag) -or $tag -eq "null") { return $null }
        return $tag
    } catch {
        return $null
    }
}

function Get-ParsedSemver {
    param([string]$Tag)
    $t = $Tag -replace '^v', ''
    $parts = $t -split '\.'
    $major = if ($parts[0] -match '^\d+$') { [int]$parts[0] } else { 0 }
    $minor = if ($parts.Count -gt 1 -and $parts[1] -match '^\d+$') { [int]$parts[1] } else { 0 }
    $patch = if ($parts.Count -gt 2 -and $parts[2] -match '^\d+$') { [int]$parts[2] } else { 0 }
    return @{ Major = $major; Minor = $minor; Patch = $patch }
}

function Get-BumpedVersion {
    param($Current, [string]$BumpType)
    switch ($BumpType) {
        "major" { return @{ Major = $Current.Major + 1; Minor = 0; Patch = 0 } }
        "minor" { return @{ Major = $Current.Major; Minor = $Current.Minor + 1; Patch = 0 } }
        "patch" { return @{ Major = $Current.Major; Minor = $Current.Minor; Patch = $Current.Patch + 1 } }
        default { return @{ Major = 0; Minor = 0; Patch = 0 } }
    }
}

function Get-BumpChoice {
    param($Current)
    $vMajor = Get-BumpedVersion -Current $Current -BumpType "major"
    $vMinor = Get-BumpedVersion -Current $Current -BumpType "minor"
    $vPatch = Get-BumpedVersion -Current $Current -BumpType "patch"
    $sMajor = "v$($vMajor.Major).$($vMajor.Minor).$($vMajor.Patch)"
    $sMinor = "v$($vMinor.Major).$($vMinor.Minor).$($vMinor.Patch)"
    $sPatch = "v$($vPatch.Major).$($vPatch.Minor).$($vPatch.Patch)"
    while ($true) {
        Write-Host ""
        Write-Host "Next version:"
        Write-Host "  1) major  → $sMajor"
        Write-Host "  2) minor  → $sMinor"
        Write-Host "  3) patch  → $sPatch"
        $choice = Read-Host "Choice [1-3]"
        switch ($choice) {
            "1" { return "major" }
            "2" { return "minor" }
            "3" { return "patch" }
            default { Write-Host "Enter 1, 2, or 3." }
        }
    }
}

function Get-Description {
    return (Read-Host "Short description for title").Trim()
}

function Test-Confirm {
    $confirm = Read-Host "Type 'yes' to create the release"
    return $confirm -ceq "yes"
}

function New-GhRelease {
    param([string]$Version, [string]$Title)
    gh release create "v$Version" --title $Title --generate-notes
}

# --- main ---
if ($args -contains "-h" -or $args -contains "--help") {
    Write-Host "Usage: .\create-release.ps1"
    Write-Host "  Requires: gh (GitHub CLI), authenticated and in a git repo with a GitHub remote."
    exit 0
}

Test-Gh

$latestTag = Get-LatestReleaseTag
if (-not $latestTag) {
    $latestTag = "v0.0.0"
    Write-Host "No existing releases found. Starting from $latestTag"
} else {
    Write-Host "Latest release: $latestTag"
}

$current = Get-ParsedSemver -Tag $latestTag
$bumpType = Get-BumpChoice -Current $current
$next = Get-BumpedVersion -Current $current -BumpType $bumpType
$newVersion = "$($next.Major).$($next.Minor).$($next.Patch)"

$description = Get-Description
if ([string]::IsNullOrWhiteSpace($description)) {
    Write-Error "Description cannot be empty."
    exit 1
}

$title = "v$newVersion - $description"

Write-Host ""
Write-Host "--- Summary ---"
Write-Host "  Tag:    v$newVersion"
Write-Host "  Title:  $title"
Write-Host "  Notes:  --generate-notes (from commits/PRs)"
Write-Host ""

if (-not (Test-Confirm)) {
    Write-Host "Aborted."
    exit 0
}

New-GhRelease -Version $newVersion -Title $title
Write-Host "Release v$newVersion created."
