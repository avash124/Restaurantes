from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")  # backend/.env

import asyncio
import logging

from celery import Celery
from celery.signals import worker_shutdown
from backend.database.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "dietary_app",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

from celery.schedules import crontab

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Los_Angeles",
    enable_utc=True,
    task_track_started=True,
    # Pre-warm hot chain menus every 6 hours so cache is always warm.
    beat_schedule={
        "warmup-hot-chains-every-6h": {
            "task": "warmup.warm_hot_chains",
            "schedule": crontab(minute=0, hour="*/6"),
        },
    },
)


@worker_shutdown.connect
def _stop_browser_sessions_on_worker_shutdown(**kwargs):
    """Stop any in-flight browser-use sessions when a Celery worker exits."""
    from backend.browser_use import session_registry
    from backend.browser_use.agents.browser_use_client import get_browseruse_client

    ids = session_registry.active_session_ids()
    if not ids:
        return

    logger.info("[celery-shutdown] stopping %d browser-use session(s)…", len(ids))
    try:
        client = get_browseruse_client()
        asyncio.run(session_registry.stop_all_sessions(client.sessions))
    except Exception as exc:
        logger.warning("[celery-shutdown] error stopping browser-use sessions: %s", exc)