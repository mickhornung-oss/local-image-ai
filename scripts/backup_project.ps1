param(
    [string]$OutputDir = "",
    [string]$Label = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Get-RepoRoot {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git ist nicht installiert oder nicht im PATH."
    }

    $root = git -C $PSScriptRoot rev-parse --show-toplevel 2>$null
    if (-not $root) {
        throw "Kein Git-Worktree gefunden."
    }

    return $root.Trim()
}

function Get-IncludedFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $entries = @(git -C $RepoRoot ls-files --cached --modified --others --exclude-standard)
    $files = @()
    foreach ($entry in $entries) {
        if ([string]::IsNullOrWhiteSpace($entry)) {
            continue
        }
        $normalized = $entry.Replace("/", "\")
        if ($normalized.StartsWith(".git\")) {
            continue
        }
        $absolutePath = Join-Path $RepoRoot $normalized
        if (-not (Test-Path -LiteralPath $absolutePath -PathType Leaf)) {
            continue
        }
        $files += $normalized
    }

    return $files | Sort-Object -Unique
}

function Get-SafeLabel {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $safe = [System.Text.RegularExpressions.Regex]::Replace($Value.Trim().ToLowerInvariant(), "[^a-z0-9_-]+", "-")
    $safe = $safe.Trim("-")
    return $safe
}

function Add-FileToZip {
    param(
        [Parameter(Mandatory = $true)]
        [System.IO.Compression.ZipArchive]$Zip,
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $absolutePath = Join-Path $RepoRoot $RelativePath
    $entryName = $RelativePath.Replace("\", "/")
    $entry = $Zip.CreateEntry($entryName, [System.IO.Compression.CompressionLevel]::Optimal)
    $entry.LastWriteTime = [DateTimeOffset]::new((Get-Item -LiteralPath $absolutePath).LastWriteTimeUtc)

    $entryStream = $entry.Open()
    $fileStream = [System.IO.File]::OpenRead($absolutePath)
    try {
        $fileStream.CopyTo($entryStream)
    }
    finally {
        $fileStream.Dispose()
        $entryStream.Dispose()
    }
}

function Add-TextToZip {
    param(
        [Parameter(Mandatory = $true)]
        [System.IO.Compression.ZipArchive]$Zip,
        [Parameter(Mandatory = $true)]
        [string]$EntryName,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $entry = $Zip.CreateEntry($EntryName, [System.IO.Compression.CompressionLevel]::Optimal)
    $stream = $entry.Open()
    $writer = [System.IO.StreamWriter]::new($stream, [System.Text.UTF8Encoding]::new($false))
    try {
        $writer.Write($Content)
    }
    finally {
        $writer.Dispose()
        $stream.Dispose()
    }
}

$repoRoot = Get-RepoRoot
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$head = (git -C $repoRoot rev-parse --short HEAD).Trim()
$statusLines = @(git -C $repoRoot status --short)
$dirty = $statusLines.Count -gt 0
$fileList = @(Get-IncludedFiles -RepoRoot $repoRoot)

if ($fileList.Count -eq 0) {
    throw "Keine backup-faehigen Projektdateien gefunden."
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $backupRoot = Join-Path $repoRoot "local_backups"
}
else {
    $backupRoot = $OutputDir
    if (-not [System.IO.Path]::IsPathRooted($backupRoot)) {
        $backupRoot = Join-Path $repoRoot $backupRoot
    }
}

New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

$nameParts = @("project-backup", $timestamp, $head)
if ($dirty) {
    $nameParts += "dirty"
}
if (-not [string]::IsNullOrWhiteSpace($Label)) {
    $safeLabel = Get-SafeLabel -Value $Label
    if (-not [string]::IsNullOrWhiteSpace($safeLabel)) {
        $nameParts += $safeLabel
    }
}

$archiveName = ($nameParts -join "_") + ".zip"
$archivePath = Join-Path $backupRoot $archiveName

if (Test-Path -LiteralPath $archivePath) {
    throw "Backup-Datei existiert bereits: $archivePath"
}

$manifest = [ordered]@{
    created_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    repo_root = $repoRoot
    git_head = $head
    git_dirty = $dirty
    included_file_count = $fileList.Count
    included_files = $fileList | ForEach-Object { $_.Replace("\", "/") }
    restore_hint = "ZIP zuerst in einen separaten Ordner entpacken und dann gewuenschte Dateien bewusst zurueckkopieren oder per Git vergleichen."
}
$manifestJson = $manifest | ConvertTo-Json -Depth 4

$fileHandle = [System.IO.File]::Open($archivePath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
$zip = [System.IO.Compression.ZipArchive]::new($fileHandle, [System.IO.Compression.ZipArchiveMode]::Create, $false)
try {
    foreach ($relativePath in $fileList) {
        Add-FileToZip -Zip $zip -RepoRoot $repoRoot -RelativePath $relativePath
    }
    Add-TextToZip -Zip $zip -EntryName "backup_manifest.json" -Content $manifestJson
}
finally {
    $zip.Dispose()
    $fileHandle.Dispose()
}

Write-Host "Backup erstellt"
Write-Host "Pfad: $archivePath"
if ($dirty) {
    Write-Host "Git-Stand: $head (mit lokalen Aenderungen)"
}
else {
    Write-Host "Git-Stand: $head"
}
Write-Host "Dateien: $($fileList.Count)"
Write-Host "Restore: ZIP zuerst in einen separaten Ordner entpacken und dann bewusst zurueckkopieren."
