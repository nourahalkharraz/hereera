@echo off
REM ============================================================
REM  MT5 Panel - start with phone access enabled.
REM
REM  Read the "Using it from your phone" part of README.md first:
REM  put this PC and your phone on a private network (Tailscale is
REM  the easy one). Do NOT forward this port on your router.
REM
REM  Set your own password below, then double click this file.
REM ============================================================
set PANEL_PASSWORD=change-me-please

title MT5 Panel (phone access)
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)

%PY% -c "import MetaTrader5" >nul 2>nul
if not %errorlevel%==0 (
  echo Installing the MetaTrader5 package, one moment...
  %PY% -m pip install --quiet MetaTrader5
)

echo.
echo Your phone opens:  http://^<this-pc-tailscale-address^>:8777
echo Password:          %PANEL_PASSWORD%
echo.
%PY% server.py --lan --password "%PANEL_PASSWORD%"
echo.
echo The panel has stopped. Press any key to close this window.
pause >nul
