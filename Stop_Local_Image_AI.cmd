@echo off
setlocal

set "REPO_ROOT=%~dp0"
set "STACK_SCRIPT=%REPO_ROOT%scripts\run_stack.ps1"

if not exist "%STACK_SCRIPT%" (
  echo Stopskript nicht gefunden:
  echo %STACK_SCRIPT%
  pause
  exit /b 1
)

echo Lokaler KI-Stack wird gestoppt...
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%STACK_SCRIPT%" stop -UserMode
if errorlevel 1 (
  echo.
  echo Der Stack konnte nicht vollstaendig gestoppt werden.
  pause
  exit /b 1
)

echo.
echo Stop abgeschlossen.
exit /b 0
