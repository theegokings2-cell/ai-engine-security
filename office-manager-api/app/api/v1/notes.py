"""
Notes API endpoints with AI summarization and Q&A.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.tenant import get_tenant_from_request
from app.core.security import get_current_user
from app.core.audit import AuditLogger
from app.models.user import User
from app.models.note import (
    Note,
    NoteCreate,
    NoteUpdate,
    NoteResponse,
    SummarizeResponse,
    QAResponse,
)
from app.services.notes_service import NotesService

router = APIRouter()


@router.get("", response_model=List[NoteResponse])
async def list_notes(
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    include_rag_docs: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List notes for the current tenant.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = NotesService(db, tenant_id)
    notes = await service.list_notes(
        limit=limit,
        offset=offset,
        include_rag_docs=include_rag_docs,
        user_id=str(user.id) if user.role == "employee" else None,
    )
    
    return notes


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific note by ID.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = NotesService(db, tenant_id)
    note = await service.get_note(note_id, str(user.id), user.role)
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    
    return note


@router.post("", response_model=NoteResponse)
async def create_note(
    note_data: NoteCreate,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new note.
    """
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    service = NotesService(db, tenant_id)
    note = await service.create_note(
        note_data=note_data.model_dump(),
        created_by_id=str(user.id),
    )
    
    # Log audit
    logger = AuditLogger(db, str(user.id), request)
    await logger.create(
        resource_type="note",
        resource_id=str(note.id),
        new_values=note.to_dict(),
    )
    
    return note


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    note_data: NoteUpdate,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing note.
    """
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    service = NotesService(db, tenant_id)
    
    # Get old values for audit
    old_note = await service.get_note(note_id, str(user.id), user.role)
    if not old_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    
    old_values = old_note.to_dict()
    
    note = await service.update_note(
        note_id=note_id,
        note_data=note_data.model_dump(exclude_unset=True),
        user_id=str(user.id),
        user_role=user.role,
    )
    
    # Log audit
    logger = AuditLogger(db, str(user.id), request)
    await logger.update(
        resource_type="note",
        resource_id=note_id,
        old_values=old_values,
        new_values=note.to_dict(),
    )
    
    return note


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a note.
    """
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    service = NotesService(db, tenant_id)
    
    # Get old values for audit
    old_note = await service.get_note(note_id, str(user.id), user.role)
    if not old_note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    
    await service.delete_note(note_id, str(user.id), user.role)
    
    # Log audit
    logger = AuditLogger(db, str(user.id), request)
    await logger.delete(
        resource_type="note",
        resource_id=note_id,
        old_values=old_note.to_dict(),
    )
    
    return {"message": "Note deleted successfully"}


@router.post("/{note_id}/summarize", response_model=SummarizeResponse)
async def summarize_note(
    note_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate AI summary and action items for a note.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = NotesService(db, tenant_id)
    
    note = await service.get_note(note_id, str(user.id), user.role)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    
    result = await service.summarize_note(note_id)
    
    return SummarizeResponse(
        id=note_id,
        summary=result["summary"],
        action_items=result["action_items"],
        key_topics=result["key_topics"],
        sentiment=result["sentiment"],
    )


@router.post("/{note_id}/qa", response_model=QAResponse)
async def ask_question(
    note_id: str,
    question: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Ask a question about a note (RAG Q&A).
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = NotesService(db, tenant_id)
    
    note = await service.get_note(note_id, str(user.id), user.role)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    
    result = await service.qa_on_note(note_id, question)
    
    return QAResponse(
        answer=result["answer"],
        sources=result["sources"],
    )


@router.post("/upload-rag")
async def upload_rag_document(
    title: str,
    content: str,
    document_type: str = "policy",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document for RAG Q&A.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = NotesService(db, tenant_id)
    note = await service.create_rag_document(
        title=title,
        content=content,
        document_type=document_type,
        created_by_id=str(user.id),
    )
    
    return {"message": "Document uploaded for RAG", "note_id": str(note.id)}
