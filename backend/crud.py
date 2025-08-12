from sqlalchemy.orm import Session
import models
import schemas
from typing import Optional

def get_task(db: Session, task_id: int):
    return db.query(models.Task).filter(models.Task.id == task_id).first()

def get_task_by_idempotency_key(db: Session, key: str):
    return db.query(models.Task).filter(models.Task.idempotency_key == key).first()

def get_tasks(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Task).order_by(models.Task.id.desc()).offset(skip).limit(limit).all()

def create_task(db: Session, task: schemas.TaskCreate, idempotency_key: Optional[str] = None):
    db_task = models.Task(
        payload=task.payload,
        priority=task.priority,
        task_type=task.task_type,
        idempotency_key=idempotency_key
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task