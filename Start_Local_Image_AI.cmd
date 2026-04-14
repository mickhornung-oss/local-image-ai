@echo off
setlocal

set "REPO_ROOT=%~dp0"
set "STACK_SCRIPT=%REPO_ROOT%scripts\run_stack.ps1"

if not exist "%STACK_SCRIPT%" (
  echo Startskript nicht gefunden:
  echo %STACK_SCRIPT%
  pause
  exit /b 1
)

echo Lokaler KI-Stack wird gestartet...
echo Das kann beim ersten Start etwas dauern.
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%STACK_SCRIPT%" start -UserMode
if errorlevel 1 (
  echo.
  echo Der Stack konnte nicht sauber gestartet werden.
  echo Bitte pruefe den Status mit:
  echo powershell -ExecutionPolicy Bypass -File .\scripts\run_stack.ps1 status
  pause
  exit /b 1
)

echo.
echo Start erfolgreich.
echo App wird im Browser geoeffnet: http://127.0.0.1:8090
start "" "http://127.0.0.1:8090" >nul 2>&1
exit /b 0
