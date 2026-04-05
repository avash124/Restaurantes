from backend.database.workers.celery_app import celery_app
from backend.browser_use.agents.deep_analysis_agent import run_deep_restaurant_agent
from backend.database.cache.job_progress import set_job_progress
import asyncio


@celery_app.task(bind=True)
def deep_analyze_restaurant_task(
    self,
    restaurant_name: str,
    website_url: str | None = None,
    location_hint: str | None = None,
):
    async def _run():
        output = await run_deep_restaurant_agent(
            restaurant_name=restaurant_name,
            website_url=website_url,
            location_hint=location_hint,
        )

        # Save structured output to Supabase here
        # Cache restaurant snapshot in Redis here

        await set_job_progress(
            self.request.id,
            {
                "status": "completed",
                "restaurant_name": output.restaurant_name,
                "menu_items_found": len(output.menu_items),
            },
        )
        return output

    output = asyncio.run(_run())

    return {
        "restaurant_name": output.restaurant_name,
        "menu_items_found": len(output.menu_items),
    }