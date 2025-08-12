import os
import time
import json
from datetime import datetime, timedelta
import random
import sys
from redis import Redis
from sqlalchemy.orm import Session

from rq import Worker, Queue, get_current_job
from rq.job import Job

import database
import models
import schemas

# --- Redis Connection ---
redis_url = os.getenv('REDIS_URL', 'redis://redis-service:6379')
redis_conn = Redis.from_url(redis_url)
PUBSUB_CHANNEL = "task_updates"

# --- Rate Limiter ---
class RateLimiter:
    def __init__(self, client: Redis, limit: int, period: int):
        self.client = client
        self.limit = limit
        self.period = period

    def is_allowed(self, key: str) -> bool:
        key = f"rate_limit:{key}"
        count = self.client.incr(key)
        if count == 1:
            self.client.expire(key, self.period)
        return count <= self.limit

api_rate_limiter = RateLimiter(redis_conn, limit=10, period=60)

# --- Utility Functions ---
def publish_update(task_id: int, db: Session):
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task:
        task_schema = schemas.Task.model_validate(task)
        message = {
            "event": "task_update",
            "data": task_schema.model_dump(mode='json')
        }
        redis_conn.publish(PUBSUB_CHANNEL, json.dumps(message))

def custom_failure_handler(job: Job, connection, type, value, traceback):
    db = database.SessionLocal()
    try:
        task_id = job.args[0]
        task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if task:
            task.status = 'failed'
            task.error_message = str(value)
            task.retry_count = job.meta.get('retry_count', 1)
            task.finished_at = datetime.utcnow()
            db.commit()
            publish_update(task_id, db)
    finally:
        db.close()

# --- Task Processing Logic ---
def _process_task_logic(task_id: int, task_type: str, duration: int, can_fail: bool):
    db = database.SessionLocal()
    task = None
    try:
        task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if not task:
            print(f"Task {task_id} not found. Skipping.")
            return

        print(f"Processing {task_type} task {task_id}...")
        task.status = 'running'

        current_job = get_current_job(connection=redis_conn)
        if current_job:
            retry_count = current_job.meta.get('retry_count', 0)
            task.retry_count = retry_count
            current_job.meta['retry_count'] = retry_count + 1
            current_job.save_meta()

        db.commit()
        publish_update(task_id, db)

        if can_fail and random.random() < 0.3:
            raise ConnectionError("Simulated network failure")

        time.sleep(duration)

        task.status = 'completed'
        task.error_message = None
        task.finished_at = datetime.utcnow()
        db.commit()
        print(f"Task {task_id} completed.")
        publish_update(task_id, db)

    except Exception as e:
        print(f"Task {task_id} failed: {e}")
        raise e  # Let RQ handle retries and failure callback

    finally:
        db.close()

def process_io_bound_task(task_id: int):
    current_job = get_current_job(connection=redis_conn)
    if not current_job:
        print(f"Could not retrieve current job for task {task_id}. Skipping.")
        return

    if "api_call" in (current_job.description or ""):
        if not api_rate_limiter.is_allowed("external_api"):
            print(f"Rate limit hit for task {task_id}. Requeuing.")
            queue = Queue(current_job.origin, connection=redis_conn)
            queue.enqueue_in(
                timedelta(seconds=15),
                current_job.func_name,
                *current_job.args
            )
            return

    _process_task_logic(task_id, "I/O-bound", duration=5, can_fail=True)

def process_cpu_bound_task(task_id: int):
    _process_task_logic(task_id, "CPU-bound", duration=15, can_fail=False)

# --- Main Worker ---
if __name__ == '__main__':
    queues_to_listen = sys.argv[1:] if len(sys.argv) > 1 else ['high', 'medium', 'low', 'cpu_bound']
    queues = [Queue(name, connection=redis_conn) for name in queues_to_listen]
    print(f"Starting worker for queues: {', '.join(queues_to_listen)}")
    worker = Worker(queues, connection=redis_conn)
    worker.work(with_scheduler=True)
