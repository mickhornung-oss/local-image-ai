@echo off
setlocal

set "REPO_ROOT=%~dp0"
set "STACK_SCRIPT=%REPO_ROOT%scripts\run_stack.ps1"

if not exist "%STACK_SCRIPT%" (
  echo Statusskript nicht gefunden:
  echo %STACK_SCRIPT%
  pause
  exit /b 1
)

echo Lokaler KI-Stack Status:
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%STACK_SCRIPT%" status -UserMode
exit /b %errorlevel%
