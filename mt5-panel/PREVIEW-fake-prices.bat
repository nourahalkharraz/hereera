@echo off
REM ============================================================
REM  MT5 Panel - LOOK AT THE INTERFACE ONLY.
REM
REM  FAKE prices, invented by this script. NOT the real market.
REM  Use it only to look at the layout when MetaTrader is not
REM  available.
REM
REM  This is NOT the same thing as a broker demo account. For a
REM  demo account -- real gold prices, real spreads, real order
REM  execution, virtual money -- log into it in MetaTrader 5 and
REM  run START.bat instead.
REM ============================================================
set PANEL_PASSWORD=change-me-please

title MT5 Panel (fake prices - interface preview)
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)

echo.
echo   PREVIEW MODE - FAKE prices. Not the real market.
echo.
echo   On this PC:   http://127.0.0.1:8777
echo   On the phone: http://^<this-pc-address^>:8777
echo   Password:     %PANEL_PASSWORD%
echo.
%PY% server.py --demo --lan --password "%PANEL_PASSWORD%"
echo.
echo The panel has stopped. Press any key to close this window.
pause >nul
