from __future__ import annotations

from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EvalModel(Base):
    __tablename__ = "eval_models"

    model_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    api_url: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    api_style: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'chat_completions'"),
    )
    api_model: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    api_key: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    eval_results: Mapped[list["EvalResult"]] = relationship(back_populates="model")
