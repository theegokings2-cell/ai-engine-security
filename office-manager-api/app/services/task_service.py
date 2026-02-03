"""
Task service with natural language processing and pagination.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus, TaskPriority


# Pagination constants
MAX_LIMIT = 100
DEFAULT_LIMIT = 20
DEFAULT_OFFSET = 0


class TaskService:
    """Service for task management operations."""
    
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    async def list_tasks(
        self,
        status_filter: Optional[TaskStatus] = None,
        assignee_id: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = DEFAULT_OFFSET,
        user_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Task], int]:
        """
        List tasks with optional filters and pagination.
        
        Args:
            status_filter: Filter by task status
            assignee_id: Filter by assigned user
            priority: Filter by priority level
            limit: Maximum number of tasks to return (capped at MAX_LIMIT)
            offset: Number of tasks to skip
            user_id: Current user ID (for access control)
            search: Search query for title/description
        
        Returns:
            Tuple of (tasks list, total count)
        """
        # Enforce limits
        limit = min(max(1, limit), MAX_LIMIT)
        offset = max(0, offset)
        
        # Build query
        conditions = [Task.tenant_id == self.tenant_id]
        
        if status_filter:
            conditions.append(Task.status == status_filter.value)
        if assignee_id:
            conditions.append(Task.assignee_id == assignee_id)
        if priority:
            conditions.append(Task.priority == priority)
        if user_id:
            # Employees see only their assigned tasks
            conditions.append(Task.assignee_id == user_id)
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    Task.title.ilike(search_term),
                    Task.description.ilike(search_term),
                )
            )
        
        # Count query
        count_query = select(func.count(Task.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar() or 0
        
        # Data query
        query = (
            select(Task)
            .where(and_(*conditions))
            .order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        tasks = list(result.scalars().all())
        
        return tasks, total_count
    
    async def get_task(
        self,
        task_id: str,
        user_id: str,
        user_role: str,
    ) -> Optional[Task]:
        """Get a specific task by ID."""
        result = await self.db.execute(
            select(Task).where(
                Task.id == task_id,
                Task.tenant_id == self.tenant_id,
            )
        )
        task = result.scalar_one_or_none()

        if not task:
            return None

        # Check access for employees
        if user_role == "employee" and task.assignee_id != user_id:
            return None
        
        return task
    
    async def create_task(
        self,
        task_data: Dict[str, Any],
        created_by_id: str,
    ) -> Task:
        """Create a new task."""
        task = Task(
            tenant_id=self.tenant_id,
            creator_id=created_by_id,
            title=task_data.get("title"),
            description=task_data.get("description"),
            priority=task_data.get("priority", TaskPriority.MEDIUM.value),
            assignee_id=task_data.get("assignee_id"),
            due_date=task_data.get("due_date"),
            reminder_enabled="Y" if task_data.get("reminder_enabled", True) else "N",
            reminder_channel=task_data.get("reminder_channel", "email"),
        )
        
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        return task

    async def create_from_natural_language(
        self,
        text: str,
        created_by_id: str,
    ) -> Task:
        """
        Create a task from natural language text.
        
        Uses AI to parse:
        - Title/description from text
        - Due date (e.g., "tomorrow at 3pm")
        - Assignee (e.g., "tell John")
        - Priority (urgency keywords)
        """
        from app.services.ai_service import AIService
        
        ai_service = AIService(self.db, self.tenant_id)
        parsed = await ai_service.parse_task_from_text(text)
        
        task = Task(
            tenant_id=self.tenant_id,
            creator_id=created_by_id,
            title=parsed.get("title", text[:100]),
            description=parsed.get("description", text),
            priority=parsed.get("priority", TaskPriority.MEDIUM.value),
            assignee_id=parsed.get("assignee_id"),
            due_date=parsed.get("due_date"),
            nl_source_text=text,
            reminder_enabled="Y",
            reminder_channel="email",
        )
        
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        return task

    async def update_task(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        user_id: str,
        user_role: str,
    ) -> Optional[Task]:
        """Update an existing task."""
        result = await self.db.execute(
            select(Task).where(
                Task.id == task_id,
                Task.tenant_id == self.tenant_id,
            )
        )
        task = result.scalar_one_or_none()

        if not task:
            return None

        # Check access
        if user_role == "employee" and task.assignee_id != user_id:
            return None

        # Update fields
        if "title" in task_data:
            task.title = task_data["title"]
        if "description" in task_data:
            task.description = task_data["description"]
        if "status" in task_data:
            status_val = task_data["status"]
            task.status = status_val.value if hasattr(status_val, "value") else status_val
            if task.status == TaskStatus.COMPLETED.value:
                task.completed_at = datetime.utcnow()
        if "priority" in task_data:
            priority_val = task_data["priority"]
            task.priority = priority_val.value if hasattr(priority_val, "value") else priority_val
        if "assignee_id" in task_data:
            task.assignee_id = task_data["assignee_id"]
        if "due_date" in task_data:
            task.due_date = task_data["due_date"]

        await self.db.commit()
        await self.db.refresh(task)

        return task

    async def complete_task(
        self,
        task_id: str,
        user_id: str,
        user_role: str,
    ) -> Optional[Task]:
        """Mark a task as completed."""
        return await self.update_task(
            task_id=task_id,
            task_data={"status": TaskStatus.COMPLETED},
            user_id=user_id,
            user_role=user_role,
        )
    
    async def delete_task(
        self,
        task_id: str,
        user_id: str,
        user_role: str,
    ) -> bool:
        """Delete a task."""
        result = await self.db.execute(
            select(Task).where(
                Task.id == task_id,
                Task.tenant_id == self.tenant_id,
            )
        )
        task = result.scalar_one_or_none()

        if not task:
            return False

        # Check access
        if user_role == "employee" and task.assignee_id != user_id:
            return False

        await self.db.delete(task)
        await self.db.commit()
        return True
    
    async def get_statistics(
        self,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get task statistics."""
        base_filter = [Task.tenant_id == self.tenant_id]
        if user_id:
            base_filter.append(Task.assignee_id == user_id)
        
        # Count by status
        status_result = await self.db.execute(
            select(Task.status, func.count(Task.id))
            .where(and_(*base_filter))
            .group_by(Task.status)
        )
        status_counts = dict(status_result.all())
        
        # Count by priority
        priority_result = await self.db.execute(
            select(Task.priority, func.count(Task.id))
            .where(and_(*base_filter))
            .group_by(Task.priority)
        )
        priority_counts = dict(priority_result.all())
        
        # Overdue tasks
        overdue_result = await self.db.execute(
            select(func.count(Task.id)).where(
                and_(
                    *base_filter,
                    Task.due_date < datetime.utcnow(),
                    Task.status != TaskStatus.COMPLETED.value,
                )
            )
        )
        overdue_count = overdue_result.scalar() or 0
        
        # Due today
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        due_today_result = await self.db.execute(
            select(func.count(Task.id)).where(
                and_(
                    *base_filter,
                    Task.due_date >= today,
                    Task.due_date < tomorrow,
                )
            )
        )
        due_today_count = due_today_result.scalar() or 0
        
        return {
            "by_status": status_counts,
            "by_priority": priority_counts,
            "overdue": overdue_count,
            "due_today": due_today_count,
            "total": sum(status_counts.values()),
        }
