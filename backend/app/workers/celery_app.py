"""
Celery Application for NexusSearch.
All tasks are run asynchronously in background workers.
"""
from celery import Celery
from app.config import settings

# Initialize Celery
celery_app = Celery(
    "nexussearch",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Paris",
    task_track_started=True,
    task_acks_late=True,
)
