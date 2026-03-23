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

function Resolve-PythonCommand {
    param([string]$RepoRoot)

    $vendorPython = Join-Path $RepoRoot "vendor\ComfyUI\venv\Scripts\python.exe"
    if (Test-Path $vendorPython) {
        return @{
            FilePath = $vendorPython
            PrefixArgs = @()
        }
    }

    $appPython = Join-Path $RepoRoot "venv\Scripts\python.exe"
    if (Test-Path $appPython) {
        return @{
            FilePath = $appPython
            PrefixArgs = @()
        }
    }

    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -eq $launcher) {
        throw "No Python runtime found for text service"
    }

    $installed = & py -0p 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to query py launcher"
    }

    foreach ($version in @("3.10", "3.11")) {
        if ($installed -match "3\.$($version.Split('.')[1])") {
            return @{
                FilePath = $launcher.Source
                PrefixArgs = @("-$version")
            }
        }
    }

    throw "No compatible Python 3.10/3.11 found for text service"
}

function Test-TextServiceHealth {
    param(
        [string]$Url,
        [string]$ExpectedService,
        [int]$ExpectedPort
    )

    try {
        $response = Invoke-WebRequest -Uri "$Url/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -ne 200) {
            return @{ Ok = $false; Reason = "http status $($response.StatusCode)" }
        }

        $payload = $response.Content | ConvertFrom-Json
        if (
            $null -eq $payload -or
            "$($payload.status)" -ne "ok" -or
            "$($payload.service)" -ne $ExpectedService -or
            "$($payload.host)" -ne "127.0.0.1" -or
            [int]$payload.port -ne $ExpectedPort
        ) {
            return @{ Ok = $false; Reason = "invalid health payload" }
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
    $serviceScript = Join-Path $repoRoot "python\text_service.py"
    $resolvedConfigPath = (Resolve-Path (Join-Path $repoRoot $ConfigPath)).Path

    if (-not (Test-Path $serviceScript)) {
        throw "python/text_service.py missing"
    }

    $config = Get-Content -Path $resolvedConfigPath -Raw | ConvertFrom-Json
    $enabled = $config.enabled -eq $true
    $serviceHost = "$($config.host)"
    $port = [int]$config.port
    $serviceName = "$($config.service_name)"

    if (-not $enabled) {
        $result = @{ status = "error"; reason = "service_disabled" }
        $exitCode = 1
    } elseif ($serviceHost -ne "127.0.0.1") {
        $result = @{ status = "error"; reason = "non_loopback_host" }
        $exitCode = 1
    } else {
        $url = "http://127.0.0.1:$port"
        $healthProbe = Test-TextServiceHealth -Url $url -ExpectedService $serviceName -ExpectedPort $port

        if ($healthProbe.Ok) {
            $result = @{
                status = "already_running"
                port = $port
                pid = (Get-ListenerPid -LocalPort $port)
                url = $url
                service = $serviceName
            }
        } else {
            $listenerPid = Get-ListenerPid -LocalPort $port
            if ($null -ne $listenerPid) {
                $result = @{
                    status = "error"
                    reason = "port_in_use_by_other_process"
                }
                $exitCode = 1
            } else {
                $pythonCommand = Resolve-PythonCommand -RepoRoot $repoRoot
                $logsRoot = Join-Path $repoRoot "vendor\ComfyUI\logs"
                if (-not (Test-Path $logsRoot)) {
                    New-Item -ItemType Directory -Path $logsRoot | Out-Null
                }

                $stdoutLog = Join-Path $logsRoot "text_service.stdout.log"
                $stderrLog = Join-Path $logsRoot "text_service.stderr.log"
                $quotedServiceScript = '"' + $serviceScript + '"'
                $quotedConfigPath = '"' + $resolvedConfigPath + '"'
                $argumentList = @()
                $argumentList += $pythonCommand.PrefixArgs
                $argumentList += @($quotedServiceScript, "--config", $quotedConfigPath, "--host", "127.0.0.1", "--port", "$port")

                $process = Start-Process -FilePath $pythonCommand.FilePath -ArgumentList $argumentList -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog

                $deadline = (Get-Date).AddSeconds(30)
                do {
                    Start-Sleep -Milliseconds 500
                    $healthProbe = Test-TextServiceHealth -Url $url -ExpectedService $serviceName -ExpectedPort $port
                    if ($healthProbe.Ok) {
                        $result = @{
                            status = "started"
                            port = $port
                            pid = $process.Id
                            url = $url
                            service = $serviceName
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
