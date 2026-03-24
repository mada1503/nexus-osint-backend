"""
Search API Routes — /api/search
"""
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.models.models import SearchType
from app.workers.tasks import run_full_investigation

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    search_type: str  # pseudo | email | name | domain


class SearchResponse(BaseModel):
    job_id: str
    task_id: str
    status: str
    message: str


@router.post("/", response_model=SearchResponse)
async def launch_search(request: SearchRequest):
    """
    Launch a new OSINT investigation.
    Dispatches a Celery task and returns immediately with a job_id.
    """
    job_id = str(uuid.uuid4())
    logger.info(f"New search job [{job_id}]: '{request.query}' ({request.search_type})")

    # Validate search type
    try:
        SearchType(request.search_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid search_type: '{request.search_type}'. Must be one of: pseudo, email, name, domain",
        )

    # Dispatch Celery Task
    task = run_full_investigation.delay(job_id, request.query, request.search_type)

    logger.info(f"Celery task dispatched: {task.id}")

    return SearchResponse(
        job_id=job_id,
        task_id=task.id,
        status="pending",
        message=f"Investigation lancée. Task ID: {task.id}",
    )


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Poll for task status and results."""
    from app.workers.celery_app import celery_app as app
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=app)

    if result.state == "PENDING":
        return {"status": "pending", "progress": None}
    elif result.state == "PROGRESS":
        return {"status": "running", "progress": result.info}
    elif result.state == "SUCCESS":
        return {"status": "completed", "data": result.result}
    elif result.state == "FAILURE":
        return {"status": "failed", "error": str(result.info)}

    return {"status": result.state.lower()}


from fastapi import WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
import asyncio

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Connect to Redis async
    r = await aioredis.from_url("redis://redis:6379/0", encoding="utf-8", decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe("sentinel_logs")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
    finally:
        await pubsub.unsubscribe("sentinel_logs")
        await r.close()
