@echo off
REM ============================================================
REM  MT5 Panel - double click this file to start.
REM  Make sure MetaTrader 5 is open and logged in first.
REM ============================================================
title MT5 Panel
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)

%PY% -c "import MetaTrader5" >nul 2>nul
if not %errorlevel%==0 (
  echo Installing the MetaTrader5 package, one moment...
  %PY% -m pip install --quiet MetaTrader5
)

%PY% server.py --open
echo.
echo The panel has stopped. Press any key to close this window.
pause >nul
