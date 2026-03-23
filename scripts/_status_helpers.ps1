function ConvertTo-StatusJson {
    param(
        [Parameter(Mandatory = $true)][object]$Payload
    )

    return ($Payload | ConvertTo-Json -Compress -Depth 8)
}

function Write-StatusFileAtomic {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][object]$Payload
    )

    $directory = Split-Path -Parent $Path
    if (-not (Test-Path $directory)) {
        New-Item -ItemType Directory -Path $directory | Out-Null
    }

    $json = ConvertTo-StatusJson -Payload $Payload
    $tempPath = "$Path.$([guid]::NewGuid().ToString()).tmp"
    Set-Content -Path $tempPath -Value $json -Encoding ASCII -NoNewline
    Move-Item -Path $tempPath -Destination $Path -Force
    return $json
}

function Read-StatusFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    try {
        $raw = Get-Content -Path $Path -Raw -Encoding UTF8
        if ([string]::IsNullOrWhiteSpace($raw)) {
            return $null
        }

        return $raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Get-JsonStatusFromLines {
    param(
        [Parameter(Mandatory = $false)][AllowNull()][object[]]$Lines
    )

    if ($null -eq $Lines) {
        return $null
    }

    $normalized = @($Lines | ForEach-Object { "$_" } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($normalized.Count -eq 0) {
        return $null
    }

    try {
        return ($normalized[-1] | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Test-ValidStatusPayload {
    param(
        [Parameter(Mandatory = $false)][object]$Payload
    )

    if ($null -eq $Payload) {
        return $false
    }

    return ($Payload.PSObject.Properties.Name -contains "status") -and ($Payload.status -is [string]) -and (-not [string]::IsNullOrWhiteSpace($Payload.status))
}

function Get-ProcessReference {
    param(
        [Parameter(Mandatory = $true)][int]$Id
    )

    $process = Get-Process -Id $Id -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        return $null
    }

    $startTimeUtc = $null
    try {
        $startTimeUtc = $process.StartTime.ToUniversalTime().ToString("o")
    } catch {
    }

    $path = $null
    try {
        $path = $process.Path
    } catch {
    }

    return [pscustomobject]@{
        pid = $process.Id
        start_time_utc = $startTimeUtc
        path = $path
    }
}

function Test-ProcessReference {
    param(
        [Parameter(Mandatory = $false)][object]$Reference
    )

    if ($null -eq $Reference) {
        return $false
    }

    if (-not ($Reference.PSObject.Properties.Name -contains "pid")) {
        return $false
    }

    $process = Get-Process -Id ([int]$Reference.pid) -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        return $false
    }

    if (($Reference.PSObject.Properties.Name -contains "start_time_utc") -and -not [string]::IsNullOrWhiteSpace("$($Reference.start_time_utc)")) {
        try {
            return $process.StartTime.ToUniversalTime().ToString("o") -eq "$($Reference.start_time_utc)"
        } catch {
            return $false
        }
    }

    return $true
}

function Get-FileAgeSeconds {
    param(
        [Parameter(Mandatory = $true)][string]$Path
    )

    if (-not (Test-Path $Path)) {
        return $null
    }

    return [int]((Get-Date) - (Get-Item $Path).LastWriteTime).TotalSeconds
}
