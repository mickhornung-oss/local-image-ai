[CmdletBinding()]
param(
    [int]$Port = 8188
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

function Test-ComfyHttp {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri "$Url/system_stats" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -ne 200) {
            return @{
                Ok = $false
                Reason = "http status $($response.StatusCode)"
            }
        }

        try {
            $null = $response.Content | ConvertFrom-Json
        } catch {
            return @{
                Ok = $false
                Reason = "non-json response"
            }
        }

        return @{
            Ok = $true
            Reason = $null
        }
    } catch {
        return @{
            Ok = $false
            Reason = $_.Exception.Message
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

$startupTimeoutSeconds = 60
$lockStaleSeconds = 90
$statusStaleSeconds = 90
$result = $null
$exitCode = 0
$lockHandle = $null
$logsRoot = $null
$statusPath = $null
$lockPath = $null

try {
    $repoRoot = Get-RepoRoot
    $comfyRoot = Join-Path $repoRoot "vendor\ComfyUI"
    $venvPython = Join-Path $comfyRoot "venv\Scripts\python.exe"
    $mainPy = Join-Path $comfyRoot "main.py"
    $url = "http://127.0.0.1:$Port"
    $logsRoot = Join-Path $comfyRoot "logs"
    $stdoutLog = Join-Path $logsRoot "comfyui.stdout.log"
    $stderrLog = Join-Path $logsRoot "comfyui.stderr.log"
    $statusPath = Join-Path $logsRoot "run_comfyui.status.json"
    $lockPath = Join-Path $logsRoot "run_comfyui.lock.json"

    if (-not (Test-Path $comfyRoot)) {
        $result = @{ status = "error"; reason = "ComfyUI missing at vendor/ComfyUI" }
        $exitCode = 1
    } elseif (-not (Test-Path $venvPython)) {
        $result = @{ status = "error"; reason = "ComfyUI venv missing at vendor/ComfyUI/venv" }
        $exitCode = 1
    } elseif (-not (Test-Path $mainPy)) {
        $result = @{ status = "error"; reason = "ComfyUI main.py missing" }
        $exitCode = 1
    } else {
        if (-not (Test-Path $logsRoot)) {
            New-Item -ItemType Directory -Path $logsRoot | Out-Null
        }

        $httpProbe = Test-ComfyHttp -Url $url
        $statusPayload = Read-StatusFile -Path $statusPath
        if (Test-StaleStatusState -Path $statusPath -Payload $statusPayload -HttpOk $httpProbe.Ok -AgeThresholdSeconds $statusStaleSeconds) {
            Remove-IfExists -Path $statusPath
            $statusPayload = $null
        }

        $lockPayload = Read-StatusFile -Path $lockPath
        if (Test-StaleLockState -Path $lockPath -Payload $lockPayload -HttpOk $httpProbe.Ok -AgeThresholdSeconds $lockStaleSeconds) {
            Remove-IfExists -Path $lockPath
            $lockPayload = $null
        }

        if ($httpProbe.Ok) {
            Remove-IfExists -Path $lockPath
            $listenerPid = Get-ListenerPid -LocalPort $Port
            $result = @{
                status = "already_running"
                port = $Port
                pid = if ($null -ne $listenerPid) { $listenerPid } else { $null }
                url = $url
                mode = "directml"
                process = if ($null -ne $listenerPid) { Get-ProcessReference -Id $listenerPid } else { $null }
                updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
            }
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
                $httpProbe = Test-ComfyHttp -Url $url
                if ($httpProbe.Ok) {
                    $listenerPid = Get-ListenerPid -LocalPort $Port
                    $result = @{
                        status = "already_running"
                        port = $Port
                        pid = if ($null -ne $listenerPid) { $listenerPid } else { $null }
                        url = $url
                        mode = "directml"
                        process = if ($null -ne $listenerPid) { Get-ProcessReference -Id $listenerPid } else { $null }
                        updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
                    }
                    $null = Write-StatusFileAtomic -Path $statusPath -Payload $result
                } else {
                    $argumentList = @("`"$mainPy`"", "--directml", "--port", "$Port")
                    $process = Start-Process `
                        -FilePath $venvPython `
                        -ArgumentList $argumentList `
                        -WorkingDirectory $comfyRoot `
                        -RedirectStandardOutput $stdoutLog `
                        -RedirectStandardError $stderrLog `
                        -WindowStyle Hidden `
                        -PassThru

                    $deadline = (Get-Date).AddSeconds($startupTimeoutSeconds)
                    while ((Get-Date) -lt $deadline) {
                        Start-Sleep -Milliseconds 1500

                        $httpProbe = Test-ComfyHttp -Url $url
                        if ($httpProbe.Ok) {
                            $listenerPid = Get-ListenerPid -LocalPort $Port
                            $result = @{
                                status = "started"
                                port = $Port
                                pid = if ($null -ne $listenerPid) { $listenerPid } else { $process.Id }
                                url = $url
                                mode = "directml"
                                process = if ($null -ne $listenerPid) { Get-ProcessReference -Id $listenerPid } else { Get-ProcessReference -Id $process.Id }
                                updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
                            }
                            break
                        }

                        $runningProcess = Get-Process -Id $process.Id -ErrorAction SilentlyContinue
                        if ($null -eq $runningProcess) {
                            $result = @{
                                status = "error"
                                reason = "ComfyUI process exited before HTTP readiness; see vendor/ComfyUI/logs/comfyui.stderr.log"
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
                            reason = "timeout waiting for ComfyUI HTTP readiness on port $Port"
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

$stdoutPayload = [pscustomobject]@{
    status = if ($result.ContainsKey("status")) { $result.status } else { $null }
    reason = if ($result.ContainsKey("reason")) { $result.reason } else { $null }
    port = if ($result.ContainsKey("port")) { $result.port } else { $null }
    pid = if ($result.ContainsKey("pid")) { $result.pid } else { $null }
    url = if ($result.ContainsKey("url")) { $result.url } else { $null }
    mode = if ($result.ContainsKey("mode")) { $result.mode } else { $null }
}
[Console]::Out.WriteLine((ConvertTo-StatusJson -Payload $stdoutPayload))
[Console]::Out.Flush()
exit $exitCode
