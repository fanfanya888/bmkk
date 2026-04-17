from __future__ import annotations

import argparse

import psycopg2


ALTER_STATEMENTS = [
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_1_response_text TEXT;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_1_judge_feedback TEXT;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_1_error TEXT;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_1_finished_at TIMESTAMPTZ;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_2_response_text TEXT;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_2_judge_feedback TEXT;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_2_error TEXT;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_2_finished_at TIMESTAMPTZ;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_3_response_text TEXT;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_3_judge_feedback TEXT;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_3_error TEXT;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_3_finished_at TIMESTAMPTZ;",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add attempt response metadata columns to eval_results."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5431)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="postgre")
    parser.add_argument("--db-name", default="pdf_question_bank")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    conn = psycopg2.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        dbname=args.db_name,
    )
    try:
        with conn:
            with conn.cursor() as cur:
                for statement in ALTER_STATEMENTS:
                    cur.execute(statement)

                cur.execute(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'eval_results'
                    ORDER BY ordinal_position
                    """
                )
                rows = cur.fetchall()
    finally:
        conn.close()

    print(f"database={args.db_name}")
    print("table=eval_results")
    for column_name, data_type in rows:
        print(f"{column_name}: {data_type}")


if __name__ == "__main__":
    main()
