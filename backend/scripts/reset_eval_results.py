from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import get_sync_session
from app.models import EvalResult


ATTEMPT_FIELD_SUFFIXES = [
    "result",
    "response_text",
    "judge_feedback",
    "error",
    "finished_at",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clear stored evaluation attempt data from eval_results."
    )
    parser.add_argument(
        "--eval-result-id",
        action="append",
        type=int,
        dest="eval_result_ids",
        help="Target eval_result_id. Can be repeated.",
    )
    parser.add_argument(
        "--question-id",
        action="append",
        type=int,
        dest="question_ids",
        help="Target question_id. Must be used together with --model-id. Can be repeated.",
    )
    parser.add_argument(
        "--model-id",
        type=int,
        help="Target model_id when selecting by question_id.",
    )
    parser.add_argument(
        "--attempt",
        type=int,
        choices=[1, 2, 3],
        help="Only clear one attempt. If omitted, clear all attempts.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview affected rows without modifying the database.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    has_eval_result_ids = bool(args.eval_result_ids)
    has_question_selection = bool(args.question_ids or args.model_id)

    if not has_eval_result_ids and not has_question_selection:
        raise ValueError("Provide --eval-result-id or --question-id with --model-id.")

    if args.question_ids and not args.model_id:
        raise ValueError("--question-id must be used together with --model-id.")

    if args.model_id and not args.question_ids:
        raise ValueError("--model-id must be used together with at least one --question-id.")


def build_query(args: argparse.Namespace):
    stmt = select(EvalResult).order_by(EvalResult.eval_result_id.asc())

    filters = []
    if args.eval_result_ids:
        filters.append(EvalResult.eval_result_id.in_(args.eval_result_ids))
    if args.question_ids and args.model_id:
        filters.append(EvalResult.question_id.in_(args.question_ids))
        filters.append(EvalResult.model_id == args.model_id)

    if filters:
        stmt = stmt.where(*filters)

    return stmt


def iter_attempts(target_attempt: int | None) -> list[int]:
    if target_attempt is not None:
        return [target_attempt]
    return [1, 2, 3]


def clear_row_attempts(row: EvalResult, *, target_attempt: int | None) -> None:
    for attempt in iter_attempts(target_attempt):
        for suffix in ATTEMPT_FIELD_SUFFIXES:
            setattr(row, f"attempt_{attempt}_{suffix}", None)


def main() -> None:
    args = parse_args()
    validate_args(args)

    with get_sync_session() as session:
        rows = list(session.scalars(build_query(args)).all())

        print(f"selected_rows={len(rows)}")
        if not rows:
            print("No rows selected.")
            return

        for row in rows:
            print(
                f"eval_result_id={row.eval_result_id} "
                f"question_id={row.question_id} "
                f"model_id={row.model_id}"
            )

        if args.dry_run:
            print("dry_run=true")
            return

        for row in rows:
            clear_row_attempts(row, target_attempt=args.attempt)
        session.commit()

        print("reset_done=true")
        print(f"attempt_scope={'all' if args.attempt is None else args.attempt}")


if __name__ == "__main__":
    main()
