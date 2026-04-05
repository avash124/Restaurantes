from sqlalchemy import text
from backend.database.db.database import engine
from backend.database.db.base import Base
from backend.database.models_db.restaurant import Restaurant
from backend.database.models_db.discovery import DiscoveryRun, DiscoveryRunRestaurant
from backend.database.models_db.restaurant_page import RestaurantPage
from backend.database.models_db.menu_item import MenuItem, MenuItemFacts
from backend.database.models_db.evals import ConditionEvaluation
from backend.database.models_db.route_cache import RouteCache
from backend.database.models_db.embeddings import MenuItemEmbedding


def init_db():
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()