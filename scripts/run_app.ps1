[CmdletBinding()]
param(
    [int]$Port = 8090,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-StrictMode -Version Latest

. (Join-Path $PSScriptRoot "_status_helpers.ps1")

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-ListenerPid {
    param([int]$LocalPort)

    $listeners = @(Get-NetTCPConnection -LocalPort $LocalPort -State Listen -ErrorAction SilentlyContinue |
        Sort-Object OwningProcess -Unique)

    if ($listeners.Count -gt 0) {
        return [int]$listeners[0].OwningProcess
    }

    return $null
}

function Test-AppHealth {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri "$Url/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -ne 200) {
            return @{
                Ok = $false
                Reason = "http status $($response.StatusCode)"
                Payload = $null
            }
        }

        try {
            $payload = $response.Content | ConvertFrom-Json
        } catch {
            return @{
                Ok = $false
                Reason = "non-json response"
                Payload = $null
            }
        }

        if (
            $null -eq $payload -or
            -not ($payload.PSObject.Properties.Name -contains "status") -or
            "$($payload.status)" -ne "ok" -or
            -not ($payload.PSObject.Properties.Name -contains "service") -or
            "$($payload.service)" -ne "local-image-app"
        ) {
            return @{
                Ok = $false
                Reason = "invalid health payload"
                Payload = $payload
            }
        }

        return @{
            Ok = $true
            Reason = $null
            Payload = $payload
        }
    } catch {
        return @{
            Ok = $false
            Reason = $_.Exception.Message
            Payload = $null
        }
    }
}

function Remove-IfExists {
    param([string]$Path)

    if (Test-Path $Path) {
        Remove-Item $Path -Force -ErrorAction SilentlyContinue
    }
}

function Stop-ReferencedProcessIfMatch {
    param([object]$Reference)

    if (Test-ProcessReference -Reference $Reference) {
        Stop-Process -Id ([int]$Reference.pid) -Force -ErrorAction SilentlyContinue
    }
}

function Test-StaleStatusState {
    param(
        [string]$Path,
        [object]$Payload,
        [bool]$HttpOk,
        [int]$AgeThresholdSeconds
    )

    if (-not (Test-ValidStatusPayload -Payload $Payload)) {
        $age = Get-FileAgeSeconds -Path $Path
        return ($null -ne $age) -and ($age -gt 5)
    }

    $processReference = $null
    if ($Payload.PSObject.Properties.Name -contains "process") {
        $processReference = $Payload.process
    }

    if ($null -ne $processReference -and -not (Test-ProcessReference -Reference $processReference)) {
        return $true
    }

    $ageSeconds = Get-FileAgeSeconds -Path $Path
    if (-not $HttpOk -and $null -ne $ageSeconds -and $ageSeconds -gt $AgeThresholdSeconds) {
        return $true
    }

    return $false
}

function Test-StaleLockState {
    param(
        [string]$Path,
        [object]$Payload,
        [bool]$HttpOk,
        [int]$AgeThresholdSeconds
    )

    if (-not (Test-ValidStatusPayload -Payload $Payload)) {
        return $false
    }

    $ownerReference = $null
    if ($Payload.PSObject.Properties.Name -contains "owner") {
        $ownerReference = $Payload.owner
    }

    if ($null -ne $ownerReference -and -not (Test-ProcessReference -Reference $ownerReference)) {
        return $true
    }

    $ageSeconds = Get-FileAgeSeconds -Path $Path
    if (-not $HttpOk -and $null -ne $ageSeconds -and $ageSeconds -gt $AgeThresholdSeconds) {
        Stop-ReferencedProcessIfMatch -Reference $ownerReference
        return $true
    }

    return $false
}

function New-LockHandle {
    param(
        [string]$Path,
        [object]$Payload
    )

    $directory = Split-Path -Parent $Path
    if (-not (Test-Path $directory)) {
        New-Item -ItemType Directory -Path $directory | Out-Null
    }

    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
    $writer = New-Object System.IO.StreamWriter($stream, [System.Text.Encoding]::ASCII)
    $writer.AutoFlush = $true
    $json = ConvertTo-StatusJson -Payload $Payload
    $writer.Write($json)
    $writer.Flush()
    $stream.Flush()

    return [pscustomobject]@{
        Path = $Path
        Stream = $stream
        Writer = $writer
    }
}

function Close-LockHandle {
    param([object]$Handle)

    if ($null -eq $Handle) {
        return
    }

    try {
        if ($null -ne $Handle.Writer) {
            $Handle.Writer.Dispose()
        }
    } catch {
    }

    try {
        if ($null -ne $Handle.Stream) {
            $Handle.Stream.Dispose()
        }
    } catch {
    }

    Remove-IfExists -Path $Handle.Path
}

function Get-CompatiblePyVersion {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -eq $launcher) {
        return $null
    }

    $installed = & py -0p 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $null
    }

    foreach ($version in @("3.10", "3.11")) {
        if ($installed -match "3\.$($version.Split('.')[1])") {
            return $version
        }
    }

    return $null
}

function Ensure-RequestsInstalled {
    param(
        [string]$PythonExe,
        [string]$RequirementsPath
    )

    & $PythonExe -c "import requests; import PIL" *> $null
    if ($LASTEXITCODE -eq 0) {
        return
    }

    & $PythonExe -m pip install -r $RequirementsPath *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install python/requirements.txt"
    }
}

function Ensure-AppPython {
    param(
        [string]$RepoRoot,
        [string]$RequirementsPath
    )

    $vendorPython = Join-Path $RepoRoot "vendor\ComfyUI\venv\Scripts\python.exe"
    if (Test-Path $vendorPython) {
        Ensure-RequestsInstalled -PythonExe $vendorPython -RequirementsPath $RequirementsPath
        return $vendorPython
    }

    $appPython = Join-Path $RepoRoot "venv\Scripts\python.exe"
    if (-not (Test-Path $appPython)) {
        $version = Get-CompatiblePyVersion
        if ($null -eq $version) {
            throw "No compatible py launcher target found for app venv"
        }

        $appVenvPath = Join-Path $RepoRoot "venv"
        & py "-$version" -m venv $appVenvPath *> $null
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $appPython)) {
            throw "Failed to create app venv with py -$version"
        }
    }

    Ensure-RequestsInstalled -PythonExe $appPython -RequirementsPath $RequirementsPath
    return $appPython
}

function Try-OpenBrowser {
    param([string]$Url)

    try {
        Start-Process $Url | Out-Null
        return $true
    } catch {
        return $false
    }
}

$startupTimeoutSeconds = 45
$lockStaleSeconds = 90
$statusStaleSeconds = 90
$result = $null
$exitCode = 0
$lockHandle = $null
$logsRoot = $null
$statusPath = $null
$lockPath = $null
$browserOpened = $false

try {
    $repoRoot = Get-RepoRoot
    $appScript = Join-Path $repoRoot "python\app_server.py"
    $requirementsPath = Join-Path $repoRoot "python\requirements.txt"
    $logsRoot = Join-Path $repoRoot "vendor\ComfyUI\logs"
    $statusPath = Join-Path $logsRoot "run_app.status.json"
    $lockPath = Join-Path $logsRoot "run_app.lock.json"
    $stdoutLog = Join-Path $logsRoot "app_server.stdout.log"
    $stderrLog = Join-Path $logsRoot "app_server.stderr.log"
    $url = "http://127.0.0.1:$Port"

    if (-not (Test-Path $appScript)) {
        $result = @{ status = "error"; reason = "python/app_server.py missing" }
        $exitCode = 1
    } elseif (-not (Test-Path $requirementsPath)) {
        $result = @{ status = "error"; reason = "python/requirements.txt missing" }
        $exitCode = 1
    } else {
        if (-not (Test-Path $logsRoot)) {
            New-Item -ItemType Directory -Path $logsRoot | Out-Null
        }

        $healthProbe = Test-AppHealth -Url $url
        $statusPayload = Read-StatusFile -Path $statusPath
        if (Test-StaleStatusState -Path $statusPath -Payload $statusPayload -HttpOk $healthProbe.Ok -AgeThresholdSeconds $statusStaleSeconds) {
            Remove-IfExists -Path $statusPath
            $statusPayload = $null
        }

        $lockPayload = Read-StatusFile -Path $lockPath
        if (Test-StaleLockState -Path $lockPath -Payload $lockPayload -HttpOk $healthProbe.Ok -AgeThresholdSeconds $lockStaleSeconds) {
            Remove-IfExists -Path $lockPath
            $lockPayload = $null
        }

        if ($healthProbe.Ok) {
            Remove-IfExists -Path $lockPath
            $listenerPid = Get-ListenerPid -LocalPort $Port
            $result = @{
                status = "already_running"
                port = $Port
                pid = if ($null -ne $listenerPid) { $listenerPid } else { $null }
                url = $url
                process = if ($null -ne $listenerPid) { Get-ProcessReference -Id $listenerPid } else { $null }
                updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
            }
            $null = Write-StatusFileAtomic -Path $statusPath -Payload $result
        } else {
            $listenerPid = Get-ListenerPid -LocalPort $Port
            if ($null -ne $listenerPid) {
                $result = @{
                    status = "error"
                    reason = "port_in_use_by_other_process"
                    updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
                }
                $exitCode = 1
                $null = Write-StatusFileAtomic -Path $statusPath -Payload $result
            } else {
                $lockPayload = Read-StatusFile -Path $lockPath
                if (Test-ValidStatusPayload -Payload $lockPayload) {
                    $result = @{ status = "busy"; reason = "startup_in_progress" }
                } else {
                    try {
                        $lockHandle = New-LockHandle -Path $lockPath -Payload @{
                            status = "busy"
                            reason = "startup_in_progress"
                            owner = Get-ProcessReference -Id $PID
                            created_at_utc = (Get-Date).ToUniversalTime().ToString("o")
                        }
                    } catch [System.IO.IOException] {
                        $result = @{ status = "busy"; reason = "startup_in_progress" }
                    }
                }

                if ($null -eq $result) {
                    $healthProbe = Test-AppHealth -Url $url
                    if ($healthProbe.Ok) {
                        $listenerPid = Get-ListenerPid -LocalPort $Port
                        $result = @{
                            status = "already_running"
                            port = $Port
                            pid = if ($null -ne $listenerPid) { $listenerPid } else { $null }
                            url = $url
                            process = if ($null -ne $listenerPid) { Get-ProcessReference -Id $listenerPid } else { $null }
                            updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
                        }
                        $null = Write-StatusFileAtomic -Path $statusPath -Payload $result
                    } else {
                        $pythonExe = Ensure-AppPython -RepoRoot $repoRoot -RequirementsPath $requirementsPath
                        $process = Start-Process `
                            -FilePath $pythonExe `
                            -ArgumentList @("`"$appScript`"", "--host", "127.0.0.1", "--port", "$Port") `
                            -WorkingDirectory $repoRoot `
                            -RedirectStandardOutput $stdoutLog `
                            -RedirectStandardError $stderrLog `
                            -WindowStyle Hidden `
                            -PassThru

                        $deadline = (Get-Date).AddSeconds($startupTimeoutSeconds)
                        while ((Get-Date) -lt $deadline) {
                            Start-Sleep -Milliseconds 1000

                            $healthProbe = Test-AppHealth -Url $url
                            if ($healthProbe.Ok) {
                                $listenerPid = Get-ListenerPid -LocalPort $Port
                                $result = @{
                                    status = "started"
                                    port = $Port
                                    pid = if ($null -ne $listenerPid) { $listenerPid } else { $process.Id }
                                    url = $url
                                    process = if ($null -ne $listenerPid) { Get-ProcessReference -Id $listenerPid } else { Get-ProcessReference -Id $process.Id }
                                    updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
                                }
                                break
                            }

                            $runningProcess = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
                            if ($null -eq $runningProcess) {
                                $result = @{
                                    status = "error"
                                    reason = "app server exited before readiness; see vendor/ComfyUI/logs/app_server.stderr.log"
                                    updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
                                }
                                $exitCode = 1
                                break
                            }
                        }

                        if ($null -eq $result) {
                            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                            $result = @{
                                status = "error"
                                reason = "timeout waiting for app /health readiness on port $Port"
                                updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
                            }
                            $exitCode = 1
                        }

                        if ($result.status -ne "busy") {
                            $null = Write-StatusFileAtomic -Path $statusPath -Payload $result
                        }
                    }
                }
            }
        }
    }
} catch {
    $result = @{
        status = "error"
        reason = $_.Exception.Message
        updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    }
    $exitCode = 1
    if ($null -ne $statusPath) {
        $null = Write-StatusFileAtomic -Path $statusPath -Payload $result
    }
} finally {
    Close-LockHandle -Handle $lockHandle
}

$json = $null
if ($null -ne $result -and -not $result.ContainsKey("browser_opened")) {
    $result.browser_opened = $false
}

if ($OpenBrowser.IsPresent -and $null -ne $result -and $result.ContainsKey("status") -and $result.status -in @("started", "already_running")) {
    $browserOpened = Try-OpenBrowser -Url "$($result.url)"
    $result.browser_opened = $browserOpened
}

if ($null -ne $statusPath -and $null -ne $result -and $result.ContainsKey("status")) {
    $null = Write-StatusFileAtomic -Path $statusPath -Payload $result
}

$stdoutPayload = [pscustomobject]@{
    status = if ($result.ContainsKey("status")) { $result.status } else { $null }
    reason = if ($result.ContainsKey("reason")) { $result.reason } else { $null }
    port = if ($result.ContainsKey("port")) { $result.port } else { $null }
    pid = if ($result.ContainsKey("pid")) { $result.pid } else { $null }
    url = if ($result.ContainsKey("url")) { $result.url } else { $null }
    browser_opened = if ($result.ContainsKey("browser_opened")) { $result.browser_opened } else { $false }
}
[Console]::Out.WriteLine((ConvertTo-StatusJson -Payload $stdoutPayload))
[Console]::Out.Flush()
exit $exitCode
