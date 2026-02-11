# Voice Integration Plan for AI Office Manager

**Date:** 2026-02-03
**Phase:** 3 - Voice Integration
**Status:** Planning

---

## Overview

Add voice capabilities to make the AI Office Manager truly hands-free:
- 🎙️ Natural voice responses (ElevenLabs)
- 📞 AI phone reception (VAPI/Retell AI)
- 🎯 Voice command scheduling

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI Office Manager                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ ElevenLabs   │    │  VAPI/Retell │    │   Whisper    │      │
│  │  TTS         │    │    AI        │    │    STT       │      │
│  │ (Text→Voice) │    │  (Phone)     │    │ (Voice→Text) │      │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘      │
│         │                   │                   │               │
│         └───────────────────┼───────────────────┘               │
│                             │                                   │
│                     ┌───────▼───────┐                          │
│                     │  Voice Router │                          │
│                     │  (Orchestration)                        │
│                     └───────┬───────┘                          │
│                             │                                   │
│         ┌───────────────────┼───────────────────┐            │
│         │                   │                   │            │
│    ┌────▼────┐       ┌─────▼─────┐       ┌─────▼─────┐     │
│    │ Telegram │       │  Phone    │       │  In-App   │     │
│    │   Bot    │       │  Calls    │       │  Voice   │     │
│    └──────────┘       └───────────┘       └───────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. ElevenLabs TTS Integration

### Purpose
Convert AI text responses to natural-sounding voice.

### Provider
- **ElevenLabs** - Best quality AI voices
- Alternatives: OpenAI TTS, Google Cloud TTS, Amazon Polly

### Implementation

**Step 1: Install SDK**
```bash
pip install elevenlabs
```

**Step 2: Configuration**
```python
# app/core/config.py
ELEVENLABS_API_KEY: Optional[str] = Field(default=None)
ELEVENLABS_VOICE_ID: str = Field(default="21m00Tcm4TlvDq8ikWAM")  # Default voice
ELEVENLABS_MODEL: str = Field(default="eleven_monolingual_v1")
```

**Step 3: Service**
```python
# app/services/voice_service.py
import elevenlabs
from pydantic import BaseModel

class VoiceSettings(BaseModel):
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    model: str = "eleven_monolingual_v1"
    stability: float = 0.5
    similarity_boost: float = 0.75

class VoiceService:
    """ElevenLabs TTS service."""
    
    def __init__(self, api_key: str, settings: VoiceSettings = None):
        elevenlabs.set_api_key(api_key)
        self.settings = settings or VoiceSettings()
    
    async def text_to_speech(
        self,
        text: str,
        voice_id: str = None,
        model: str = None
    ) -> bytes:
        """Convert text to speech audio."""
        voice = voice_id or self.settings.voice_id
        model = model or self.settings.model
        
        audio = elevenlabs.generate(
            text=text,
            voice=voice,
            model=model
        )
        return audio
    
    async def text_to_speech_file(
        self,
        text: str,
        output_path: str,
        voice_id: str = None
    ) -> str:
        """Convert text to speech and save to file."""
        audio = await self.text_to_speech(text, voice_id)
        with open(output_path, "wb") as f:
            f.write(audio)
        return output_path
    
    async def stream_speech(
        self,
        text: str,
        voice_id: str = None
    ):
        """Stream speech to file/websocket."""
        audio_generator = elevenlabs.generate(
            text=text,
            voice=voice_id or self.settings.voice_id,
            stream=True
        )
        for chunk in audio_generator:
            yield chunk

# Usage
voice_service = VoiceService(settings.ELEVENLABS_API_KEY)
audio = await voice_service.text_to_speech("Your appointment is confirmed for tomorrow at 2 PM.")
```

**Step 4: Available Voices**
| Voice ID | Name | Gender | Style |
|----------|------|--------|-------|
| 21m00Tcm4TlvDq8ikWAM | Adam | Male | Deep, confident |
| AZnzlk1XvdvUeBnXmlNG | Bella | Female | Soft, warm |
| nPczCjz82KWdKScP46sk | Charlie | Male | Casual |
| *更多声音...* | | | |

**Step 5: Pricing**
- Free tier: 10,000 characters/month
- Starter: $5/month = 30,000 characters
- Creator: $22/month = 100,000 characters

---

## 2. Phone Reception (VAPI/Retell AI)

### Purpose
AI answers phone calls and handles scheduling.

### Provider Comparison

| Feature | VAPI | Retell AI |
|---------|------|-----------|
| Pricing | $0.15/min | $0.06/min |
| Voices | 10+ | 50+ |
| STT | Whisper | Whisper |
| Latency | ~300ms | ~400ms |
| Phone Numbers | US/Canada | US/Canada/UK |

**Recommendation:** Start with **VAPI** (simpler), switch to **Retell AI** (cheaper at scale)

### VAPI Implementation

**Step 1: Sign Up**
1. Go to https://vapi.ai
2. Create account and get API key
3. Purchase phone number ($1/month)

**Step 2: Configuration**
```python
# app/core/config.py
VAPI_API_KEY: Optional[str] = Field(default=None)
VAPI_PHONE_NUMBER: Optional[str] = Field(default=None)
VAPI_ASSISTANT_ID: Optional[str] = Field(default=None)
```

**Step 3: Create Assistant**
```json
{
  "name": "Office Manager AI",
  "model": {
    "provider": "openai",
    "model": "gpt-4",
    "system_prompt": "You are the AI receptionist for [Company Name]. "
    "Your job is to: "
    "1. Answer phone calls professionally "
    "2. Schedule appointments "
    "3. Answer basic questions "
    "4. Take messages "
    "Speak clearly and concisely."
  },
  "voice": {
    "provider": "elevenlabs",
    "voice_id": "21m00Tcm4TlvDq8ikWAM"
  },
  "transcriber": {
    "provider": "deepgram",
    "model": "nova-2"
  }
}
```

**Step 4: API Integration**
```python
# app/services/phone_service.py
import httpx
from pydantic import BaseModel
from typing import Optional

class PhoneCall(BaseModel):
    id: str
    phone_number: str
    status: str
    duration: int
    recording_url: Optional[str]

class PhoneService:
    """VAPI phone service for AI call handling."""
    
    def __init__(self, api_key: str, assistant_id: str):
        self.api_key = api_key
        self.assistant_id = assistant_id
        self.base_url = "https://api.vapi.ai"
    
    async def create_call(
        self,
        phone_number: str,
        assistant_id: str = None
    ) -> PhoneCall:
        """Initiate an outbound call."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "assistant_id": assistant_id or self.assistant_id,
            "phone_number": {
                "number": phone_number,
                "type": "external"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/call",
                json=payload,
                headers=headers
            )
            return PhoneCall(**response.json())
    
    async def get_call_status(self, call_id: str) -> PhoneCall:
        """Get status of a call."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/call/{call_id}",
                headers=headers
            )
            return PhoneCall(**response.json())
    
    async def end_call(self, call_id: str) -> bool:
        """End an active call."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {"status": "ended"}
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/call/{call_id}",
                json=payload,
                headers=headers
            )
            return response.status_code == 200

# Usage
phone_service = PhoneService(
    api_key=settings.VAPI_API_KEY,
    assistant_id=settings.VAPI_ASSISTANT_ID
)
call = await phone_service.create_call("+1234567890")
```

**Step 5: Webhook Handler**
```python
# app/integrations/phone.py
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()

class VapiWebhook(BaseModel):
    event: str
    call: dict
    transcript: Optional[str] = None

@router.post("/webhooks/vapi")
async def vapi_webhook(request: Request, webhook: VapiWebhook):
    """Handle VAPI webhook events."""
    
    if webhook.event == "call.ended":
        # Save transcript to customer record
        customer_phone = webhook.call["phone_number"]
        transcript = webhook.transcript or ""
        
        logger.info(f"Call ended with {customer_phone}")
        logger.info(f"Transcript: {transcript}")
        
        # Extract action items from transcript
        if "schedule" in transcript.lower():
            await process_scheduling_request(customer_phone, transcript)
        
    elif webhook.event == "call.transcript":
        # Real-time transcript processing
        await handle_transcript(webhook.transcript)
    
    return {"status": "received"}
```

**Step 6: Phone Call Flow**
```
Incoming Call
     │
     ▼
┌─────────────┐
│  AI Answers │ ← VAPI handles phone connection
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────────┐
│  Greeting   │────▶│ STT (Whisper)  │
└─────────────┘     └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  GPT-4         │
                   │  (Understand)  │
                   └────────┬────────┘
                            │
           ┌────────────────┼────────────────┐
           │                │                │
           ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Schedule │    │ Question │    │  Message │
    │  Appt    │    │  Answer  │    │   Take   │
    └──────────┘    └──────────┘    └──────────┘
           │                │                │
           └────────────────┼────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  TTS (11Labs)  │
                   │  (Speak back)  │
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  Call Continues │
                   └─────────────────┘
```

---

## 3. Speech-to-Text (Whisper)

### Purpose
Convert voice commands to text for AI processing.

### Implementation

```python
# app/services/stt_service.py
import openai
from pydantic import BaseModel
from typing import Optional

class TranscriptionResult(BaseModel):
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None

class STTService:
    """Whisper speech-to-text service."""
    
    def __init__(self, api_key: str):
        openai.api_key = api_key
    
    async def transcribe_audio(
        self,
        audio_file: bytes,
        model: str = "whisper-1",
        language: str = None
    ) -> TranscriptionResult:
        """Transcribe audio to text."""
        import io
        
        audio_io = io.BytesIO(audio_file)
        audio_io.name = "audio.mp3"
        
        response = await openai.Audio.atranscribe(
            model=model,
            file=audio_io,
            language=language
        )
        
        return TranscriptionResult(
            text=response["text"],
            duration=response.get("duration")
        )
    
    async def transcribe_file(
        self,
        file_path: str,
        model: str = "whisper-1"
    ) -> TranscriptionResult:
        """Transcribe audio file to text."""
        with open(file_path, "rb") as f:
            response = await openai.Audio.atranscribe(
                model=model,
                file=f
            )
        
        return TranscriptionResult(text=response["text"])
```

---

## 4. Unified Voice Service

```python
# app/services/unified_voice.py
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class VoiceChannel(str, Enum):
    TELEGRAM = "telegram"
    PHONE = "phone"
    IN_APP = "in_app"

class VoiceRequest(BaseModel):
    text: str
    channel: VoiceChannel
    recipient_id: Optional[str] = None
    voice_id: Optional[str] = None

class UnifiedVoiceService:
    """Unified service for all voice interactions."""
    
    def __init__(
        self,
        tts_service,
        stt_service,
        phone_service
    ):
        self.tts = tts_service
        self.stt = stt_service
        self.phone = phone_service
    
    async def send_voice_message(
        self,
        text: str,
        channel: VoiceChannel,
        recipient: str = None,
        voice_id: str = None
    ) -> bool:
        """Send voice message to user."""
        # Convert text to speech
        audio = await self.tts.text_to_speech(text, voice_id)
        
        if channel == VoiceChannel.TELEGRAM:
            return await send_telegram_voice(recipient, audio)
        
        elif channel == VoiceChannel.PHONE:
            return await self.phone.initiate_call(recipient, audio)
        
        elif channel == VoiceChannel.IN_APP:
            return await stream_voice_to_browser(recipient, audio)
        
        return False
    
    async def process_voice_input(
        self,
        audio: bytes,
        channel: VoiceChannel
    ) -> str:
        """Process voice input and return text."""
        # Convert speech to text
        transcription = await self.stt.transcribe_audio(audio)
        return transcription.text
```

---

## 5. Example Voice Interactions

### Example 1: Phone Scheduling
```
AI: "Thank you for calling [Company]. How can I help you today?"

Customer: "Hi, I'd like to book an appointment."

AI: "Sure! What type of service are you looking for?"

Customer: "I need an oil change."

AI: "I have openings tomorrow at 10 AM, 2 PM, and 4 PM. Which works best?"

Customer: "2 PM works."

AI: "Perfect! I've booked you for an oil change tomorrow at 2 PM. 
      Can I get your name and phone number?"

Customer: "It's John Smith, 555-0123."

AI: "Thanks, John! I've saved your information. 
      You'll receive a reminder tomorrow. 
      Is there anything else I can help with?"

Customer: "No, that's all. Thanks!"

AI: "You're welcome! Have a great day!"
```

### Example 2: Voice Command via Telegram
```
User: 🎤 (voice message)

AI: [Processes voice]
   "Schedule a meeting with John tomorrow at 3 PM."

AI: [Confirms]
   "Sure! I'll schedule a meeting with John tomorrow at 3 PM.
    Should I send calendar invites?"

User: "Yes please!"

AI: [Sends calendar invite]
   "Done! Calendar invites sent to both you and John."
```

---

## 6. Pricing Estimates

| Service | Free Tier | Cost at Scale |
|---------|-----------|---------------|
| ElevenLabs | 10k chars/mo | ~$22/mo for 100k chars |
| VAPI | - | $0.15/min (~$650/mo for 1000 calls) |
| Whisper | - | $0.006/min (~$36/mo for 1000 calls) |
| **Total** | - | **~$700/mo for production** |

---

## 7. Implementation Timeline

### Week 1: ElevenLabs TTS
- [ ] Set up ElevenLabs account
- [ ] Implement TTS service
- [ ] Add voice settings to config
- [ ] Test with Telegram voice messages
- [ ] Add voice selection options

### Week 2: VAPI Phone Reception
- [ ] Set up VAPI account
- [ ] Purchase phone number
- [ ] Create AI assistant prompt
- [ ] Implement call handling
- [ ] Set up webhooks
- [ ] Test call flows

### Week 3: Whisper STT
- [ ] Implement STT service
- [ ] Add voice command parsing
- [ ] Train on company vocabulary
- [ ] Test accuracy

### Week 4: Integration & Polish
- [ ] Unify voice services
- [ ] Add voice preferences
- [ ] Test all channels
- [ ] Optimize latency
- [ ] Launch!

---

## 8. Future Enhancements

### Advanced Features
- **Voice cloning** - AI speaks in owner's voice
- **Real-time translation** - Multi-language support
- **Emotion detection** - Adjust tone based on customer mood
- **Call recording analysis** - Improve AI from real calls
- **Custom voice personas** - Different voices for different contexts

### Integration Ideas
- **Zoom/Teams** - AI joins meetings, takes notes
- **CRM** - Voice commands to update records
- **IVR System** - Replace traditional phone menu

---

## 9. Success Metrics

| Metric | Target |
|--------|--------|
| Call answering time | < 3 seconds |
| Scheduling accuracy | > 95% |
| Customer satisfaction | > 4.5/5 |
| Voice recognition accuracy | > 95% |
| Cost per call | < $0.25 |

---

## Resources

- **ElevenLabs:** https://elevenlabs.io
- **VAPI:** https://vapi.ai
- **Retell AI:** https://retellai.com
- **OpenAI Whisper:** https://openai.com/research/whisper

---

**Questions?** Review the service implementations above or consult provider documentation.
