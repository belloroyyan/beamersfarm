"""Process a bounded batch of signed-in abandoned carts and exit."""
from app import create_app
from utils.abandoned_carts import process_abandoned_carts


if __name__ == "__main__":
    application = create_app()
    with application.app_context():
        print(process_abandoned_carts())
