[CmdletBinding()]
param(
    [string]$TargetDir = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-StrictMode -Version Latest

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-DefaultDesktopPath {
    $desktop = [Environment]::GetFolderPath("Desktop")
    if (-not [string]::IsNullOrWhiteSpace($desktop)) {
        return $desktop
    }
    return (Join-Path $HOME "Desktop")
}

$repoRoot = Get-RepoRoot
$startLauncher = Join-Path $repoRoot "Start_Local_Image_AI.cmd"
if (-not (Test-Path $startLauncher)) {
    Write-Error "Startdatei fehlt: $startLauncher"
    exit 1
}

$effectiveTargetDir = if ([string]::IsNullOrWhiteSpace($TargetDir)) { Get-DefaultDesktopPath } else { $TargetDir }
if (-not (Test-Path $effectiveTargetDir)) {
    New-Item -ItemType Directory -Path $effectiveTargetDir -Force | Out-Null
}

$shortcutPath = Join-Path $effectiveTargetDir "Local Image AI starten.lnk"
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $startLauncher
$shortcut.WorkingDirectory = $repoRoot
$shortcut.Description = "Startet die lokale Local Image AI App."
$shortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,220"
$shortcut.Save()

Write-Output "Desktop-Verknuepfung bereit:"
Write-Output $shortcutPath
exit 0
