"""Smoke test for Python-to-PostgreSQL connectivity."""

from .connection import get_connection


def main() -> None:
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
        print("PostgreSQL connection successful.")
        print(f"Server: {version}")
    except RuntimeError as error:
        print(f"PostgreSQL connection failed: {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()