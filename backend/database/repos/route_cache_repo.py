from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from backend.database.models_db.route_cache import RouteCache


def get_valid_route_cache(
    session: Session,
    origin_hash: str,
    restaurant_id,
    travel_mode: str,
):
    stmt = (
        select(RouteCache)
        .where(RouteCache.origin_hash == origin_hash)
        .where(RouteCache.restaurant_id == restaurant_id)
        .where(RouteCache.travel_mode == travel_mode)
        .where(RouteCache.expires_at > datetime.utcnow())
    )
    return session.execute(stmt).scalars().first()


def save_route_cache(
    session: Session,
    origin_hash: str,
    restaurant_id,
    travel_mode: str,
    distance_meters: int | None,
    duration_seconds: int | None,
    expires_at,
) -> RouteCache:
    row = RouteCache(
        origin_hash=origin_hash,
        restaurant_id=restaurant_id,
        travel_mode=travel_mode,
        distance_meters=distance_meters,
        duration_seconds=duration_seconds,
        expires_at=expires_at,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_expired_routes(session: Session) -> int:
    stmt = (
        delete(RouteCache)
        .where(RouteCache.expires_at <= datetime.utcnow())
        .execution_options(synchronize_session="fetch")
    )
    result = session.execute(stmt)
    session.commit()
    return result.rowcount