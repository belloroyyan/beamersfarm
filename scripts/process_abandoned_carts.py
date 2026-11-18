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
    """Wait until Railway MySQL accepts a real query, not merely a TCP connection."""
    logger = logging.getLogger(__name__)
    for attempt in range(1, MAX_DATABASE_ATTEMPTS + 1):
        try:
            with db.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database is reachable for abandoned-cart worker.")
            return
        except SQLAlchemyError as exc:
            db.session.rollback()
            db.engine.dispose()
            if attempt == MAX_DATABASE_ATTEMPTS:
                logger.exception(
                    "Database did not become reachable after %s attempts.",
                    MAX_DATABASE_ATTEMPTS,
                )
                raise
            logger.warning(
                "Database unavailable for abandoned-cart worker; attempt %s/%s failed (%s). Retrying in %ss.",
                attempt,
                MAX_DATABASE_ATTEMPTS,
                type(exc).__name__,
                DATABASE_RETRY_SECONDS,
            )
            time.sleep(DATABASE_RETRY_SECONDS)


def process_batch_with_retry():
    """Retry only failures before batch processing starts (e.g. candidate SELECT).

    Per-cart failures are handled and counted inside process_abandoned_carts().
    Retrying those here could resend a push whose delivery succeeded but whose
    database commit failed, so only an exception escaping the batch function
    is retried.
    """
    logger = logging.getLogger(__name__)
    max_batch_attempts = 3
    wait_for_database()
    for attempt in range(1, max_batch_attempts + 1):
        try:
            return process_abandoned_carts()
        except SQLAlchemyError as exc:
            db.session.rollback()
            db.engine.dispose()
            if attempt == max_batch_attempts:
                logger.exception(
                    "Abandoned-cart batch could not start after %s attempts.",
                    max_batch_attempts,
                )
                raise
            logger.warning(
                "Database failed before abandoned-cart batch could be read; attempt %s/%s failed (%s). Retrying in %ss.",
                attempt,
                max_batch_attempts,
                type(exc).__name__,
                DATABASE_RETRY_SECONDS,
            )
            time.sleep(DATABASE_RETRY_SECONDS)
            wait_for_database()
    raise RuntimeError("Abandoned-cart batch exited retry loop unexpectedly.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    application = create_app()
    with application.app_context():
        result = process_batch_with_retry()
        print("Abandoned-cart processing result:", result, flush=True)
        if result.get("failed"):
            # Non-zero exit makes operational/database errors visible in
            # Railway Cron logs. Delivery failures are counted and left
            # pending for a future run; they do not fail the whole job.
            raise SystemExit(1)
