import os
from urllib.parse import urlparse
from pydantic import BaseModel


class Settings(BaseModel):
    postgres_url: str = os.getenv("POSTGRES_URL", "")
    redis_cache_url: str = os.getenv("REDIS_CACHE_URL", "redis://localhost:6379/2")
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    menu_embedding_dim: int = int(os.getenv("MENU_EMBEDDING_DIM", "768"))

    def postgres_hostname(self) -> str | None:
        raw = (self.postgres_url or "").strip()
        if not raw:
            return None

        try:
            parsed = urlparse(raw)
            return parsed.hostname
        except Exception:
            return None

    def postgres_url_is_usable(self) -> bool:
        raw = (self.postgres_url or "").strip()
        if not raw:
            return False

        try:
            parsed = urlparse(raw)
        except Exception:
            return False

        if parsed.scheme not in {"postgresql", "postgres"}:
            return False

        host = parsed.hostname or ""
        if not host or ".." in host:
            return False

        # Supabase Postgres host must be: db.<project-ref>.supabase.co
        if host.startswith("db.") and host.endswith(".supabase.co"):
            parts = host.split(".")
            if len(parts) < 4 or not parts[1]:
                return False

        return True


settings = Settings()
