from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models_db.restaurant import Restaurant


def get_restaurant_by_name(session: Session, name: str) -> Restaurant | None:
    stmt = select(Restaurant).where(Restaurant.name.ilike(name))
    return session.execute(stmt).scalars().first()


def upsert_restaurant(session: Session, data: dict) -> Restaurant:
    existing = get_restaurant_by_name(session, data["name"])
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    restaurant = Restaurant(**data)
    session.add(restaurant)
    session.commit()
    session.refresh(restaurant)
    return restaurant