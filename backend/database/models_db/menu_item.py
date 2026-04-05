import uuid
from datetime import datetime

from sqlalchemy import Text, Float, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.db.base import Base


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2))

    evidence_source_type: Mapped[str] = mapped_column(Text, default="restaurant_explicit")
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class MenuItemFacts(Base):
    __tablename__ = "menu_item_facts"

    menu_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("menu_items.id", ondelete="CASCADE"),
        primary_key=True,
    )

    ingredients_explicit: Mapped[list] = mapped_column(JSONB, default=list)
    ingredients_inferred: Mapped[list] = mapped_column(JSONB, default=list)
    allergens_explicit: Mapped[list] = mapped_column(JSONB, default=list)
    preparation_tags: Mapped[list] = mapped_column(JSONB, default=list)
    uncertainty_flags: Mapped[list] = mapped_column(JSONB, default=list)
    nutrition_explicit: Mapped[dict] = mapped_column(JSONB, default=dict)

    last_extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)