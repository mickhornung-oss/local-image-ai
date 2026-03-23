[CmdletBinding()]
param(
    [string]$ConfigPath = "config\\text_service.json"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-StrictMode -Version Latest

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Resolve-LocalPath {
    param(
        [string]$RepoRoot,
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $null
    }

    if ([System.IO.Path]::IsPathRooted($Value)) {
        $candidate = $Value
    } else {
        $candidate = Join-Path $RepoRoot $Value
    }
    return [System.IO.Path]::GetFullPath($candidate)
}

function Test-RunnerHealth {
    param(
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest -Uri "$Url/v1/models" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -ne 200) {
            return @{ Ok = $false; Reason = "http status $($response.StatusCode)" }
        }

        $payload = $response.Content | ConvertFrom-Json
        if ($null -eq $payload) {
            return @{ Ok = $false; Reason = "invalid response payload" }
        }

        return @{ Ok = $true; Reason = $null; Payload = $payload }
    } catch {
        return @{ Ok = $false; Reason = $_.Exception.Message }
    }
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

$result = $null
$exitCode = 0

try {
    $repoRoot = Get-RepoRoot
    $resolvedConfigPath = (Resolve-Path (Join-Path $repoRoot $ConfigPath)).Path
    $config = Get-Content -Path $resolvedConfigPath -Raw | ConvertFrom-Json

    if ($config.enabled -ne $true) {
        throw "text service disabled by config"
    }

    if ("$($config.runner_type)" -ne "llama_cpp_server") {
        throw "runner_type must be llama_cpp_server"
    }

    if ("$($config.runner_host)" -ne "127.0.0.1") {
        throw "runner_host must be 127.0.0.1"
    }

    $runnerPort = [int]$config.runner_port
    $runnerUrl = "http://127.0.0.1:$runnerPort"
    $runnerBinaryPath = Resolve-LocalPath -RepoRoot $repoRoot -Value "$($config.runner_binary_path)"
    $modelPath = Resolve-LocalPath -RepoRoot $repoRoot -Value "$($config.model_path)"

    if (-not $runnerBinaryPath -or -not (Test-Path $runnerBinaryPath)) {
        $result = @{ status = "error"; reason = "runner_binary_missing" }
        $exitCode = 1
    } elseif (-not $modelPath -or -not (Test-Path $modelPath)) {
        $result = @{ status = "error"; reason = "model_missing" }
        $exitCode = 1
    } else {
        $healthProbe = Test-RunnerHealth -Url $runnerUrl
        if ($healthProbe.Ok) {
            $result = @{
                status = "already_running"
                port = $runnerPort
                pid = (Get-ListenerPid -LocalPort $runnerPort)
                url = $runnerUrl
                runner_binary_path = $runnerBinaryPath
                model_path = $modelPath
            }
        } else {
            $listenerPid = Get-ListenerPid -LocalPort $runnerPort
            if ($null -ne $listenerPid) {
                $result = @{
                    status = "error"
                    reason = "port_in_use_by_other_process"
                }
                $exitCode = 1
            } else {
                $logsRoot = Join-Path $repoRoot "vendor\text_runner\logs"
                if (-not (Test-Path $logsRoot)) {
                    New-Item -ItemType Directory -Path $logsRoot | Out-Null
                }

                $stdoutLog = Join-Path $logsRoot "llama-server.stdout.log"
                $stderrLog = Join-Path $logsRoot "llama-server.stderr.log"
                $quotedModelPath = '"' + $modelPath + '"'
                $argumentList = @(
                    "--model", $quotedModelPath,
                    "--host", "127.0.0.1",
                    "--port", "$runnerPort",
                    "--ctx-size", "2048"
                )

                $process = Start-Process -FilePath $runnerBinaryPath -ArgumentList $argumentList -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog

                $deadline = (Get-Date).AddSeconds(90)
                do {
                    Start-Sleep -Milliseconds 500
                    $healthProbe = Test-RunnerHealth -Url $runnerUrl
                    if ($healthProbe.Ok) {
                        $result = @{
                            status = "started"
                            port = $runnerPort
                            pid = $process.Id
                            url = $runnerUrl
                            runner_binary_path = $runnerBinaryPath
                            model_path = $modelPath
                        }
                        break
                    }
                } while ((Get-Date) -lt $deadline)

                if ($null -eq $result) {
                    try {
                        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                    } catch {
                    }
                    $result = @{
                        status = "error"
                        reason = "startup_timeout"
                    }
                    $exitCode = 1
                }
            }
        }
    }
} catch {
    $result = @{
        status = "error"
        reason = $_.Exception.Message
    }
    $exitCode = 1
}

$result | ConvertTo-Json -Compress
exit $exitCode
