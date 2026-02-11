"""
Twilio integration for SMS (used by SMS service).
"""
from typing import Any, Dict, Optional


class TwilioClient:
    """Twilio client wrapper (optional - can use twilio library directly)."""
    
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
    ):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
    
    async def send_sms(self, to: str, body: str) -> Dict[str, Any]:
        """Send an SMS via Twilio."""
        try:
            from twilio.rest import Client
            
            client = Client(self.account_sid, self.auth_token)
            message = client.messages.create(
                body=body[:1600],
                from_=self.from_number,
                to=to,
            )
            
            return {
                "status": "sent",
                "message_id": message.sid,
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }
    
    async def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """Get the status of a sent message."""
        try:
            from twilio.rest import Client
            
            client = Client(self.account_sid, self.auth_token)
            message = client.messages(message_id).fetch()
            
            return {
                "status": message.status,
                "to": message.to,
                "sent_at": str(message.date_sent) if message.date_sent else None,
            }
        
        except Exception as e:
            return {"status": "error", "error": str(e)}
