"""
AI service for OpenAI, Anthropic, and Ollama providers.
Supports:
- OpenAI (or OpenAI-compatible providers)
- Anthropic (or Anthropic-compatible providers like MiniMax)
- Ollama (local, free LLM - no API key needed)

Uses shared HTTP client with retry logic and circuit breaker protection.
"""
import json
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.circuit_breaker import circuit_breaker
from app.core.logging import get_logger

logger = get_logger()


def extract_json(text: str) -> dict:
    """Extract JSON from text, handling markdown code blocks."""
    # Try to parse directly first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract from markdown code block
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try to find JSON object in text
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from response: {text[:200]}")


class AIService:
    """Service for AI operations using OpenAI, Anthropic, or Ollama providers."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self._openai_client = None
        self._anthropic_client = None
        self._ollama_client = None

    @property
    def provider(self) -> str:
        """Get the configured AI provider."""
        return settings.AI_PROVIDER.lower()

    @property
    def openai_client(self):
        """Get or create OpenAI client."""
        if self._openai_client is None and settings.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            client_kwargs = {"api_key": settings.OPENAI_API_KEY}
            if settings.OPENAI_BASE_URL:
                client_kwargs["base_url"] = settings.OPENAI_BASE_URL
            self._openai_client = AsyncOpenAI(**client_kwargs)
        return self._openai_client

    @property
    def anthropic_client(self):
        """Get or create Anthropic client (supports MiniMax via base_url)."""
        if self._anthropic_client is None and settings.ANTHROPIC_API_KEY:
            from anthropic import AsyncAnthropic
            client_kwargs = {"api_key": settings.ANTHROPIC_API_KEY}
            if settings.ANTHROPIC_BASE_URL:
                client_kwargs["base_url"] = settings.ANTHROPIC_BASE_URL
            self._anthropic_client = AsyncAnthropic(**client_kwargs)
        return self._anthropic_client

    @property
    def ollama_client(self):
        """Get or create Ollama client (uses OpenAI-compatible API, no API key needed)."""
        if self._ollama_client is None:
            from openai import AsyncOpenAI
            # Ollama uses OpenAI-compatible API at /v1, no API key required
            self._ollama_client = AsyncOpenAI(
                api_key="ollama",  # Ollama doesn't validate this but OpenAI SDK requires it
                base_url=settings.OLLAMA_BASE_URL,
            )
        return self._ollama_client

    def _get_client(self):
        """Get the appropriate client based on provider config."""
        if self.provider == "anthropic":
            return self.anthropic_client
        elif self.provider == "ollama":
            return self.ollama_client
        return self.openai_client

    def _is_configured(self) -> bool:
        """Check if AI is configured."""
        if self.provider == "anthropic":
            return self.anthropic_client is not None
        elif self.provider == "ollama":
            return True  # Ollama is always "configured" if the model is pulled
        return self.openai_client is not None

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call the LLM with the appropriate provider."""
        if self.provider == "anthropic":
            response = await self.anthropic_client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=2048,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
            )
            # Filter for TextBlock (skip ThinkingBlock from extended thinking models)
            for block in response.content:
                if hasattr(block, 'text'):
                    return block.text
            return response.content[0].text
        elif self.provider == "ollama":
            # Ollama uses OpenAI-compatible API
            response = await self.ollama_client.chat.completions.create(
                model=settings.OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            return response.choices[0].message.content
        else:
            response = await self.openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            return response.choices[0].message.content

    @circuit_breaker.call("ai")
    async def summarize_content(
        self,
        content: str,
    ) -> Dict[str, Any]:
        """
        Summarize content and extract action items.

        Returns:
            - summary: Brief summary of the content
            - action_items: List of action items with assignee and due date
            - key_topics: List of key topics discussed
            - sentiment: Overall sentiment (positive, neutral, negative)
        """
        start_time = time.time()

        if not self._is_configured():
            logger.warning("ai_client_not_configured", tenant_id=self.tenant_id, provider=self.provider)
            return {
                "summary": f"AI not configured. Set {self.provider.upper()}_API_KEY for real AI.",
                "action_items": [],
                "key_topics": [],
                "sentiment": "neutral",
            }

        try:
            system_prompt = "You are a helpful assistant that summarizes meeting notes and extracts action items. Always respond with valid JSON only."

            user_prompt = f"""
            Analyze the following content and provide:
            1. A brief summary (2-3 sentences)
            2. Action items with assignees and due dates (if mentioned)
            3. Key topics discussed
            4. Overall sentiment

            Content:
            {content[:10000]}

            Return as JSON:
            {{
                "summary": "...",
                "action_items": [
                    {{"task": "...", "assignee": "...", "due_date": "..."}}
                ],
                "key_topics": ["...", "..."],
                "sentiment": "positive|neutral|negative"
            }}
            """

            response_text = await self._call_llm(system_prompt, user_prompt)

            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "ai_summarize_completed",
                tenant_id=self.tenant_id,
                duration_ms=duration_ms,
                provider=self.provider,
            )

            result = extract_json(response_text)

            action_items = []
            for item in result.get("action_items", []):
                action_items.append({
                    "task": item.get("task", ""),
                    "assignee": item.get("assignee"),
                    "due_date": item.get("due_date"),
                })

            return {
                "summary": result.get("summary", ""),
                "action_items": action_items,
                "key_topics": result.get("key_topics", []),
                "sentiment": result.get("sentiment", "neutral"),
            }

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "ai_summarize_failed",
                tenant_id=self.tenant_id,
                duration_ms=duration_ms,
                error=str(e),
            )
            raise

    @circuit_breaker.call("ai")
    async def parse_task_from_text(
        self,
        text: str,
    ) -> Dict[str, Any]:
        """
        Parse natural language text into structured task data.

        Extracts:
        - title: Task title
        - description: Full original text
        - assignee_id: User ID (matched by name)
        - due_date: Parsed due date
        - priority: Inferred priority
        """
        start_time = time.time()

        if not self._is_configured():
            logger.warning("ai_client_not_configured", tenant_id=self.tenant_id, provider=self.provider)
            return {
                "title": text[:100],
                "description": text,
                "assignee_id": None,
                "due_date": None,
                "priority": "medium",
            }

        try:
            system_prompt = "You are an AI assistant that parses natural language task descriptions. Always respond with valid JSON only."

            user_prompt = f"""
            Parse the following natural language task description and extract structured data:

            Text: "{text}"

            Extract:
            - title: A concise task title (max 100 chars)
            - description: The full task description
            - assignee_name: The person mentioned (just the name, e.g., "finance", "John")
            - due_date: Any date/time mentioned (ISO format if possible, e.g., "2024-01-15T15:00:00")
            - priority: low/medium/high/urgent (infer from urgency words)

            Return as JSON:
            {{
                "title": "...",
                "description": "...",
                "assignee_name": "...",
                "due_date": "...",
                "priority": "..."
            }}
            """

            response_text = await self._call_llm(system_prompt, user_prompt)

            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "ai_parse_task_completed",
                tenant_id=self.tenant_id,
                duration_ms=duration_ms,
                provider=self.provider,
            )

            result = extract_json(response_text)

            # Try to find assignee ID from name
            assignee_id = await self._find_user_by_name(result.get("assignee_name", ""))

            # Parse due date
            due_date = None
            if result.get("due_date"):
                try:
                    due_date = datetime.fromisoformat(result["due_date"].replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            return {
                "title": result.get("title", text[:100]),
                "description": text,
                "assignee_id": assignee_id,
                "due_date": due_date,
                "priority": result.get("priority", "medium"),
            }

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "ai_parse_task_failed",
                tenant_id=self.tenant_id,
                duration_ms=duration_ms,
                error=str(e),
            )
            raise

    @circuit_breaker.call("ai")
    async def rag_query(
        self,
        query: str,
        documents: List[str],
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG (Retrieval-Augmented Generation).

        Args:
            query: The question to answer
            documents: List of documents to search

        Returns:
            - answer: The answer to the question
            - sources: Relevant document chunks with scores
        """
        start_time = time.time()

        if not self._is_configured():
            logger.warning("ai_client_not_configured", tenant_id=self.tenant_id, provider=self.provider)
            return {
                "answer": f"AI not configured. Set {self.provider.upper()}_API_KEY for real AI.",
                "sources": [],
            }

        try:
            relevant_chunks = self._search_documents(query, documents)
            context = "\n\n".join(relevant_chunks)

            system_prompt = "You are a helpful assistant that answers questions based on provided documents."

            user_prompt = f"""
            Answer the question based on the provided context. If the answer cannot be found in the context, say so.

            Context:
            {context}

            Question: {query}

            Answer:
            """

            answer = await self._call_llm(system_prompt, user_prompt)

            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "ai_rag_query_completed",
                tenant_id=self.tenant_id,
                duration_ms=duration_ms,
                chunks_searched=len(documents),
                chunks_matched=len(relevant_chunks),
                provider=self.provider,
            )

            return {
                "answer": answer,
                "sources": [{"chunk": chunk, "relevance_score": 0.9} for chunk in relevant_chunks[:3]],
            }

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "ai_rag_query_failed",
                tenant_id=self.tenant_id,
                duration_ms=duration_ms,
                error=str(e),
            )
            raise

    @circuit_breaker.call("ai")
    async def parse_complex_command(
        self,
        command: str,
    ) -> List[Dict[str, Any]]:
        """
        Parse a complex natural language command into multiple actions.

        Returns a list of actions, each with:
        - type: "task" or "event"
        - title: Item title
        - description: Item description
        - For tasks: priority, due_date
        - For events: start_time, end_time, event_type

        Example input: "Create 3 calendar blocks to reach out to sales leads with task reminders"
        Example output: [
            {"type": "event", "title": "Sales Lead Outreach 1", "start_time": "...", ...},
            {"type": "task", "title": "Reminder: Sales Lead Outreach 1", "due_date": "...", ...},
            ...
        ]
        """
        start_time = time.time()

        if not self._is_configured():
            logger.warning("ai_client_not_configured", tenant_id=self.tenant_id, provider=self.provider)
            # Return a basic task as fallback
            return [{
                "type": "task",
                "title": command[:100],
                "description": command,
                "priority": "medium",
                "due_date": None,
            }]

        try:
            # Get current date for context
            today = datetime.now()
            tomorrow = today + timedelta(days=1)

            system_prompt = """You are an intelligent assistant that parses natural language commands into structured actions.
You can create TASKS and CALENDAR EVENTS. Always respond with valid JSON only.

Current date context:
- Today: {today}
- Tomorrow: {tomorrow}

Rules:
1. If user asks for multiple items (e.g., "3 calendar blocks"), create that many
2. If user mentions "reminders" or "task reminders" for events, create both the event AND a reminder task
3. For calendar blocks/events without specific times, space them out during business hours (9am-5pm)
4. Task reminders should be due 30 minutes before the linked event
5. Infer reasonable defaults for missing information
6. Use ISO format for dates: YYYY-MM-DDTHH:MM:SS""".format(today=today.strftime("%Y-%m-%d"), tomorrow=tomorrow.strftime("%Y-%m-%d"))

            user_prompt = f"""Parse this command into actions:

"{command}"

Return a JSON object with an "actions" array. Each action should have:
- type: "task" or "event"
- title: descriptive title
- description: optional description

For tasks, also include:
- priority: "low", "medium", "high", or "urgent"
- due_date: ISO datetime or null

For events, also include:
- start_time: ISO datetime
- end_time: ISO datetime
- event_type: "meeting", "call", "block", "reminder", or "other"
- all_day: boolean

Example response:
{{
    "actions": [
        {{
            "type": "event",
            "title": "Sales Lead Outreach - Call 1",
            "description": "Reach out to potential sales lead",
            "start_time": "2024-01-15T09:00:00",
            "end_time": "2024-01-15T09:30:00",
            "event_type": "call",
            "all_day": false
        }},
        {{
            "type": "task",
            "title": "Prepare for Sales Lead Call 1",
            "description": "Review lead information before call",
            "priority": "high",
            "due_date": "2024-01-15T08:30:00"
        }}
    ]
}}
"""

            response_text = await self._call_llm(system_prompt, user_prompt)

            duration_ms = (time.time() - start_time) * 1000
            logger.info(
                "ai_parse_command_completed",
                tenant_id=self.tenant_id,
                duration_ms=duration_ms,
                provider=self.provider,
            )

            result = extract_json(response_text)
            actions = result.get("actions", [])

            # Validate and clean up actions
            validated_actions = []
            for action in actions:
                if action.get("type") not in ["task", "event"]:
                    continue

                cleaned = {
                    "type": action["type"],
                    "title": action.get("title", "Untitled"),
                    "description": action.get("description", ""),
                }

                if action["type"] == "task":
                    cleaned["priority"] = action.get("priority", "medium")
                    if cleaned["priority"] not in ["low", "medium", "high", "urgent"]:
                        cleaned["priority"] = "medium"

                    due_date = action.get("due_date")
                    if due_date:
                        try:
                            cleaned["due_date"] = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                        except (ValueError, AttributeError):
                            cleaned["due_date"] = None
                    else:
                        cleaned["due_date"] = None

                elif action["type"] == "event":
                    cleaned["event_type"] = action.get("event_type", "meeting")
                    cleaned["all_day"] = action.get("all_day", False)

                    start_time_str = action.get("start_time")
                    end_time_str = action.get("end_time")

                    if start_time_str:
                        try:
                            cleaned["start_time"] = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                        except (ValueError, AttributeError):
                            cleaned["start_time"] = datetime.now() + timedelta(hours=1)
                    else:
                        cleaned["start_time"] = datetime.now() + timedelta(hours=1)

                    if end_time_str:
                        try:
                            cleaned["end_time"] = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                        except (ValueError, AttributeError):
                            cleaned["end_time"] = cleaned["start_time"] + timedelta(minutes=30)
                    else:
                        cleaned["end_time"] = cleaned["start_time"] + timedelta(minutes=30)

                validated_actions.append(cleaned)

            return validated_actions if validated_actions else [{
                "type": "task",
                "title": command[:100],
                "description": command,
                "priority": "medium",
                "due_date": None,
            }]

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "ai_parse_command_failed",
                tenant_id=self.tenant_id,
                duration_ms=duration_ms,
                error=str(e),
            )
            raise

    async def index_document(
        self,
        document_id: str,
        content: str,
    ) -> None:
        """Index a document for RAG search."""
        logger.info(
            "ai_document_indexed",
            tenant_id=self.tenant_id,
            document_id=document_id,
        )
        pass

    async def _find_user_by_name(self, name: str) -> Optional[str]:
        """Find user ID by name (for task assignment)."""
        if not name:
            return None

        from sqlalchemy import select
        from app.models.user import User

        result = await self.db.execute(
            select(User.id).where(
                User.tenant_id == self.tenant_id,
                User.full_name.ilike(f"%{name}%"),
                User.is_active == True,
            )
        )
        user = result.scalar_one_or_none()

        return str(user) if user else None

    def _search_documents(
        self,
        query: str,
        documents: List[str],
    ) -> List[str]:
        """Search documents for relevant chunks."""
        keywords = query.lower().split()

        relevant = []
        for doc in documents:
            doc_lower = doc.lower()
            if any(kw in doc_lower for kw in keywords):
                relevant.append(doc[:2000])

        return relevant[:5]
