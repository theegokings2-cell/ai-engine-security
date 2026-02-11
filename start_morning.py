#!/usr/bin/env python3
"""
Office Manager Morning Startup Script
Starts the API server and Telegram bot for morning operations.
"""
import subprocess
import sys
import os
import time
import signal

def start_api():
    """Start the API server."""
    print("[1/2] Starting API server on port 8000...")
    api_process = subprocess.Popen(
        [sys.executable, "-B", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=os.path.join(os.path.dirname(__file__), "..", "office-manager-api"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    return api_process

def start_telegram_bot():
    """Start the Telegram bot."""
    print("[2/2] Starting Telegram bot...")
    bot_process = subprocess.Popen(
        [sys.executable, "telegram_bot.py"],
        cwd=os.path.join(os.path.dirname(__file__), "..", "services"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    return bot_process

def wait_for_api(url="http://localhost:8000/health", timeout=30):
    """Wait for API to be ready."""
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except:
            pass
        time.sleep(1)
    return False

def main():
    print("=" * 50)
    print("OFFICE MANAGER - MORNING STARTUP")
    print("=" * 50)
    
    # Check Telegram token
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or token == "your-telegram-bot-token":
        print("\nWARNING: TELEGRAM_BOT_TOKEN not set or is placeholder!")
        print("The Telegram bot will not work without a real token.")
        print("Get a token from @BotFather on Telegram.")
        print("")
    
    # Start API server
    api_process = start_api()
    
    # Wait for API to be ready
    print("\nWaiting for API to be ready...")
    if wait_for_api():
        print("API is ready!")
    else:
        print("WARNING: API did not become ready in time. Check logs.")
    
    # Start Telegram bot (only if token is set)
    if token and token != "your-telegram-bot-token":
        bot_process = start_telegram_bot()
        print("Telegram bot started!")
    else:
        print("\nSkipping Telegram bot (no valid token)")
        bot_process = None
    
    print("\n" + "=" * 50)
    print("SERVICES STARTED")
    print("=" * 50)
    print(f"API:      http://localhost:8000")
    print(f"Health:   http://localhost:8000/health")
    print(f"Docs:     http://localhost:8000/docs")
    
    if bot_process:
        print(f"Bot:      Running (PID: {bot_process.pid})")
    
    print("\nPress Ctrl+C to stop all services...")
    
    try:
        # Monitor processes
        while True:
            time.sleep(5)
            if api_process.poll() is not None:
                print("API process died! Restarting...")
                api_process = start_api()
            if bot_process and bot_process.poll() is not None:
                print("Bot process died! Restarting...")
                bot_process = start_telegram_bot()
    except KeyboardInterrupt:
        print("\nShutting down...")
        if api_process:
            api_process.terminate()
        if bot_process:
            bot_process.terminate()
        print("Done.")

if __name__ == "__main__":
    main()
