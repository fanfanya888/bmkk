from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import get_sync_session
from app.models import EvalResult
from app.services.evaluation_service import get_question_or_raise, resolve_answer_image_paths
from app.services.judge_service import judge_model_response
from app.services.model_service import get_model_detail


def format_duration(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    minutes, secs = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}h{minutes:02d}m{secs:02d}s"
    if minutes:
        return f"{minutes:d}m{secs:02d}s"
    return f"{secs:d}s"


def render_progress_bar(completed: int, total: int, *, width: int = 24) -> str:
    if total <= 0:
        return "[" + ("-" * width) + "]"
    filled = int(width * completed / total)
    if completed > 0 and filled == 0:
        filled = 1
    filled = min(filled, width)
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Judge existing model responses without re-calling the evaluated model."
    )
    parser.add_argument("--model-id", type=int, required=True)
    parser.add_argument("--attempt", type=int, choices=[1, 2, 3], default=1)
    parser.add_argument("--question-id", action="append", type=int, dest="question_ids")
    parser.add_argument("--question-id-start", type=int)
    parser.add_argument("--question-id-end", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def build_query(args: argparse.Namespace):
    attempt_response_text = getattr(EvalResult, f"attempt_{args.attempt}_response_text")
    attempt_result = getattr(EvalResult, f"attempt_{args.attempt}_result")

    stmt = select(EvalResult.eval_result_id).where(
        EvalResult.model_id == args.model_id,
        attempt_response_text.is_not(None),
    )
    if args.question_ids:
        stmt = stmt.where(EvalResult.question_id.in_(args.question_ids))
    if args.question_id_start is not None:
        stmt = stmt.where(EvalResult.question_id >= args.question_id_start)
    if args.question_id_end is not None:
        stmt = stmt.where(EvalResult.question_id <= args.question_id_end)
    if not args.force:
        stmt = stmt.where(attempt_result.is_(None))
    stmt = stmt.order_by(EvalResult.question_id.asc())
    if args.limit is not None:
        stmt = stmt.limit(args.limit)
    return stmt


def main() -> None:
    args = parse_args()

    with get_sync_session() as session:
        model = get_model_detail(session, args.model_id)
        eval_result_ids = list(session.scalars(build_query(args)).all())

        print(f"model_id={model.model_id}")
        print(f"model_name={model.model_name}")
        print(f"attempt={args.attempt}")
        print(f"selected_rows={len(eval_result_ids)}")

        if not eval_result_ids:
            print("No rows selected.")
            return

        started_at = perf_counter()
        counters: Counter[str] = Counter()

        for index, eval_result_id in enumerate(eval_result_ids, start=1):
            item_started_at = perf_counter()
            row = session.get(EvalResult, eval_result_id)
            assert row is not None

            response_text = getattr(row, f"attempt_{args.attempt}_response_text")
            question = get_question_or_raise(session, row.question_id)

            print(f"--> [{index}/{len(eval_result_ids)}] judging eval_result_id={eval_result_id}")

            try:
                decision = judge_model_response(
                    model_response_text=response_text or "",
                    standard_answer_text=question.answer_text,
                    answer_image_paths=resolve_answer_image_paths(question),
                )
                setattr(row, f"attempt_{args.attempt}_result", decision.result)
                setattr(row, f"attempt_{args.attempt}_judge_feedback", decision.feedback)
                setattr(row, f"attempt_{args.attempt}_error", None)
                status = "correct" if decision.result == 1 else "incorrect"
            except Exception as exc:
                setattr(row, f"attempt_{args.attempt}_result", None)
                setattr(row, f"attempt_{args.attempt}_judge_feedback", None)
                setattr(row, f"attempt_{args.attempt}_error", str(exc))
                status = "error"

            setattr(row, f"attempt_{args.attempt}_finished_at", datetime.now(UTC))
            session.commit()

            counters[status] += 1
            item_elapsed = perf_counter() - item_started_at
            total_elapsed = perf_counter() - started_at
            average_seconds = total_elapsed / index
            eta_seconds = average_seconds * (len(eval_result_ids) - index)
            print(
                f"<-- [{index}/{len(eval_result_ids)}] eval_result_id={eval_result_id} "
                f"status={status} item_elapsed={item_elapsed:.2f}s"
            )
            print(
                f"    progress={render_progress_bar(index, len(eval_result_ids))} "
                f"{index}/{len(eval_result_ids)} "
                f"elapsed={format_duration(total_elapsed)} "
                f"avg={average_seconds:.2f}s/row "
                f"eta={format_duration(eta_seconds)}"
            )

        elapsed = perf_counter() - started_at
        print("Summary")
        print(f"  total={len(eval_result_ids)}")
        print(f"  correct={counters['correct']}")
        print(f"  incorrect={counters['incorrect']}")
        print(f"  error={counters['error']}")
        print(f"  elapsed_seconds={elapsed:.2f}")


if __name__ == "__main__":
    main()
