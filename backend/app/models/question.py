from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Question(Base):
    __tablename__ = "questions"

    question_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    content_text: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    content_images: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    answer_images: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    analysis_text: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    analysis_images: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    subject: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    stage: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    grade: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    textbook_chapter: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("''"),
    )
    knowledge_level_1: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("''"),
    )
    knowledge_level_2: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("''"),
    )
    knowledge_level_3: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("''"),
    )
    question_type: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    difficulty: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    cognitive_level: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    solving_methods: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    common_pitfalls: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    source_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_region: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    has_image: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    has_latex: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    quality_score: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    eval_results: Mapped[list["EvalResult"]] = relationship(back_populates="question")
