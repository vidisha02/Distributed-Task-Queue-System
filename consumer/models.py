from sqlalchemy import Column, Integer, String, DateTime, Text, UniqueConstraint
from sqlalchemy.sql import func
from database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    idempotency_key = Column(String, unique=True, index=True, nullable=True)
    task_type = Column(String, default='io_bound', index=True)
    status = Column(String, default='pending', index=True)
    priority = Column(String, default='medium', index=True)
    payload = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint('idempotency_key', name='uq_idempotency_key'),)