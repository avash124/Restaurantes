from backend.database.cache.redis_client import get_json, set_json, delete_key
from backend.database.cache.cache_keys import job_progress_key

JOB_PROGRESS_TTL_SECONDS = 60 * 60  # 1 hour


async def set_job_progress(job_id: str, payload: dict):
    """
    Example payload:
    {
        "status": "running",
        "restaurants_discovered": 42,
        "restaurants_deep_analyzed": 11,
        "message": "Wide browsing feeding deep browsing"
    }
    """
    await set_json(job_progress_key(job_id), payload, JOB_PROGRESS_TTL_SECONDS)


async def get_job_progress(job_id: str):
    return await get_json(job_progress_key(job_id))


async def clear_job_progress(job_id: str):
    await delete_key(job_progress_key(job_id))