[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

& .\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8787
