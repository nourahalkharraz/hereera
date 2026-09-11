@echo off
REM ============================================================
REM  MT5 Panel - your account, reachable from your phone.
REM
REM  The password is NOT stored in this file. On first run you
REM  are asked for one and it is saved to panel-password.txt,
REM  which git ignores, so it can never be committed.
REM
REM  Read "Using it from your phone" in README.md first: keep
REM  this on a private network (Tailscale). Never forward the
REM  port on your router.
REM ============================================================
title MT5 Panel (phone access)
cd /d "%~dp0"

if not exist "panel-password.txt" (
  echo.
  echo   No panel password set yet.
  set /p NEWPASS=  Choose a password for phone access:
  echo %NEWPASS%> panel-password.txt
  echo   Saved to panel-password.txt ^(git ignores this file^).
  echo.
)

where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)

%PY% -c "import MetaTrader5" >nul 2>nul
if not %errorlevel%==0 (
  echo Installing the MetaTrader5 package, one moment...
  %PY% -m pip install --quiet MetaTrader5
)

echo.
echo   Your phone opens:  http://^<this-pc-tailscale-address^>:8777
echo   Password:          the one in panel-password.txt
echo.
%PY% server.py --lan
echo.
echo The panel has stopped. Press any key to close this window.
pause >nul
