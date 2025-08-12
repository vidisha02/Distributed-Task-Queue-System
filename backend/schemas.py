from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Optional
import uuid

# Shared properties for a task
class TaskBase(BaseModel):
    payload: Optional[str] = None

# Properties to receive via API on creation
class TaskCreate(TaskBase):
    task_type: Literal['io_bound', 'cpu_bound'] = 'io_bound'
    priority: Literal['high', 'medium', 'low'] = 'medium'
    delay: int = Field(default=0, ge=0, description="Delay in seconds")

# Properties to return to client
class Task(TaskBase):
    id: int
    idempotency_key: Optional[str] = None
    task_type: str
    status: str
    priority: str
    retry_count: int
    created_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True