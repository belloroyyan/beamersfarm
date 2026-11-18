"""Process a bounded abandoned-cart batch and exit for Railway Cron."""

import logging
import time

from app import create_app
from models import db
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from utils.abandoned_carts import process_abandoned_carts


MAX_DATABASE_ATTEMPTS = 15
DATABASE_RETRY_SECONDS = 4


def wait_for_database():
    """Wait briefly for Railway MySQL to accept connections after a restart."""
    for attempt in range(1, MAX_DATABASE_ATTEMPTS + 1):
        try:
            with db.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logging.getLogger(__name__).info("Database is reachable for abandoned-cart worker.")
            return
        except SQLAlchemyError as exc:
            if attempt == MAX_DATABASE_ATTEMPTS:
                logging.getLogger(__name__).error(
                    "Database did not become reachable after %s attempts; last error: %s",
                    MAX_DATABASE_ATTEMPTS,
                    type(exc).__name__,
                )
                raise
            logging.getLogger(__name__).warning(
                "Database unavailable for abandoned-cart worker; attempt %s/%s failed (%s). Retrying in %ss.",
                attempt,
                MAX_DATABASE_ATTEMPTS,
                type(exc).__name__,
                DATABASE_RETRY_SECONDS,
            )
            db.engine.dispose()
            time.sleep(DATABASE_RETRY_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    application = create_app()
    with application.app_context():
        wait_for_database()
        result = process_abandoned_carts()
        print("Abandoned-cart processing result:", result, flush=True)
        if result.get("failed"):
            # Non-zero exit makes operational/database errors visible in
            # Railway Cron logs. Delivery failures are counted and left
            # pending for a future run; they do not fail the whole job.
            raise SystemExit(1)
