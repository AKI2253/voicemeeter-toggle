@echo off
chcp 65001 >nul 2>&1
title VoiceMeeter Toggle

:: ---- Admin Check ----
NET SESSION >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [*] Requesting admin privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs -WorkingDirectory '%~dp0'"
    exit /b
)

:: ---- Change to script directory ----
cd /d "%~dp0"

:: ---- Find Python ----
set PYTHON=
for %%P in (python3.exe python.exe) do (
    where %%P >nul 2>&1 && (
        set PYTHON=%%P
        goto :found
    )
)
where py.exe >nul 2>&1 && set PYTHON=py.exe

:found
if "%PYTHON%"=="" (
    echo [ERROR] Python not found! Please install Python 3.9+ and add to PATH.
    echo          Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [*] Python: %PYTHON%

:: ---- Check dependencies ----
"%PYTHON%" -c "import voicemeeterlib" >nul 2>&1
if %errorLevel% NEQ 0 (
    echo [!] Installing dependencies...
    "%PYTHON%" -m pip install -r requirements.txt
    if %errorLevel% NEQ 0 (
        echo [ERROR] Failed to install dependencies.
        echo         Run manually: pip install -r requirements.txt
        pause
        exit /b 1
    )
)

:: ---- Run ----
echo [*] Starting VoiceMeeter Toggle...
"%PYTHON%" main.py
pause
