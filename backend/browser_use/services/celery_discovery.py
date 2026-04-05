from backend.database.workers.celery_app import celery_app
from backend.browser_use.agents.wide_browsing_agent import run_wide_discovery_agent
from backend.database.cache.job_progress import set_job_progress
from backend.database.workers.tasks.deep_tasks import deep_analyze_restaurant_task
import asyncio


@celery_app.task(bind=True)
def discover_restaurants_in_radius_task(self, location: str, radius_miles: float, category: str):
    output = asyncio.run(run_wide_discovery_agent(location, radius_miles, category))
    restaurants = output.restaurants

    for restaurant in restaurants:
        deep_analyze_restaurant_task.delay(
            restaurant_name=restaurant.name,
            website_url=restaurant.website_url,
            location_hint=location,
        )

    asyncio.run(
        set_job_progress(
            self.request.id,
            {
                "status": "running",
                "restaurants_discovered": len(restaurants),
                "restaurants_deep_analyzed": 0,
                "message": "Wide browsing complete; deep browsing queued",
            },
        )
    )

    return {"restaurants_found": len(restaurants)}