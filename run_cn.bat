@echo off
rem ---------------------------------------------------------------
rem  Localized build launcher for Tenshi no Himago-to
rem  Uses the bundled portable Python 3.10 in .\python
rem  Run this file; do NOT start lcsebody.exe directly.
rem ---------------------------------------------------------------
setlocal
cd /d "%~dp0"

set "PY=.\python\python.exe"
if not exist "%PY%" set "PY=python\python.exe"

if not exist "%PY%" (
    echo.
    echo   [X] Bundled Python not found at .\python\python.exe
    echo.
    pause
    exit /b 1
)

echo.
echo   ==================================================
echo     Tenshi no Himago-to  -  Chinese localization
echo   ==================================================
echo.

"%PY%" "%~dp0launch_cn.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo   [X] Launcher exited with code %RC%.
    echo       If it reported a permission error, right-click this
    echo       file and choose "Run as administrator".
    echo.
    pause
)

endlocal