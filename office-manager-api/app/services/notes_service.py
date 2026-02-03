"""
Notes service with AI summarization and RAG Q&A.
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note


class NotesService:
    """Service for note operations with AI features."""
    
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    async def list_notes(
        self,
        limit: int = 100,
        offset: int = 0,
        include_rag_docs: bool = False,
        user_id: Optional[str] = None,
    ) -> List[Note]:
        """List notes with optional filters."""
        query = select(Note).where(Note.tenant_id == self.tenant_id)
        
        if not include_rag_docs:
            query = query.where(Note.is_rag_document == "N")
        
        if user_id:
            # Employees see only their own notes
            query = query.where(Note.created_by_id == user_id)
        
        query = query.order_by(Note.created_at.desc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_note(
        self,
        note_id: str,
        user_id: str,
        user_role: str,
    ) -> Optional[Note]:
        """Get a specific note by ID."""
        result = await self.db.execute(
            select(Note).where(
                Note.id == note_id,
                Note.tenant_id == self.tenant_id,
            )
        )
        note = result.scalar_one_or_none()
        
        if not note:
            return None
        
        # Check access
        if user_role == "employee" and note.created_by_id != user_id:
            return None
        
        return note
    
    async def create_note(
        self,
        note_data: Dict[str, Any],
        created_by_id: str,
    ) -> Note:
        """Create a new note."""
        note = Note(
            tenant_id=self.tenant_id,
            title=note_data.get("title"),
            content=note_data.get("content"),
            meeting_context=note_data.get("meeting_context"),
            source_type=note_data.get("source_type", "manual"),
            created_by_id=created_by_id,
        )
        
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)

        return note

    async def update_note(
        self,
        note_id: str,
        note_data: Dict[str, Any],
        user_id: str,
        user_role: str,
    ) -> Optional[Note]:
        """Update an existing note."""
        result = await self.db.execute(
            select(Note).where(
                Note.id == note_id,
                Note.tenant_id == self.tenant_id,
            )
        )
        note = result.scalar_one_or_none()
        
        if not note:
            return None
        
        # Check access
        if user_role == "employee" and note.created_by_id != user_id:
            return None
        
        # Update fields
        if "title" in note_data:
            note.title = note_data["title"]
        if "content" in note_data:
            note.content = note_data["content"]
        if "meeting_context" in note_data:
            note.meeting_context = note_data["meeting_context"]

        await self.db.commit()
        await self.db.refresh(note)

        return note

    async def delete_note(
        self,
        note_id: str,
        user_id: str,
        user_role: str,
    ) -> bool:
        """Delete a note."""
        result = await self.db.execute(
            select(Note).where(
                Note.id == note_id,
                Note.tenant_id == self.tenant_id,
            )
        )
        note = result.scalar_one_or_none()
        
        if not note:
            return False
        
        # Check access
        if user_role == "employee" and note.created_by_id != user_id:
            return False
        
        note.deleted_at = datetime.utcnow()
        note.is_deleted = "Y"
        
        await self.db.commit()
        return True
    
    async def summarize_note(
        self,
        note_id: str,
    ) -> Dict[str, Any]:
        """Generate AI summary and action items for a note."""
        from app.services.ai_service import AIService
        
        ai_service = AIService(self.db, self.tenant_id)
        
        note = await self.get_note(note_id, "", "admin")
        if not note:
            raise ValueError("Note not found")
        
        result = await ai_service.summarize_content(note.content)
        
        # Update note with AI results
        note.ai_summary = result["summary"]
        note.ai_action_items = json.dumps(result["action_items"])
        note.ai_key_topics = json.dumps(result["key_topics"])
        note.ai_sentiment = result["sentiment"]

        await self.db.commit()

        return result
    
    async def qa_on_note(
        self,
        note_id: str,
        question: str,
    ) -> Dict[str, Any]:
        """Answer a question about a note using RAG."""
        from app.services.ai_service import AIService
        
        ai_service = AIService(self.db, self.tenant_id)
        
        note = await self.get_note(note_id, "", "admin")
        if not note:
            raise ValueError("Note not found")
        
        result = await ai_service.rag_query(
            query=question,
            documents=[note.content],
        )
        
        return result
    
    async def create_rag_document(
        self,
        title: str,
        content: str,
        document_type: str,
        created_by_id: str,
    ) -> Note:
        """Create a document for RAG Q&A."""
        note = Note(
            tenant_id=self.tenant_id,
            title=title,
            content=content,
            is_rag_document="Y",
            document_type=document_type,
            source_type="policy_document",
            created_by_id=created_by_id,
        )
        
        self.db.add(note)
        await self.db.commit()

        # Index in vector store (stub)
        from app.services.ai_service import AIService
        ai_service = AIService(self.db, self.tenant_id)
        await ai_service.index_document(str(note.id), content)
        
        await self.db.refresh(note)
        
        return note
