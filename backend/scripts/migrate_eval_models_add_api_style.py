from __future__ import annotations

import argparse

import psycopg


ALTER_STATEMENTS = [
    "ALTER TABLE eval_models ADD COLUMN IF NOT EXISTS api_style TEXT;",
    "ALTER TABLE eval_models ALTER COLUMN api_style SET DEFAULT 'chat_completions';",
    "UPDATE eval_models SET api_style = 'chat_completions' WHERE api_style IS NULL OR btrim(api_style) = '';",
    "ALTER TABLE eval_models ALTER COLUMN api_style SET NOT NULL;",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add api_style column to eval_models for chat/responses protocol selection."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5431)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="postgre")
    parser.add_argument("--db-name", default="pdf_question_bank")
    return parser.parse_args()


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
                for statement in ALTER_STATEMENTS:
                    cur.execute(statement)

                cur.execute(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'eval_models'
                    ORDER BY ordinal_position
                    """
                )
                rows = cur.fetchall()
    finally:
        conn.close()

    print(f"database={args.db_name}")
    print("table=eval_models")
    for column_name, data_type in rows:
        print(f"{column_name}: {data_type}")


if __name__ == "__main__":
    main()
