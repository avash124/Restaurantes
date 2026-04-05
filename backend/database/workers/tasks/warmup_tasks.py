"""
Celery task: pre-warm the menu cache for hot chain restaurants.

Scheduled via Celery Beat (configured in celery_app.py) to run every 6 hours
so menus are always fresh in Redis before users start searching.
"""

import asyncio
import logging

from backend.database.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="warmup.warm_hot_chains", bind=True, max_retries=1)
def warm_hot_chains_task(self):
    """
    Run the async warm_hot_chains() function inside a fresh event loop.
    This is a Celery task so it runs in a worker process.
    """
    from backend.browser_use.services.warmup_service import warm_hot_chains

    results: dict[str, bool] = asyncio.run(warm_hot_chains())

    succeeded = sum(1 for ok in results.values() if ok)
    failed = len(results) - succeeded
    logger.info("[warmup_task] done — %d succeeded, %d failed", succeeded, failed)

    return {"succeeded": succeeded, "failed": failed, "details": results}
