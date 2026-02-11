"""
Telegram bot webhook handler.
"""
from typing import Any, Dict

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.config import settings


router = APIRouter(prefix="/integrations/telegram", tags=["Telegram"])


class TelegramUpdate(BaseModel):
    """Telegram webhook update."""
    update_id: int
    message: Dict[str, Any] = None
    callback_query: Dict[str, Any] = None


class TelegramWebhookHandler:
    """Handler for Telegram bot webhooks."""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
    
    async def handle_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming Telegram update.
        
        Supports:
        - /start: Start the bot
        - /task <text>: Create a task
        - /note <text>: Create a note
        - /help: Show help
        """
        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        
        if not text:
            return {"status": "ok"}
        
        # Parse command
        if text.startswith("/start"):
            response = (
                "👋 Welcome to Office Manager Bot!\n\n"
                "Commands:\n"
                "/task <text> - Create a task from text\n"
                "/note <text> - Create a quick note\n"
                "/help - Show this help"
            )
        elif text.startswith("/task"):
            task_text = text[5:].strip()
            if task_text:
                # Create task (would call task service)
                return await self._create_task(chat_id, task_text)
            else:
                response = "Please provide task description. Example: /task Review Q3 report"
        elif text.startswith("/note"):
            note_text = text[5:].strip()
            if note_text:
                # Create note (would call note service)
                return await self._create_note(chat_id, note_text)
            else:
                response = "Please provide note content. Example: /note Meeting with John"
        elif text.startswith("/help"):
            response = (
                "📋 Office Manager Bot Commands:\n\n"
                "/task <text> - Create a task from natural language\n"
                "/note <text> - Create a quick note\n"
                "/calendar - Get today's events\n"
                "/help - Show this help"
            )
        elif text.startswith("/calendar"):
            # Get calendar events
            return await self._get_calendar(chat_id)
        else:
            response = (
                "🤔 I didn't understand that command.\n"
                "Use /help to see available commands."
            )
        
        # Send response
        await self._send_message(chat_id, response)
        
        return {"status": "ok"}
    
    async def _create_task(self, chat_id: str, text: str) -> Dict[str, Any]:
        """Create a task from Telegram message."""
        # This would call the task service with natural language parsing
        response = f"✅ Task created from your message:\n\n\"{text[:100]}...\""
        await self._send_message(chat_id, response)
        return {"status": "ok"}
    
    async def _create_note(self, chat_id: str, text: str) -> Dict[str, Any]:
        """Create a note from Telegram message."""
        response = f"📝 Note saved:\n\n\"{text[:100]}...\""
        await self._send_message(chat_id, response)
        return {"status": "ok"}
    
    async def _get_calendar(self, chat_id: str) -> Dict[str, Any]:
        """Get calendar events for today."""
        # This would call the calendar service
        response = "📅 Today's Events:\n\nNo events scheduled."
        await self._send_message(chat_id, response)
        return {"status": "ok"}
    
    async def _send_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        """Send a message to a Telegram chat."""
        if not self.bot_token:
            return {"status": "stub", "chat_id": chat_id, "text": text}
        
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                },
            )
        
        return response.json()


handler = TelegramWebhookHandler()


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Telegram webhook endpoint.
    
    Configure this endpoint in Telegram BotFather:
    /setwebhook -> https://your-domain.com/integrations/telegram/webhook
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        return {"status": "stub", "message": "Telegram not configured"}
    
    update_data = await request.json()
    
    try:
        await handler.handle_update(update_data)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/webhook")
async def telegram_webhook_verify():
    """Verify webhook endpoint for Telegram."""
    return {"status": "ok", "message": "Telegram webhook active"}


@router.post("/send")
async def send_telegram_message(
    chat_id: str,
    text: str,
):
    """Send a message to a Telegram user (for notifications)."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return {"status": "stub", "chat_id": chat_id, "text": text}
    
    import httpx
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
            },
        )
    
    return response.json()
