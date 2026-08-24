"""PostgreSQL connection setup."""

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV = PROJECT_ROOT / "backend" / ".env"
ROOT_ENV = PROJECT_ROOT / ".env"

# Prefer the requested backend configuration; the root fallback supports the
# existing workspace until its configuration is moved to backend/.env.
load_dotenv(BACKEND_ENV)
load_dotenv(ROOT_ENV)


def get_connection() -> psycopg.Connection:
    """Open and return a PostgreSQL connection from the environment."""

    missing = [
        name
        for name in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")
        if not os.getenv(name)
    ]
    if missing:
        raise RuntimeError(
            "Missing required database environment variable(s): "
            + ", ".join(missing)
        )

    try:
        return psycopg.connect(
            host=os.environ["DB_HOST"],
            port=os.environ["DB_PORT"],
            dbname=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
        )
    except psycopg.Error as error:
        raise RuntimeError(
            "Unable to connect to PostgreSQL. Verify the host, port, database, "
            "user, and password configuration."
        ) from error