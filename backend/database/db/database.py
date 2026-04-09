from sqlalchemy import create_engine
from backend.database.core.config import settings

if settings.postgres_url_is_usable():
    engine = create_engine(
        settings.postgres_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
    )
else:
    engine = create_engine("sqlite+pysqlite:///:memory:", echo=False)
