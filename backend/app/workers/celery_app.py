from celery import Celery
from app.core.config import settings

# Initialize Celery app
celery_app = Celery(
    "cinerec_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Core configurations
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Stop tasks from hanging forever by setting absolute timeouts (30 mins for heavy rendering)
    task_time_limit=1800,
    task_soft_time_limit=1500,
    # Prefetch multiplier of 1 ensures fair distribution of heavy tasks among multiple workers
    worker_prefetch_multiplier=1,
)

# Autodiscover worker tasks
celery_app.autodiscover_tasks(["app.workers"])
