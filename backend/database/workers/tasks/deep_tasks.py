from sqlalchemy import select

from backend.database.workers.celery_app import celery_app
from backend.database.db.session import SessionLocal
from backend.database.models_db.restaurant import Restaurant
from backend.database.repos.menu_repo import create_menu_item


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def deep_analyze_restaurant_task(_task, restaurant_id: str):
    session = SessionLocal()
    try:
        stmt = select(Restaurant).where(Restaurant.id == restaurant_id)
        restaurant = session.execute(stmt).scalars().first()
        if not restaurant:
            return {"status": "not_found", "restaurant_id": restaurant_id}

        # Replace with Browser Use deep-browsing results
        items = []

        for item in items:
            create_menu_item(session, restaurant.id, item)

        restaurant.deep_status = "complete"
        session.add(restaurant)
        session.commit()

        return {"status": "done", "restaurant_id": restaurant_id, "items_created": len(items)}
    finally:
        session.close()