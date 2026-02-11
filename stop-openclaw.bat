@echo off
echo Stopping OpenClaw Gateway...
openclaw gateway stop 2>nul
echo.
echo Gateway stopped. Telegram bot will no longer respond.
pause
