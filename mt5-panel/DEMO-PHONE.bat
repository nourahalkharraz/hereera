@echo off
REM ============================================================
REM  MT5 Panel - DEMO + phone access.
REM
REM  This runs the panel with FAKE prices and a FAKE account.
REM  MetaTrader 5 does NOT need to be open, and you do NOT need
REM  to log in anywhere. Nothing here touches a real account.
REM
REM  Use it to try the interface from your phone.
REM ============================================================
set PANEL_PASSWORD=change-me-please

title MT5 Panel (demo + phone)
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)

echo.
echo   DEMO MODE - fake prices, no MetaTrader 5 needed.
echo.
echo   On this PC:   http://127.0.0.1:8777
echo   On the phone: http://^<this-pc-address^>:8777
echo   Password:     %PANEL_PASSWORD%
echo.
%PY% server.py --demo --lan --password "%PANEL_PASSWORD%"
echo.
echo The panel has stopped. Press any key to close this window.
pause >nul
