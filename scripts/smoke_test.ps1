[CmdletBinding()]
param(
    [string]$Prompt = "portrait photo of a person, cinematic lighting, detailed skin, realistic lens rendering",
    [string]$NegativePrompt = "blurry, low quality, deformed, extra fingers",
    [int]$Width = 1024,
    [int]$Height = 1024,
    [int]$Steps = 20,
    [double]$Cfg = 6.5,
    [int]$TimeoutSeconds = 180,
    [int]$Port = 8188
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-StrictMode -Version Latest

. (Join-Path $PSScriptRoot "_status_helpers.ps1")

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Test-ComfyHttp {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri "$Url/system_stats" -UseBasicParsing -TimeoutSec 5
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Invoke-PythonJsonStatus {
    param(
        [string]$PythonExe,
        [string]$ScriptPath,
        [string[]]$Arguments
    )

    $output = & $PythonExe $ScriptPath @Arguments 2>&1
    return @{
        ExitCode = $LASTEXITCODE
        Payload = Get-JsonStatusFromLines -Lines @($output)
        Output = @($output)
    }
}

function Invoke-RunnerStatus {
    param(
        [string]$RepoRoot,
        [string]$RunScript,
        [string]$StatusPath,
        [int]$PortValue
    )

    $stdoutFile = Join-Path ([System.IO.Path]::GetTempPath()) ("run-comfyui-" + [guid]::NewGuid().ToString() + ".stdout.log")
    $stderrFile = Join-Path ([System.IO.Path]::GetTempPath()) ("run-comfyui-" + [guid]::NewGuid().ToString() + ".stderr.log")
    $process = $null
    $startedAt = Get-Date

    try {
        $process = Start-Process `
            -FilePath "powershell.exe" `
            -ArgumentList @("-ExecutionPolicy", "Bypass", "-File", "`"$RunScript`"", "-Port", "$PortValue") `
            -WorkingDirectory $RepoRoot `
            -RedirectStandardOutput $stdoutFile `
            -RedirectStandardError $stderrFile `
            -PassThru

        $deadline = (Get-Date).AddSeconds(70)
        $payload = $null
        while ((Get-Date) -lt $deadline) {
            $lines = @()
            if (Test-Path $stdoutFile) {
                $lines = @(Get-Content $stdoutFile)
            }

            $payload = Get-JsonStatusFromLines -Lines $lines
            if (-not (Test-ValidStatusPayload -Payload $payload) -and (Test-Path $StatusPath)) {
                $statusItem = Get-Item $StatusPath
                if ($statusItem.LastWriteTime -ge $startedAt.AddSeconds(-1)) {
                    $payload = Read-StatusFile -Path $StatusPath
                }
            }

            if (Test-ValidStatusPayload -Payload $payload) {
                break
            }

            $process.Refresh()
            if ($process.HasExited) {
                break
            }

            Start-Sleep -Milliseconds 500
        }

        return $payload
    } finally {
        if ($null -ne $process) {
            $process.Refresh()
            if (-not $process.HasExited) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        }

        foreach ($tempFile in @($stdoutFile, $stderrFile)) {
            if (Test-Path $tempFile) {
                Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

function Wait-ForRunnerFinalStatus {
    param(
        [string]$StatusPath,
        [int]$Seconds,
        [datetime]$NotBefore
    )

    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Path $StatusPath) {
            $statusItem = Get-Item $StatusPath
            if ($statusItem.LastWriteTime -ge $NotBefore.AddSeconds(-1)) {
                $payload = Read-StatusFile -Path $StatusPath
                if (Test-ValidStatusPayload -Payload $payload) {
                    if ($payload.status -in @("started", "already_running", "error")) {
                        return $payload
                    }
                }
            }
        }

        Start-Sleep -Milliseconds 1000
    }

    return $null
}

$result = $null
$exitCode = 0
$logsRoot = $null
$smokeStatusFile = $null
$internalNote = $null
$renderElapsedSeconds = $null

try {
    $repoRoot = Get-RepoRoot
    $comfyRoot = Join-Path $repoRoot "vendor\ComfyUI"
    $venvPython = Join-Path $comfyRoot "venv\Scripts\python.exe"
    $outputDir = Join-Path $comfyRoot "output"
    $inventoryScript = Join-Path $repoRoot "python\checkpoint_inventory.py"
    $renderScript = Join-Path $repoRoot "python\render_text2img.py"
    $runScript = Join-Path $repoRoot "scripts\run_comfyui.ps1"
    $logsRoot = Join-Path $comfyRoot "logs"
    $runStatusFile = Join-Path $logsRoot "run_comfyui.status.json"
    $smokeStatusFile = Join-Path $logsRoot "smoke_test.status.json"
    $baseUrl = "http://127.0.0.1:$Port"

    if (-not (Test-Path $venvPython)) {
        $result = @{ status = "error"; mode = $null; output_file = $null; error_type = "api_error"; blocker = "api_error" }
        $exitCode = 1
    } elseif (-not (Test-Path $inventoryScript)) {
        $result = @{ status = "error"; mode = $null; output_file = $null; error_type = "api_error"; blocker = "api_error" }
        $exitCode = 1
    } elseif (-not (Test-Path $renderScript)) {
        $result = @{ status = "error"; mode = $null; output_file = $null; error_type = "api_error"; blocker = "api_error" }
        $exitCode = 1
    } else {
        $runnerCheckStarted = Get-Date
        $runStatus = Invoke-RunnerStatus -RepoRoot $repoRoot -RunScript $runScript -StatusPath $runStatusFile -PortValue $Port
        if (-not (Test-ValidStatusPayload -Payload $runStatus)) {
            $result = @{ status = "error"; mode = $null; output_file = $null; error_type = "api_error"; blocker = "api_error" }
            $exitCode = 1
        } elseif ($runStatus.status -eq "busy") {
            $runStatus = Wait-ForRunnerFinalStatus -StatusPath $runStatusFile -Seconds 20 -NotBefore $runnerCheckStarted
            if (-not (Test-ValidStatusPayload -Payload $runStatus)) {
                $result = @{ status = "error"; mode = $null; output_file = $null; error_type = "api_error"; blocker = "api_error" }
                $exitCode = 1
            }
        }

        if ($null -eq $result) {
            if ($runStatus.status -eq "error") {
                $result = @{ status = "error"; mode = $null; output_file = $null; error_type = "api_error"; blocker = "api_error" }
                $exitCode = 1
            } elseif ($runStatus.status -notin @("started", "already_running")) {
                $result = @{ status = "error"; mode = $null; output_file = $null; error_type = "api_error"; blocker = "api_error" }
                $exitCode = 1
            } else {
                $httpDeadline = (Get-Date).AddSeconds(10)
                while ((Get-Date) -lt $httpDeadline) {
                    if (Test-ComfyHttp -Url $baseUrl) {
                        break
                    }
                    Start-Sleep -Milliseconds 500
                }

                if (-not (Test-ComfyHttp -Url $baseUrl)) {
                    $result = @{ status = "error"; mode = $null; output_file = $null; error_type = "api_error"; blocker = "api_error" }
                    $exitCode = 1
                } else {
                    $inventoryInvoke = Invoke-PythonJsonStatus `
                        -PythonExe $venvPython `
                        -ScriptPath $inventoryScript `
                        -Arguments @()

                    $inventoryStatus = $inventoryInvoke.Payload
                    if (
                        $inventoryInvoke.ExitCode -ne 0 -or
                        -not (Test-ValidStatusPayload -Payload $inventoryStatus) -or
                        $inventoryStatus.status -ne "ok"
                    ) {
                        $result = @{ status = "error"; mode = $null; output_file = $null; error_type = "api_error"; blocker = "api_error" }
                        $exitCode = 1
                    } else {
                        $sdxlCount = 0
                        if ($inventoryStatus.PSObject.Properties.Name -contains "sdxl_count") {
                            $sdxlCount = [int]$inventoryStatus.sdxl_count
                        }

                        $renderArguments = @(
                            "--prompt", $Prompt,
                            "--negative-prompt", $NegativePrompt,
                            "--width", "$Width",
                            "--height", "$Height",
                            "--steps", "$Steps",
                            "--cfg", "$Cfg",
                            "--wait",
                            "--wait-timeout", "$TimeoutSeconds",
                            "--output-dir", $outputDir
                        )

                        if ($sdxlCount -ge 1) {
                            $selectedCheckpoint = $null
                            if ($inventoryStatus.PSObject.Properties.Name -contains "selected") {
                                $selectedCheckpoint = "$($inventoryStatus.selected)"
                            }
                            if ([string]::IsNullOrWhiteSpace($selectedCheckpoint)) {
                                $result = @{ status = "error"; mode = $null; output_file = $null; error_type = "api_error"; blocker = "api_error" }
                                $exitCode = 1
                            } else {
                                $renderArguments += @("--checkpoint", $selectedCheckpoint)
                            }
                        } else {
                            $internalNote = "no_real_sdxl_checkpoint"
                            $renderArguments += @("--workflow", "api_healthcheck_placeholder.json")
                        }
                    }

                    if ($null -eq $result) {
                        $renderStatus = $null
                        $renderExitCode = 1
                        $renderDeadline = (Get-Date).AddSeconds(10)
                        $renderStopwatch = [System.Diagnostics.Stopwatch]::StartNew()
                        do {
                            $renderInvoke = Invoke-PythonJsonStatus `
                                -PythonExe $venvPython `
                                -ScriptPath $renderScript `
                                -Arguments $renderArguments

                            $renderExitCode = $renderInvoke.ExitCode
                            $renderStatus = $renderInvoke.Payload
                            $renderErrorType = $null
                            if (Test-ValidStatusPayload -Payload $renderStatus) {
                                if ($renderStatus.PSObject.Properties.Name -contains "error_type") {
                                    $renderErrorType = "$($renderStatus.error_type)"
                                }
                            }

                            if ($renderExitCode -eq 0 -and (Test-ValidStatusPayload -Payload $renderStatus) -and $renderStatus.status -eq "ok") {
                                break
                            }

                            if ($renderErrorType -ne "api_error") {
                                break
                            }

                            Start-Sleep -Milliseconds 1000
                        } while ((Get-Date) -lt $renderDeadline)
                        $renderStopwatch.Stop()
                        $renderElapsedSeconds = [math]::Round($renderStopwatch.Elapsed.TotalSeconds, 1)

                        if (-not (Test-ValidStatusPayload -Payload $renderStatus)) {
                            $result = @{ status = "error"; mode = $null; output_file = $null; error_type = "api_error"; blocker = "api_error"; elapsed_seconds = $renderElapsedSeconds }
                            $exitCode = 1
                        } elseif ($renderExitCode -ne 0 -or $renderStatus.status -ne "ok") {
                            $renderMode = $null
                            $renderErrorType = "unknown_execution_error"
                            $renderBlocker = "unknown_execution_error"
                            if ($renderStatus.PSObject.Properties.Name -contains "mode") {
                                $renderMode = "$($renderStatus.mode)"
                            }
                            if ($renderStatus.PSObject.Properties.Name -contains "error_type") {
                                $renderErrorType = "$($renderStatus.error_type)"
                            }
                            if ($renderStatus.PSObject.Properties.Name -contains "blocker") {
                                $renderBlocker = "$($renderStatus.blocker)"
                            }
                            $result = @{
                                status = "error"
                                mode = $renderMode
                                output_file = $null
                                error_type = $renderErrorType
                                blocker = $renderBlocker
                                elapsed_seconds = $renderElapsedSeconds
                            }
                            $exitCode = 1
                        } else {
                            $result = @{
                                status = "ok"
                                mode = "$($renderStatus.mode)"
                                output_file = if ($null -ne $renderStatus.output_file) { "$($renderStatus.output_file)" } else { $null }
                                elapsed_seconds = $renderElapsedSeconds
                            }
                        }
                    }
                }
            }
        }
    }
} catch {
    $result = @{
        status = "error"
        mode = $null
        output_file = $null
        error_type = "api_error"
        blocker = "api_error"
    }
    $exitCode = 1
}

$json = ConvertTo-StatusJson -Payload $result
if ($null -ne $smokeStatusFile) {
    $statusPayloadForFile = @{} + $result
    if ($null -ne $internalNote) {
        $statusPayloadForFile.note = $internalNote
    }
    $null = Write-StatusFileAtomic -Path $smokeStatusFile -Payload $statusPayloadForFile
}
[Console]::Out.WriteLine($json)
[Console]::Out.Flush()
exit $exitCode
