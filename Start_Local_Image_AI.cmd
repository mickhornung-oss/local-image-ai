@echo off
setlocal

set "REPO_ROOT=%~dp0"
set "STACK_SCRIPT=%REPO_ROOT%scripts\run_stack.ps1"

echo Starte den lokalen KI-Stack...
echo.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%STACK_SCRIPT%" start
if errorlevel 1 (
  echo.
  echo Der Stack konnte nicht sauber gestartet werden.
  echo Bitte die Meldungen oben pruefen.
  pause
  exit /b 1
)

echo.
echo Stack laeuft.
echo App: http://127.0.0.1:8090
start "" "http://127.0.0.1:8090" >nul 2>&1
exit /b 0
