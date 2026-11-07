"""Process a bounded abandoned-cart batch and exit for Railway Cron."""

import logging

from app import create_app
from utils.abandoned_carts import process_abandoned_carts


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    application = create_app()
    with application.app_context():
        result = process_abandoned_carts()
        print("Abandoned-cart processing result:", result, flush=True)
        if result.get("failed"):
            # Non-zero exit makes operational/database errors visible in
            # Railway Cron logs. Delivery failures are counted and left
            # pending for a future run; they do not fail the whole job.
            raise SystemExit(1)
