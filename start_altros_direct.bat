@echo off
title ALTROS — Starting...
set ALTROS_DIR=C:\Users\manis\ALTROS
set PYTHONIOENCODING=utf-8
color 0B

echo.
echo  ================================================
echo   ALTROS — Autonomous Learning AI System
echo  ================================================
echo.

:: ── Kill old processes ──────────────────────────────────────
echo [0/4] Cleaning up old processes...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im py.exe >nul 2>&1
taskkill /f /im ngrok.exe >nul 2>&1
timeout /t 2 /nobreak >nul

:: ── Start Ollama ─────────────────────────────────────────────
echo [1/4] Starting Ollama...
start "" "ollama" serve
timeout /t 4 /nobreak >nul
echo     Ollama started.

:: ── Start ALTROS ─────────────────────────────────────────────
echo [2/4] Starting ALTROS...
start "" cmd /k "cd /d %ALTROS_DIR% && py -3.12 main.py"
echo     ALTROS starting...

:: ── Wait for ALTROS server (port 8000) ───────────────────────
echo [3/4] Waiting for ALTROS server on port 8000...
set /a counter=0
:waitloop
timeout /t 2 /nobreak >nul
set /a counter+=2
curl -s http://localhost:8000/status >nul 2>&1
if %errorlevel% == 0 (
    echo     Server ready after %counter%s!
    goto serverready
)
if %counter% GEQ 60 (
    echo     Timeout — server did not start in 60s
    echo     Check ALTROS terminal for errors
    pause
    exit
)
echo     Waiting... %counter%s
goto waitloop

:serverready
:: ── Start Ngrok ──────────────────────────────────────────────
echo [4/4] Starting Ngrok tunnel...
start "" cmd /k "ngrok http 8000"

:: Wait for ngrok to initialize
timeout /t 5 /nobreak >nul

:: ── Get Ngrok Public URL ────────────────────────────────────
echo     Detecting Ngrok public URL...

set "NGROK_URL="

for /f "delims=" %%A in ('powershell -NoProfile -Command "(Invoke-RestMethod 'http://127.0.0.1:4040/api/tunnels').tunnels | Where-Object {$_.proto -eq 'https'} | Select-Object -First 1 -ExpandProperty public_url"') do (
    set "NGROK_URL=%%A"
)

echo.
echo  ================================================
echo   ALTROS is ONLINE!
echo  ================================================
echo.

if defined NGROK_URL (
    echo   Public URL:
    echo   %NGROK_URL%
    echo.
    echo   Opening ALTROS automatically...
    echo  ================================================
    start "" "%NGROK_URL%"
) else (
    echo   Could not detect public URL.
    echo   Open http://localhost:4040 to check Ngrok.
    echo   ================================================
)

echo.
pause
