from backend.database.workers.celery_app import celery_app
from backend.database.db.session import SessionLocal
from backend.database.repos.restaurant_repo import upsert_restaurant
from backend.database.models_db.discovery import DiscoveryRun, DiscoveryRunRestaurant


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def discover_restaurants_in_radius_task(_task, center_lat: float, center_lng: float, radius_miles: float, category: str | None = None):
    session = SessionLocal()
    try:
        run = DiscoveryRun(
            center_lat=center_lat,
            center_lng=center_lng,
            radius_miles=radius_miles,
            category=category,
            status="running",
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        discovered = []

        for idx, restaurant_data in enumerate(discovered, start=1):
            restaurant = upsert_restaurant(session, restaurant_data)
            session.add(
                DiscoveryRunRestaurant(
                    discovery_run_id=run.id,
                    restaurant_id=restaurant.id,
                    discovered_rank=idx,
                    source_url=restaurant_data.get("website_url"),
                )
            )

        run.status = "completed"
        session.add(run)
        session.commit()

        return {"discovery_run_id": str(run.id), "restaurants_found": len(discovered)}
    finally:
        session.close()