"""Upgrade the original create_all SQLite demo database without deleting it."""

import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
import secrets


REVISION = "091ae9e801ad"


def main():
    db_path = Path(sys.argv[1] if len(sys.argv) > 1 else "instance/database.db")
    if not db_path.exists():
        print(f"No SQLite file at {db_path}; run flask db upgrade instead.")
        return

    connection = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "alembic_version" in tables:
            print("Migration history already exists; nothing to do.")
            return
        if "orders" not in tables:
            print("No legacy orders table; run flask db upgrade instead.")
            return

        backup = db_path.with_name(f"{db_path.name}.legacy-{datetime.now(timezone.utc):%Y%m%d%H%M%S}.bak")
        shutil.copy2(db_path, backup)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(orders)")}
        if "public_token" not in columns:
            connection.execute("ALTER TABLE orders ADD COLUMN public_token VARCHAR(64)")
            rows = connection.execute("SELECT id FROM orders WHERE public_token IS NULL").fetchall()
            for (order_id,) in rows:
                connection.execute(
                    "UPDATE orders SET public_token = ? WHERE id = ?",
                    (secrets.token_urlsafe(32), order_id),
                )
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_public_token ON orders(public_token)")
        connection.execute("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
        connection.execute("INSERT INTO alembic_version (version_num) VALUES (?)", (REVISION,))
        connection.commit()
        print(f"Legacy SQLite upgraded safely; backup saved at {backup}.")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
