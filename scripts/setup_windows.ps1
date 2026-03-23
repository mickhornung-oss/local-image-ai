[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Write-Step {
    param([string]$Message)
    Write-Host "[setup] $Message" -ForegroundColor Cyan
}

function Fail {
    param([string]$Message)
    Write-Error $Message
    exit 1
}

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-PythonLauncherVersions {
    $output = & cmd /c "py -0p 2>&1"
    if ($LASTEXITCODE -ne 0) {
        return @()
    }

    $entries = @()
    foreach ($line in $output) {
        $lineText = "$line"
        if ($lineText -match "^\s*-(?<version>\d+\.\d+)(?:-\d+)?\s+(?<path>.+)$") {
            $entries += [pscustomobject]@{
                Version = $Matches["version"]
                Path = $Matches["path"].Trim()
            }
        }
    }

    return $entries
}

function Select-CompatiblePython {
    $versions = Get-PythonLauncherVersions
    foreach ($target in @("3.10", "3.11")) {
        if ($versions | Where-Object { $_.Version -eq $target }) {
            return $target
        }
    }
    return $null
}

function Invoke-LoggedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory
    )

    Write-Host ">> $FilePath $($Arguments -join ' ')" -ForegroundColor DarkGray
    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        if ($LASTEXITCODE -ne 0) {
            Fail "Command failed: $FilePath $($Arguments -join ' ')"
        }
    } finally {
        Pop-Location
    }
}

function Install-ComfyUIFromZip {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][string]$TargetPath
    )

    $zipUrl = "https://github.com/comfyanonymous/ComfyUI/archive/refs/heads/master.zip"
    $tempZip = Join-Path ([System.IO.Path]::GetTempPath()) ("ComfyUI-" + [guid]::NewGuid().ToString() + ".zip")
    $tempExtract = Join-Path ([System.IO.Path]::GetTempPath()) ("ComfyUI-" + [guid]::NewGuid().ToString())

    Write-Step "Downloading ComfyUI source archive"
    Invoke-WebRequest -Uri $zipUrl -OutFile $tempZip

    try {
        Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force
        $expandedRoot = Join-Path $tempExtract "ComfyUI-master"
        if (-not (Test-Path (Join-Path $expandedRoot "main.py"))) {
            Fail "Downloaded ComfyUI archive is missing main.py"
        }

        if (Test-Path $TargetPath) {
            Remove-Item $TargetPath -Recurse -Force
        }

        Move-Item -Path $expandedRoot -Destination $TargetPath
    } finally {
        if (Test-Path $tempZip) {
            Remove-Item $tempZip -Force
        }
        if (Test-Path $tempExtract) {
            Remove-Item $tempExtract -Recurse -Force
        }
    }
}

$repoRoot = Get-RepoRoot
$vendorRoot = Join-Path $repoRoot "vendor"
$comfyRoot = Join-Path $vendorRoot "ComfyUI"
$venvRoot = Join-Path $comfyRoot "venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"
$venvPip = Join-Path $venvRoot "Scripts\pip.exe"
$clientRequirements = Join-Path $repoRoot "python\requirements.txt"
$comfyMainPy = Join-Path $comfyRoot "main.py"

Write-Step "Repository root: $repoRoot"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Fail @"
Python Launcher 'py' was not found.

Install a compatible Python version with one of these options:
  winget install Python.Python.3.10

Manual fallback:
  Install Python 3.10.x 64-bit from https://www.python.org/downloads/windows/
  and make sure the Python Launcher ('py') is installed.
"@
}

$gitCommand = Get-Command git -ErrorAction SilentlyContinue

$selectedPython = Select-CompatiblePython
if (-not $selectedPython) {
    $available = (Get-PythonLauncherVersions | ForEach-Object { $_.Version } | Sort-Object -Unique) -join ", "
    if (-not $available) {
        $available = "none detected"
    }

    Fail @"
No compatible Python runtime found via 'py -0p'.
Detected versions: $available

Install one of the supported versions:
  winget install Python.Python.3.10

Manual fallback:
  Install Python 3.10.x 64-bit from https://www.python.org/downloads/windows/
  and ensure the Python Launcher ('py') is enabled.
"@
}

Write-Step "Using Python $selectedPython via the Python Launcher"

if (-not (Test-Path $vendorRoot)) {
    New-Item -ItemType Directory -Path $vendorRoot | Out-Null
}

if (-not (Test-Path $comfyRoot)) {
    if ($gitCommand) {
        Write-Step "Cloning ComfyUI into vendor/ComfyUI"
        Invoke-LoggedCommand -FilePath "git" -Arguments @("clone", "https://github.com/comfyanonymous/ComfyUI", $comfyRoot) -WorkingDirectory $repoRoot
    } else {
        Write-Step "Git not found; using zip download fallback"
        Install-ComfyUIFromZip -RepoRoot $repoRoot -TargetPath $comfyRoot
    }
} elseif (-not (Test-Path $comfyMainPy)) {
    $entries = @(Get-ChildItem -Force $comfyRoot)
    $onlyPlaceholder = $entries.Count -eq 1 -and $entries[0].Name -eq ".gitkeep"
    $recoverableEntries = @(".gitkeep", "venv")
    $recoverable = $entries.Count -gt 0 -and @($entries | Where-Object { $_.Name -notin $recoverableEntries }).Count -eq 0
    if ($onlyPlaceholder) {
        Remove-Item $entries[0].FullName -Force
        if ($gitCommand) {
            Write-Step "Replacing placeholder directory with a fresh ComfyUI clone"
            Invoke-LoggedCommand -FilePath "git" -Arguments @("clone", "https://github.com/comfyanonymous/ComfyUI", $comfyRoot) -WorkingDirectory $repoRoot
        } else {
            Write-Step "Replacing placeholder directory with a zip-downloaded ComfyUI tree"
            Install-ComfyUIFromZip -RepoRoot $repoRoot -TargetPath $comfyRoot
        }
    } elseif ($recoverable) {
        if (Test-Path $comfyRoot) {
            Write-Step "Replacing incomplete vendor/ComfyUI contents"
            Remove-Item $comfyRoot -Recurse -Force
        }
        if ($gitCommand) {
            Invoke-LoggedCommand -FilePath "git" -Arguments @("clone", "https://github.com/comfyanonymous/ComfyUI", $comfyRoot) -WorkingDirectory $repoRoot
        } else {
            Install-ComfyUIFromZip -RepoRoot $repoRoot -TargetPath $comfyRoot
        }
    } elseif ($entries.Count -eq 0) {
        if ($gitCommand) {
            Write-Step "Cloning ComfyUI into empty vendor/ComfyUI"
            Invoke-LoggedCommand -FilePath "git" -Arguments @("clone", "https://github.com/comfyanonymous/ComfyUI", $comfyRoot) -WorkingDirectory $repoRoot
        } else {
            Write-Step "Git not found; using zip download fallback"
            Install-ComfyUIFromZip -RepoRoot $repoRoot -TargetPath $comfyRoot
        }
    } else {
        Fail "vendor/ComfyUI exists but does not look like a ComfyUI checkout. Remove it or fix the contents, then rerun setup."
    }
} else {
    Write-Step "ComfyUI already exists at vendor/ComfyUI"
}

if (-not (Test-Path $venvPython)) {
    Write-Step "Creating virtual environment with py -$selectedPython"
    Invoke-LoggedCommand -FilePath "py" -Arguments @("-$selectedPython", "-m", "venv", $venvRoot) -WorkingDirectory $repoRoot
} else {
    Write-Step "Virtual environment already exists at vendor/ComfyUI/venv"
}

Write-Step "Upgrading pip inside the ComfyUI venv"
Invoke-LoggedCommand -FilePath $venvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip") -WorkingDirectory $comfyRoot

Write-Step "Installing torch-directml"
Invoke-LoggedCommand -FilePath $venvPip -Arguments @("install", "torch-directml") -WorkingDirectory $comfyRoot

$requirementsPath = Join-Path $comfyRoot "requirements.txt"
if (-not (Test-Path $requirementsPath)) {
    Fail "ComfyUI requirements.txt was not found at $requirementsPath"
}

Write-Step "Installing ComfyUI requirements"
Invoke-LoggedCommand -FilePath $venvPip -Arguments @("install", "-r", $requirementsPath) -WorkingDirectory $comfyRoot

if (-not (Test-Path $clientRequirements)) {
    Fail "Client requirements file was not found at $clientRequirements"
}

Write-Step "Installing Python client requirements"
Invoke-LoggedCommand -FilePath $venvPip -Arguments @("install", "-r", $clientRequirements) -WorkingDirectory $repoRoot

foreach ($subDir in @("models\checkpoints", "models\vae", "models\loras", "output", "input")) {
    $target = Join-Path $comfyRoot $subDir
    if (-not (Test-Path $target)) {
        New-Item -ItemType Directory -Path $target | Out-Null
    }
}

Write-Host ""
Write-Host "Setup completed." -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Put an SDXL checkpoint into vendor/ComfyUI/models/checkpoints/"
Write-Host "  2. Run: powershell -ExecutionPolicy Bypass -File .\scripts\run_comfyui.ps1"
Write-Host "  3. In a second terminal run: powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1"
