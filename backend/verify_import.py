"""Print imported UFDR record counts for a case."""

import argparse

from .database.connection import get_connection


TABLES = ("cases", "devices", "contacts", "messages", "calls", "media")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify UFDR import counts")
    parser.add_argument("--case-name", required=True)
    parser.add_argument("--source-file", required=True)
    args = parser.parse_args()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM cases WHERE case_name = %s AND source_file = %s",
                           (args.case_name, args.source_file))
            case = cursor.fetchone()
            if case is None:
                raise SystemExit("Case not found")
            case_id = case[0]
            print(f"Case: {args.case_name}")
            for table in TABLES:
                column = "id" if table == "cases" else "case_id"
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} = %s", (case_id,))
                print(f"{table}: {cursor.fetchone()[0]}")
            for table in ("ocr_results", "transcriptions", "image_analysis", "image_tags"):
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {table} child
                    JOIN media ON media.id = child.media_id
                    WHERE media.case_id = %s
                    """, (case_id,))
                print(f"{table}: {cursor.fetchone()[0]}")


if __name__ == "__main__":
    main()