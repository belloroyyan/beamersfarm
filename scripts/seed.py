from app import create_app, seed_products
from models import db

app = create_app()
with app.app_context():
    seed_products()
    db.session.remove()
print("seed complete")
