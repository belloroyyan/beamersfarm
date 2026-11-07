"""Wait for the configured database, then apply reviewed Alembic migrations.

Configure Railway's Pre-deploy Command as:
    python -m scripts.railway_migrate

This script never creates, drops, stamps, or resets the database.
"""

from __future__ import annotations

import subprocess
import sys
import time
from urllib.parse import make_url

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from config import Config, DATABASE_CONNECT_ARGS

MAX_ATTEMPTS = 45
RETRY_SECONDS = 2


def main() -> int:
    database_url = Config.SQLALCHEMY_DATABASE_URI
    parsed_url = make_url(database_url)
    safe_target = parsed_url.host or parsed_url.drivername
    if parsed_url.port:
        safe_target = f"{safe_target}:{parsed_url.port}"

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args=DATABASE_CONNECT_ARGS,
    )
    try:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                with engine.connect() as connection:
                    connection.exec_driver_sql("SELECT 1")
                print(f"Database is reachable ({safe_target}).", flush=True)
                break
            except SQLAlchemyError as exc:
                if attempt == MAX_ATTEMPTS:
                    print(
                        f"Database did not become reachable at {safe_target} "
                        f"after {MAX_ATTEMPTS} attempts. Last error type: "
                        f"{type(exc).__name__}. Migration was not started.",
                        file=sys.stderr,
                        flush=True,
                    )
                    return 1
                print(
                    f"Waiting for database ({safe_target}); "
                    f"attempt {attempt}/{MAX_ATTEMPTS} failed "
                    f"({type(exc).__name__}). Retrying in {RETRY_SECONDS}s.",
                    flush=True,
                )
                time.sleep(RETRY_SECONDS)
    finally:
        engine.dispose()

    command = [sys.executable, "-m", "flask", "--app", "app", "db", "upgrade"]
    print("Applying Alembic migrations...", flush=True)
    result = subprocess.run(command, check=False)
    if result.returncode:
        print(
            f"Alembic migration command failed with exit code {result.returncode}.",
            file=sys.stderr,
            flush=True,
        )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
