import uuid
from datetime import datetime

from sqlalchemy import Text, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.db.base import Base


class ConditionEvaluation(Base):
    __tablename__ = "condition_evaluations"
    __table_args__ = (
        UniqueConstraint("menu_item_id", "condition_id", name="uq_menu_item_condition"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("menu_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    condition_id: Mapped[str] = mapped_column(Text, nullable=False)

    label: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    reasons: Mapped[list] = mapped_column(JSONB, default=list)
    missing_info: Mapped[list] = mapped_column(JSONB, default=list)
    matched_rules: Mapped[list] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)