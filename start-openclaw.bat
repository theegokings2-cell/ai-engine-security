@echo off
echo ========================================
echo Starting OpenClaw Gateway (Minimax)
echo ========================================

:: Kill any conflicting simple telegram bot if running
taskkill /F /FI "WINDOWTITLE eq telegram-bot*" 2>nul

:: Check if gateway is already running
netstat -ano | findstr :18789 >nul
if %errorlevel%==0 (
    echo Gateway already running on port 18789
    echo Use Telegram to chat with Minimax
    goto :end
)

:: Start the gateway
echo Starting gateway...
start "OpenClaw Gateway" /min cmd /c "openclaw gateway"

:: Wait for startup
timeout /t 5 /nobreak >nul

:: Verify
netstat -ano | findstr :18789 >nul
if %errorlevel%==0 (
    echo.
    echo ========================================
    echo OpenClaw Gateway is RUNNING
    echo ========================================
    echo.
    echo Telegram bot is ready - send messages to your bot
    echo Model: Minimax M2.1
    echo.
    echo Commands in Telegram:
    echo   - Just type to chat with Minimax
    echo   - /reset - Start fresh conversation
    echo   - /model - Check current model
    echo.
) else (
    echo ERROR: Gateway failed to start
    echo Run manually: openclaw gateway
)

:end
pause
