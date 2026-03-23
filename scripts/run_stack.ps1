[CmdletBinding()]
param(
    [ValidateSet("start", "status", "stop")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-StrictMode -Version Latest

. (Join-Path $PSScriptRoot "_status_helpers.ps1")

function Get-RepoRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Get-LogsRoot {
    param([string]$RepoRoot)

    $path = Join-Path $RepoRoot "vendor\ComfyUI\logs"
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
    }
    return $path
}

function Get-StackStatePath {
    param([string]$RepoRoot)

    return (Join-Path (Get-LogsRoot -RepoRoot $RepoRoot) "run_stack.state.json")
}

function Remove-IfExists {
    param([string]$Path)

    if (Test-Path $Path) {
        Remove-Item $Path -Force -ErrorAction SilentlyContinue
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

function Invoke-JsonLauncherScript {
    param(
        [string]$ScriptPath,
        [string[]]$Arguments = @()
    )

    $lines = @(& powershell -ExecutionPolicy Bypass -File $ScriptPath @Arguments 2>&1)
    $payload = Get-JsonStatusFromLines -Lines $lines
    $exitCode = $LASTEXITCODE

    return [pscustomobject]@{
        payload = $payload
        exit_code = $exitCode
        raw_lines = $lines
    }
}

function Start-ComponentViaScript {
    param(
        [string]$ComponentId,
        [string]$Label,
        [string]$ScriptPath,
        [int]$TimeoutSeconds,
        [object]$State = $null
    )

    $beforeStatus = Get-ComponentLiveStatus -ComponentId $ComponentId -State $State
    if ($beforeStatus.running) {
        return [pscustomobject]@{
            status = "already_running"
            reason = $null
            port = $beforeStatus.port
            pid = $beforeStatus.pid
            url = $beforeStatus.url
        }
    }

    $quotedScriptPath = '"' + $ScriptPath + '"'
    $launcherProcess = Start-Process -FilePath "powershell.exe" -ArgumentList @("-ExecutionPolicy", "Bypass", "-File", $quotedScriptPath) -PassThru -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    do {
        Start-Sleep -Milliseconds 500
        $liveStatus = Get-ComponentLiveStatus -ComponentId $ComponentId -State $State
        if ($liveStatus.running) {
            if (-not $launcherProcess.HasExited) {
                try {
                    Stop-Process -Id $launcherProcess.Id -Force -ErrorAction SilentlyContinue
                } catch {
                }
            }

            return [pscustomobject]@{
                status = "started"
                reason = $null
                port = $liveStatus.port
                pid = $liveStatus.pid
                url = $liveStatus.url
            }
        }

        if ($launcherProcess.HasExited -and $launcherProcess.ExitCode -ne 0) {
            return [pscustomobject]@{
                status = "error"
                reason = "$Label start failed with exit code $($launcherProcess.ExitCode)"
                port = $liveStatus.port
                pid = $liveStatus.pid
                url = $liveStatus.url
            }
        }
    } while ((Get-Date) -lt $deadline)

    if (-not $launcherProcess.HasExited) {
        try {
            Stop-Process -Id $launcherProcess.Id -Force -ErrorAction SilentlyContinue
        } catch {
        }
    }

    $finalStatus = Get-ComponentLiveStatus -ComponentId $ComponentId -State $State
    return [pscustomobject]@{
        status = "error"
        reason = if ($finalStatus.running) { "started_without_launcher_status" } else { "timeout_waiting_for_$ComponentId" }
        port = $finalStatus.port
        pid = $finalStatus.pid
        url = $finalStatus.url
    }
}

function Get-ComponentLiveStatus {
    param(
        [string]$ComponentId,
        [object]$State = $null
    )

    switch ($ComponentId) {
        "comfyui" {
            $probe = Test-JsonEndpoint -Url "http://127.0.0.1:8188" -Path "/system_stats" -Validator {
                param($payload)
                $null -ne $payload
            }
            $managedEntry = Get-ManagedComponentState -State $State -ComponentId "comfyui"
            return [pscustomobject]@{
                id = "comfyui"
                label = "ComfyUI"
                running = [bool]$probe.Ok
                port = 8188
                pid = Get-ListenerPid -LocalPort 8188
                managed = [bool]($null -ne $managedEntry -and $managedEntry.started_by_stack -eq $true)
                detail = if ($probe.Ok) { "ok" } else { $probe.Reason }
                url = "http://127.0.0.1:8188"
            }
        }
        "text_runner" {
            $probe = Test-JsonEndpoint -Url "http://127.0.0.1:8092" -Path "/v1/models" -Validator {
                param($payload)
                $null -ne $payload
            }
            $managedEntry = Get-ManagedComponentState -State $State -ComponentId "text_runner"
            return [pscustomobject]@{
                id = "text_runner"
                label = "Text-Runner"
                running = [bool]$probe.Ok
                port = 8092
                pid = Get-ListenerPid -LocalPort 8092
                managed = [bool]($null -ne $managedEntry -and $managedEntry.started_by_stack -eq $true)
                detail = if ($probe.Ok) { "ok" } else { $probe.Reason }
                url = "http://127.0.0.1:8092"
            }
        }
        "text_service" {
            $probe = Test-JsonEndpoint -Url "http://127.0.0.1:8091" -Path "/health" -Validator {
                param($payload)
                "$($payload.status)" -eq "ok" -and "$($payload.service)" -eq "local-text-service"
            }
            $managedEntry = Get-ManagedComponentState -State $State -ComponentId "text_service"
            return [pscustomobject]@{
                id = "text_service"
                label = "Text-Service"
                running = [bool]$probe.Ok
                port = 8091
                pid = Get-ListenerPid -LocalPort 8091
                managed = [bool]($null -ne $managedEntry -and $managedEntry.started_by_stack -eq $true)
                detail = if ($probe.Ok) { "ok" } else { $probe.Reason }
                url = "http://127.0.0.1:8091"
            }
        }
        "app" {
            $probe = Test-JsonEndpoint -Url "http://127.0.0.1:8090" -Path "/health" -Validator {
                param($payload)
                "$($payload.status)" -eq "ok" -and "$($payload.service)" -eq "local-image-app"
            }
            $managedEntry = Get-ManagedComponentState -State $State -ComponentId "app"
            return [pscustomobject]@{
                id = "app"
                label = "Haupt-App"
                running = [bool]$probe.Ok
                port = 8090
                pid = Get-ListenerPid -LocalPort 8090
                managed = [bool]($null -ne $managedEntry -and $managedEntry.started_by_stack -eq $true)
                detail = if ($probe.Ok) { "ok" } else { $probe.Reason }
                url = "http://127.0.0.1:8090"
            }
        }
        default {
            throw "unknown component id: $ComponentId"
        }
    }
}

function Test-JsonEndpoint {
    param(
        [string]$Url,
        [string]$Path,
        [scriptblock]$Validator
    )

    try {
        $response = Invoke-WebRequest -Uri "$Url$Path" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -ne 200) {
            return @{ Ok = $false; Payload = $null; Reason = "http status $($response.StatusCode)" }
        }

        $payload = $response.Content | ConvertFrom-Json
        if ($null -eq $payload) {
            return @{ Ok = $false; Payload = $null; Reason = "empty payload" }
        }

        if ($null -ne $Validator -and -not (& $Validator $payload)) {
            return @{ Ok = $false; Payload = $payload; Reason = "invalid payload" }
        }

        return @{ Ok = $true; Payload = $payload; Reason = $null }
    } catch {
        return @{ Ok = $false; Payload = $null; Reason = $_.Exception.Message }
    }
}

function Get-ManagedComponentState {
    param(
        [object]$State,
        [string]$ComponentId
    )

    if ($null -eq $State) {
        return $null
    }
    if (-not ($State.PSObject.Properties.Name -contains "components")) {
        return $null
    }
    $components = $State.components
    if ($null -eq $components) {
        return $null
    }
    if ($components -is [System.Collections.IDictionary]) {
        return $components[$ComponentId]
    }
    if ($components.PSObject.Properties.Name -contains $ComponentId) {
        return $components.$ComponentId
    }
    return $null
}

function New-ManagedEntry {
    param(
        [object]$StartPayload,
        [object]$PreviousEntry
    )

    $processReference = $null
    if ($StartPayload.PSObject.Properties.Name -contains "pid" -and $null -ne $StartPayload.pid) {
        $processReference = Get-ProcessReference -Id ([int]$StartPayload.pid)
    }

    $startedByStack = $false
    if ("$($StartPayload.status)" -eq "started") {
        $startedByStack = $true
    } elseif ($null -ne $PreviousEntry -and $PreviousEntry.PSObject.Properties.Name -contains "started_by_stack" -and $PreviousEntry.started_by_stack -eq $true) {
        $previousProcess = $null
        if ($PreviousEntry.PSObject.Properties.Name -contains "process") {
            $previousProcess = $PreviousEntry.process
        }
        if (Test-ProcessReference -Reference $previousProcess) {
            $startedByStack = $true
            if ($null -eq $processReference) {
                $processReference = $previousProcess
            }
        }
    }

    return [ordered]@{
        status = "$($StartPayload.status)"
        started_by_stack = $startedByStack
        port = if ($StartPayload.PSObject.Properties.Name -contains "port") { $StartPayload.port } else { $null }
        pid = if ($StartPayload.PSObject.Properties.Name -contains "pid") { $StartPayload.pid } else { $null }
        url = if ($StartPayload.PSObject.Properties.Name -contains "url") { $StartPayload.url } else { $null }
        process = $processReference
        updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    }
}

function Save-StackState {
    param(
        [string]$Path,
        [hashtable]$Components
    )

    $payload = [ordered]@{
        schema = "run_stack_v1"
        updated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        components = [ordered]@{}
    }

    foreach ($componentId in $Components.Keys) {
        $payload.components[$componentId] = $Components[$componentId]
    }

    $null = Write-StatusFileAtomic -Path $Path -Payload $payload
}

function Get-StackLiveStatus {
    param([object]$State)
    $orderedIds = @("comfyui", "text_runner", "text_service", "app")
    return @($orderedIds | ForEach-Object { Get-ComponentLiveStatus -ComponentId $_ -State $State })
}

function Write-StackStatus {
    param(
        [string]$ActionLabel,
        [object[]]$StatusItems
    )

    Write-Output "Stack $ActionLabel"
    Write-Output "Komponente    Status   Port  PID    Verwaltet  Detail"
    Write-Output "-----------   ------   ----  ----   ---------  ------"
    foreach ($item in $StatusItems) {
        $statusText = if ($item.running) { "laeuft" } else { "aus" }
        $pidText = if ($null -ne $item.pid) { "$($item.pid)" } else { "-" }
        $managedText = if ($item.managed) { "ja" } else { "nein" }
        $detailText = if ([string]::IsNullOrWhiteSpace("$($item.detail)")) { "-" } else { "$($item.detail)" }
        Write-Output ("{0,-12} {1,-7} {2,4}  {3,-6} {4,-10} {5}" -f $item.label, $statusText, $item.port, $pidText, $managedText, $detailText)
    }
}

function Stop-ManagedProcess {
    param(
        [string]$ComponentId,
        [string]$Label,
        [object]$Entry
    )

    if ($null -eq $Entry -or $Entry.started_by_stack -ne $true) {
        return [pscustomobject]@{ id = $ComponentId; label = $Label; action = "skipped"; reason = "not_managed" }
    }

    $processReference = $null
    if ($Entry.PSObject.Properties.Name -contains "process") {
        $processReference = $Entry.process
    }

    if (-not (Test-ProcessReference -Reference $processReference)) {
        return [pscustomobject]@{ id = $ComponentId; label = $Label; action = "skipped"; reason = "already_stopped" }
    }

    try {
        Stop-Process -Id ([int]$processReference.pid) -Force -ErrorAction Stop
        Start-Sleep -Milliseconds 800
        return [pscustomobject]@{ id = $ComponentId; label = $Label; action = "stopped"; reason = $null }
    } catch {
        return [pscustomobject]@{ id = $ComponentId; label = $Label; action = "error"; reason = $_.Exception.Message }
    }
}

$repoRoot = Get-RepoRoot
$statePath = Get-StackStatePath -RepoRoot $repoRoot
$existingState = Read-StatusFile -Path $statePath
$exitCode = 0

switch ($Action) {
    "start" {
        $scriptRuns = @(
            @{ id = "comfyui"; label = "ComfyUI"; path = (Join-Path $PSScriptRoot "run_comfyui.ps1"); timeout = 120 },
            @{ id = "text_runner"; label = "Text-Runner"; path = (Join-Path $PSScriptRoot "run_text_runner.ps1"); timeout = 180 },
            @{ id = "text_service"; label = "Text-Service"; path = (Join-Path $PSScriptRoot "run_text_service.ps1"); timeout = 60 },
            @{ id = "app"; label = "Haupt-App"; path = (Join-Path $PSScriptRoot "run_app.ps1"); timeout = 90 }
        )

        $componentState = @{}
        $startSummaries = @()
        foreach ($scriptRun in $scriptRuns) {
            $payload = Start-ComponentViaScript -ComponentId $scriptRun.id -Label $scriptRun.label -ScriptPath $scriptRun.path -TimeoutSeconds $scriptRun.timeout -State $existingState
            $previousEntry = Get-ManagedComponentState -State $existingState -ComponentId $scriptRun.id
            $componentState[$scriptRun.id] = New-ManagedEntry -StartPayload $payload -PreviousEntry $previousEntry
            $startSummaries += [pscustomobject]@{
                label = $scriptRun.label
                status = "$($payload.status)"
                reason = if ($payload.PSObject.Properties.Name -contains "reason") { "$($payload.reason)" } else { "" }
            }
            if ("$($payload.status)" -eq "error") {
                $exitCode = 1
            }
        }

        Save-StackState -Path $statePath -Components $componentState
        $liveStatus = Get-StackLiveStatus -State (Read-StatusFile -Path $statePath)

        Write-Output "Start-Ergebnis"
        foreach ($summary in $startSummaries) {
            $reasonText = if ([string]::IsNullOrWhiteSpace($summary.reason)) { "" } else { " | $($summary.reason)" }
            Write-Output ("- {0}: {1}{2}" -f $summary.label, $summary.status, $reasonText)
        }
        Write-Output ""
        Write-StackStatus -ActionLabel "Status nach Start" -StatusItems $liveStatus

        if (@($liveStatus | Where-Object { -not $_.running }).Count -gt 0) {
            $exitCode = 1
        }
    }
    "status" {
        $liveStatus = Get-StackLiveStatus -State $existingState
        Write-StackStatus -ActionLabel "Status" -StatusItems $liveStatus
    }
    "stop" {
        $stopPlan = @(
            @{ id = "app"; label = "Haupt-App" },
            @{ id = "text_service"; label = "Text-Service" },
            @{ id = "text_runner"; label = "Text-Runner" },
            @{ id = "comfyui"; label = "ComfyUI" }
        )

        $stopSummaries = @()
        foreach ($planItem in $stopPlan) {
            $entry = Get-ManagedComponentState -State $existingState -ComponentId $planItem.id
            $summary = Stop-ManagedProcess -ComponentId $planItem.id -Label $planItem.label -Entry $entry
            $stopSummaries += $summary
        }

        Remove-IfExists -Path (Join-Path (Get-LogsRoot -RepoRoot $repoRoot) "run_app.status.json")
        Remove-IfExists -Path (Join-Path (Get-LogsRoot -RepoRoot $repoRoot) "run_app.lock.json")
        Remove-IfExists -Path (Join-Path (Get-LogsRoot -RepoRoot $repoRoot) "run_comfyui.status.json")
        Remove-IfExists -Path (Join-Path (Get-LogsRoot -RepoRoot $repoRoot) "run_comfyui.lock.json")
        Remove-IfExists -Path $statePath

        Write-Output "Stop-Ergebnis"
        foreach ($summary in $stopSummaries) {
            $reasonText = if ([string]::IsNullOrWhiteSpace($summary.reason)) { "" } else { " | $($summary.reason)" }
            Write-Output ("- {0}: {1}{2}" -f $summary.label, $summary.action, $reasonText)
            if ($summary.action -eq "error") {
                $exitCode = 1
            }
        }
        Write-Output ""
        $liveStatus = Get-StackLiveStatus -State $null
        Write-StackStatus -ActionLabel "Status nach Stop" -StatusItems $liveStatus
    }
}

exit $exitCode
