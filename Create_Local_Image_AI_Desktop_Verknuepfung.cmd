@echo off
setlocal

set "REPO_ROOT=%~dp0"
set "SHORTCUT_SCRIPT=%REPO_ROOT%scripts\create_desktop_shortcut.ps1"

if not exist "%SHORTCUT_SCRIPT%" (
  echo Verknuepfungsskript nicht gefunden:
  echo %SHORTCUT_SCRIPT%
  pause
  exit /b 1
)

echo Desktop-Verknuepfung fuer Local Image AI wird erstellt...
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%SHORTCUT_SCRIPT%"
if errorlevel 1 (
  echo.
  echo Die Desktop-Verknuepfung konnte nicht erstellt werden.
  pause
  exit /b 1
)

echo.
echo Verknuepfung erfolgreich erstellt.
exit /b 0
