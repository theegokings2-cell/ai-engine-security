"""
Telegram Bot for Office Manager
Uses the backend API for all operations.
"""

import os
import asyncio
from typing import Dict, Any
import aiohttp
from datetime import datetime


class TelegramBot:
    """Telegram bot that integrates with Office Manager API."""
    
    def __init__(self, token: str = None, api_base_url: str = "http://localhost:8000/api/v1"):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.api_base_url = api_base_url.rstrip("/")
        self.api_client = aiohttp.ClientSession()
        self.offset = 0
        self.running = False
        
    async def close(self):
        """Close the HTTP session."""
        await self.api_client.close()
    
    async def _api_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the Telegram API."""
        url = f"https://api.telegram.org/bot{self.token}/{method}"
        async with self.api_client.request(method, url, **kwargs) as response:
            return await response.json()
    
    async def _call_backend(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the backend API."""
        url = f"{self.api_base_url}{endpoint}"
        headers = kwargs.pop("headers", {})
        
        # Get token from storage or environment
        token = os.getenv("API_ACCESS_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        async with self.api_client.request(method, url, headers=headers, **kwargs) as response:
            return await response.json()
    
    async def get_updates(self) -> list:
        """Get new updates from Telegram."""
        data = {
            "offset": self.offset,
            "timeout": 30,
        }
        result = await self._api_request("getUpdates", **data)
        return result.get("result", [])
    
    async def send_message(self, chat_id: int, text: str, **kwargs) -> Dict[str, Any]:
        """Send a message to a chat."""
        data = {
            "chat_id": chat_id,
            "text": text,
            **kwargs,
        }
        return await self._api_request("sendMessage", json=data)
    
    async def handle_update(self, update: Dict[str, Any]) -> str:
        """Handle a single update."""
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        user = message.get("from", {})
        user_id = user.get("id")
        
        if not text or not chat_id:
            return ""
        
        # Remove bot mention if present
        text = text.replace("@OfficeManagerBot", "").strip()
        
        # Handle commands
        if text.startswith("/"):
            return await self._handle_command(chat_id, text, user_id)
        else:
            # Handle as natural language task creation
            return await self._handle_nl_task(chat_id, text, user_id)
    
    async def _handle_command(self, chat_id: int, command: str, user_id: int) -> str:
        """Handle a command."""
        parts = command.split(" ", 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "/start":
            return (
                "👋 Welcome to Office Manager Bot!\n\n"
                "I can help you manage tasks, calendar events, and notes.\n\n"
                "Commands:\n"
                "/tasks - List your tasks\n"
                "/calendar today - Show today's events\n"
                "/note summarize <id> - Summarize a note with AI\n"
                "\nJust type naturally to create tasks, e.g.:\n"
                "'Remind me to call John tomorrow at 2pm'"
            )
        
        elif cmd == "/tasks":
            return await self._cmd_tasks(chat_id, args)
        
        elif cmd == "/calendar":
            return await self._cmd_calendar(chat_id, args)
        
        elif cmd == "/note":
            return await self._cmd_note(chat_id, args)
        
        elif cmd == "/help":
            return (
                "📚 Available Commands:\n\n"
                "/tasks - List all your tasks\n"
                "/tasks pending - Show only pending tasks\n"
                "/tasks completed - Show completed tasks\n"
                "/calendar today - Show today's events\n"
                "/calendar week - Show this week's events\n"
                "/note summarize <note_id> - Get AI summary of a note\n"
                "\n💡 Just type naturally to create tasks!"
            )
        
        else:
            return f"Unknown command: {cmd}. Type /help for available commands."
    
    async def _cmd_tasks(self, chat_id: int, args: str) -> str:
        """Handle /tasks command."""
        try:
            # Get tasks from API
            result = await self._call_backend("GET", "/tasks")
            
            if "error" in result:
                return f"Error fetching tasks: {result.get('error')}"
            
            tasks = result if isinstance(result, list) else []
            
            # Filter based on args
            if "pending" in args.lower():
                tasks = [t for t in tasks if t.get("status") != "completed"]
            elif "completed" in args.lower():
                tasks = [t for t in tasks if t.get("status") == "completed"]
            
            if not tasks:
                return "📋 No tasks found."
            
            # Format response
            lines = ["📋 *Your Tasks:*\n"]
            for i, task in enumerate(tasks[:10], 1):
                status = "✅" if task.get("status") == "completed" else "○"
                title = task.get("title", task.get("content", "")[:50])
                due_date = task.get("due_date", "")
                
                line = f"{status} {i}. {title}"
                if due_date:
                    line += f" (📅 {due_date[:10]})"
                lines.append(line)
            
            if len(tasks) > 10:
                lines.append(f"\n...and {len(tasks) - 10} more tasks")
            
            return "\n".join(lines)
        
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _cmd_calendar(self, chat_id: int, args: str) -> str:
        """Handle /calendar command."""
        try:
            from datetime import datetime
            
            # Get today's events
            today = datetime.now().strftime("%Y-%m-%d")
            result = await self._call_backend(
                "GET",
                f"/calendar?start_date={today}T00:00:00&end_date={today}T23:59:59"
            )
            
            if "error" in result:
                return f"Error fetching events: {result.get('error')}"
            
            events = result if isinstance(result, list) else []
            
            if not events:
                return "📅 No events scheduled for today."
            
            # Format response
            lines = ["📅 *Today's Events:*\n"]
            for event in events[:10]:
                title = event.get("title", "Untitled")
                start = event.get("start_time", "") or event.get("start", "")
                
                try:
                    if start:
                        dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                        time_str = dt.strftime("%I:%M %p")
                    else:
                        time_str = "All day"
                except:
                    time_str = start[:5] if len(start) >= 5 else ""
                
                lines.append(f"• {time_str} - {title}")
            
            return "\n".join(lines)
        
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _cmd_note(self, chat_id: int, args: str) -> str:
        """Handle /note command."""
        if not args.lower().startswith("summarize"):
            return "Usage: /note summarize <note_id>"
        
        parts = args.split(" ", 2)
        if len(parts) < 2:
            return "Usage: /note summarize <note_id>"
        
        note_id = parts[1]
        
        try:
            result = await self._call_backend("POST", f"/notes/{note_id}/summarize")
            
            if "error" in result:
                return f"Error: {result.get('error')}"
            
            summary = result.get("summary", "No summary available")
            action_items = result.get("action_items", [])
            
            lines = [f"📝 *Note Summary:*\n\n{summary}"]
            
            if action_items:
                lines.append("\n*Action Items:*")
                for item in action_items[:5]:
                    lines.append(f"• {item}")
            
            return "\n".join(lines)
        
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def _handle_nl_task(self, chat_id: int, text: str, user_id: int) -> str:
        """Handle natural language task creation."""
        try:
            result = await self._call_backend(
                "POST",
                "/tasks/from-text",
                json={"text": text}
            )
            
            if "error" in result:
                return f"❌ Could not create task: {result.get('error')}"
            
            task_title = result.get("title", result.get("content", "Task"))
            return f"✅ Created task: *{task_title}*"
        
        except Exception as e:
            return f"Error creating task: {str(e)}"
    
    async def run(self):
        """Run the bot polling loop."""
        if not self.token:
            print("ERROR: Telegram bot token not set!")
            return
        
        self.running = True
        print("Telegram Bot started...")
        
        while self.running:
            try:
                updates = await self.get_updates()
                
                for update in updates:
                    update_id = update.get("update_id", 0)
                    
                    if update_id >= self.offset:
                        self.offset = update_id + 1
                        
                        response = await self.handle_update(update)
                        
                        if response:
                            message = update.get("message", {})
                            chat_id = message.get("chat", {}).get("id")
                            
                            if chat_id:
                                await self.send_message(chat_id, response, parse_mode="Markdown")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Error in polling loop: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Stop the bot."""
        self.running = False


async def main():
    """Main entry point for the bot."""
    bot = TelegramBot()
    
    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\nStopping bot...")
        bot.stop()
    finally:
        await bot.close()


if __name__ == "__main__":
    import sys
    asyncio.run(main())
