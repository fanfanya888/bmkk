from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EvalResult(Base):
    __tablename__ = "eval_results"

    eval_result_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("questions.question_id", ondelete="CASCADE"),
        nullable=False,
    )
    model_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("eval_models.model_id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_1_result: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    attempt_2_result: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    attempt_3_result: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    attempt_1_response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_1_judge_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_1_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_1_finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    attempt_1_result_override: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    attempt_1_result_overridden_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    attempt_2_response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_2_judge_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_2_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_2_finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    attempt_2_result_override: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    attempt_2_result_overridden_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    attempt_3_response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_3_judge_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_3_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_3_finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    attempt_3_result_override: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    attempt_3_result_overridden_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    question: Mapped["Question"] = relationship(back_populates="eval_results")
    model: Mapped["EvalModel"] = relationship(back_populates="eval_results")
