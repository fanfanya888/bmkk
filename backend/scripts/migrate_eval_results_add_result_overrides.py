from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import get_sync_session


ALTER_STATEMENTS = [
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_1_result_override SMALLINT;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_1_result_overridden_at TIMESTAMPTZ;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_2_result_override SMALLINT;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_2_result_overridden_at TIMESTAMPTZ;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_3_result_override SMALLINT;",
    "ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS attempt_3_result_overridden_at TIMESTAMPTZ;",
]


def main() -> None:
    with get_sync_session() as session:
        for statement in ALTER_STATEMENTS:
            session.execute(text(statement))
        session.commit()

        rows = session.execute(
            text(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'eval_results'
                  AND (
                    column_name LIKE 'attempt\\_%\\_result\\_override'
                    OR column_name LIKE 'attempt\\_%\\_result\\_overridden\\_at'
                  )
                ORDER BY ordinal_position
                """
            )
        ).all()

    print("table=eval_results")
    for column_name, data_type in rows:
        print(f"{column_name}: {data_type}")


if __name__ == "__main__":
    main()
