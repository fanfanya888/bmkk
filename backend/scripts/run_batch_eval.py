from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from time import perf_counter

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import get_sync_session
from app.models import EvalResult
from app.schemas.evaluation import EvaluationRunRequest
from app.services.evaluation_service import run_evaluation
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
        description="Run batch evaluations synchronously without Redis/Celery."
    )
    parser.add_argument("--model-id", type=int, required=True, help="Target eval_models.model_id")
    parser.add_argument("--attempt", type=int, choices=[1, 2, 3], default=1)
    parser.add_argument(
        "--question-id",
        action="append",
        type=int,
        dest="question_ids",
        help="Run only the specified question_id. Can be repeated.",
    )
    parser.add_argument("--question-id-start", type=int, help="Inclusive question_id start")
    parser.add_argument("--question-id-end", type=int, help="Inclusive question_id end")
    parser.add_argument("--limit", type=int, help="Max number of questions to run")
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        help="Override single model request timeout in seconds for this run.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rerun rows even if the chosen attempt already has finished_at.",
    )
    parser.add_argument(
        "--persist-result",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write results back to eval_results. Default: true.",
    )
    return parser.parse_args()


def build_question_query(args: argparse.Namespace):
    stmt = select(EvalResult.question_id).where(EvalResult.model_id == args.model_id)

    if args.question_ids:
        stmt = stmt.where(EvalResult.question_id.in_(args.question_ids))
    if args.question_id_start is not None:
        stmt = stmt.where(EvalResult.question_id >= args.question_id_start)
    if args.question_id_end is not None:
        stmt = stmt.where(EvalResult.question_id <= args.question_id_end)

    if not args.force:
        attempt_finished_at = getattr(EvalResult, f"attempt_{args.attempt}_finished_at")
        stmt = stmt.where(attempt_finished_at.is_(None))

    stmt = stmt.order_by(EvalResult.question_id.asc())
    if args.limit is not None:
        stmt = stmt.limit(args.limit)
    return stmt


def main() -> None:
    args = parse_args()

    with get_sync_session() as session:
        model = get_model_detail(session, args.model_id)
        question_ids = list(session.scalars(build_question_query(args)).all())

        print(f"model_id={model.model_id}")
        print(f"model_name={model.model_name}")
        print(f"api_style={model.api_style}")
        print(f"api_model={model.api_model}")
        print(f"attempt={args.attempt}")
        print(f"persist_result={args.persist_result}")
        print(f"request_timeout_seconds={args.request_timeout_seconds or 'default'}")
        print(f"selected_questions={len(question_ids)}")

        if not question_ids:
            print("No questions selected.")
            return

        started_at = perf_counter()
        counters: Counter[str] = Counter()

        for index, question_id in enumerate(question_ids, start=1):
            item_started_at = perf_counter()
            print(f"--> [{index}/{len(question_ids)}] starting question_id={question_id}")

            result = run_evaluation(
                session,
                EvaluationRunRequest(
                    question_id=question_id,
                    model_id=args.model_id,
                    attempt=args.attempt,
                    persist_result=args.persist_result,
                    request_timeout_seconds=args.request_timeout_seconds,
                ),
            )

            if result.error:
                status = "error"
            elif result.attempt_result == 1:
                status = "correct"
            elif result.attempt_result == 0:
                status = "incorrect"
            else:
                status = "unknown"

            counters[status] += 1
            item_elapsed = perf_counter() - item_started_at
            total_elapsed = perf_counter() - started_at
            average_seconds = total_elapsed / index
            remaining = len(question_ids) - index
            eta_seconds = average_seconds * remaining

            print(
                f"<-- [{index}/{len(question_ids)}] "
                f"question_id={question_id} "
                f"status={status} "
                f"item_elapsed={item_elapsed:.2f}s "
                f"judge_feedback={result.judge_feedback!r} "
                f"error={result.error!r}"
            )
            print(
                f"    progress={render_progress_bar(index, len(question_ids))} "
                f"{index}/{len(question_ids)} "
                f"elapsed={format_duration(total_elapsed)} "
                f"avg={average_seconds:.2f}s/q "
                f"eta={format_duration(eta_seconds)}"
            )

        elapsed = perf_counter() - started_at
        print("Summary")
        print(f"  total={len(question_ids)}")
        print(f"  correct={counters['correct']}")
        print(f"  incorrect={counters['incorrect']}")
        print(f"  error={counters['error']}")
        print(f"  unknown={counters['unknown']}")
        print(f"  elapsed_seconds={elapsed:.2f}")


if __name__ == "__main__":
    main()
