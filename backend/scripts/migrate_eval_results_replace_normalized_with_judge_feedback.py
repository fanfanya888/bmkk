from __future__ import annotations

import argparse

import psycopg


RENAMES = [
    ("attempt_1_normalized_text", "attempt_1_judge_feedback"),
    ("attempt_2_normalized_text", "attempt_2_judge_feedback"),
    ("attempt_3_normalized_text", "attempt_3_judge_feedback"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename eval_results normalized_text columns to judge_feedback."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5431)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="postgre")
    parser.add_argument("--db-name", default="pdf_question_bank")
    return parser.parse_args()


def column_exists(cur: psycopg.Cursor, column_name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'eval_results'
          AND column_name = %s
        """,
        (column_name,),
    )
    return cur.fetchone() is not None


def main() -> None:
    args = parse_args()
    conn = psycopg.connect(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        dbname=args.db_name,
    )
    try:
        with conn:
            with conn.cursor() as cur:
                for old_name, new_name in RENAMES:
                    if column_exists(cur, old_name) and not column_exists(cur, new_name):
                        cur.execute(
                            f"ALTER TABLE eval_results RENAME COLUMN {old_name} TO {new_name}"
                        )

                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'eval_results'
                    ORDER BY ordinal_position
                    """
                )
                for (column_name,) in cur.fetchall():
                    print(column_name)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
