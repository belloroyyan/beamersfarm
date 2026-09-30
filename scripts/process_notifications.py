"""Process a bounded notification batch and exit for Railway Cron."""

from app import create_app
from services.whatsapp import process_pending_notifications


if __name__ == "__main__":
    application = create_app()
    with application.app_context():
        print(process_pending_notifications())
