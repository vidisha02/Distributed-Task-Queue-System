import redis.asyncio
import json
import asyncio
from rq import Queue, Retry
from datetime import timedelta
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
    Header,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import crud
import models
import schemas
from database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- Redis Pub/Sub Listener ---
async def redis_listener(manager: ConnectionManager):
    r = redis.asyncio.Redis(host="redis-service", port=6379, auto_close_connection_pool=False)
    pubsub = r.pubsub()
    await pubsub.subscribe("task_updates")
    print("Subscribed to 'task_updates' channel.")
    while True:
        try:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("data"):
                await manager.broadcast(message['data'].decode('utf-8'))
        except asyncio.CancelledError:
            print("Listener task cancelled.")
            break
        except Exception as e:
            print(f"Error in Redis listener: {e}")
            await asyncio.sleep(1)
    await pubsub.close()


# --- FastAPI Lifespan Events (UPDATED) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This block runs on startup
    print("Application startup: Starting Redis listener...")
    listener_task = asyncio.create_task(redis_listener(manager))
    
    yield # The application is now running
    
    # This block runs on shutdown
    print("Application shutdown: Stopping Redis listener...")
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        print("Listener task successfully shut down.")

# --- App Initialization (UPDATED) ---
app = FastAPI(
    title="Orchestra API Producer",
    lifespan=lifespan # Use the new lifespan context manager
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Redis and RQ Connection ---
redis_conn = redis.Redis(host="redis-service", port=6379)

# Queues for I/O-bound tasks with priorities
high_prio_q = Queue('high', connection=redis_conn)
medium_prio_q = Queue('medium', connection=redis_conn)
low_prio_q = Queue('low', connection=redis_conn)

# Queue for CPU-bound tasks
cpu_bound_q = Queue('cpu_bound', connection=redis_conn)

# --- Dependency for Database Session ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API Endpoints ---

@app.post("/v1/tasks", response_model=schemas.Task, status_code=status.HTTP_202_ACCEPTED)
async def create_task_endpoint(
    task: schemas.TaskCreate,
    idempotency_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if idempotency_key:
        existing_task = crud.get_task_by_idempotency_key(db, key=idempotency_key)
        if existing_task:
            return existing_task

    try:
        db_task = crud.create_task(db=db, task=task, idempotency_key=idempotency_key)
    except IntegrityError:
        db.rollback()
        existing_task = crud.get_task_by_idempotency_key(db, key=idempotency_key)
        if not existing_task:
            raise HTTPException(status_code=500, detail="Failed to create or retrieve task.")
        return existing_task

    # Define retry policy
    retry_policy = Retry(max=3, interval=[1, 2, 3])

    # Select queue and task function based on task_type
    if task.task_type == 'cpu_bound':
        queue = cpu_bound_q
        task_function = "worker.process_cpu_bound_task"
    else: # Default to io_bound
        if task.priority == 'high':
            queue = high_prio_q
        elif task.priority == 'low':
            queue = low_prio_q
        else:
            queue = medium_prio_q
        task_function = "worker.process_io_bound_task"

    # Enqueue the job
    job_args = (db_task.id,)
    if task.delay > 0:
        queue.enqueue_in(
            timedelta(seconds=task.delay),
            task_function,
            *job_args,
            retry=retry_policy,
            on_failure="worker.custom_failure_handler"
        )
    else:
        queue.enqueue(
            task_function,
            *job_args,
            retry=retry_policy,
            on_failure="worker.custom_failure_handler"
        )

    # Use model_validate for Pydantic v2 instead of from_orm
    task_dict = schemas.Task.model_validate(db_task).model_dump()
    await manager.broadcast(json.dumps(task_dict, default=str))
    return db_task

@app.get("/v1/tasks", response_model=List[schemas.Task])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_tasks(db, skip=skip, limit=limit)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)