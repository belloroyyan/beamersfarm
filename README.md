# Beamers Farms

Flask storefront and operations desk for Beamers Farms, Osogbo, Nigeria. This project keeps the supplied Python/Jinja application, SQLAlchemy models and Alembic migrations; it does not use the unused React starter.

## Local development

Python 3.12 is used by the container. Create a virtual environment, install the pinned dependencies, and use a private SQLite database for local work:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
CHICKEN_DATABASE_URL=sqlite:////tmp/beamers-farms-local.sqlite \
AUTO_CREATE_SCHEMA=true PORT=3000 .venv/bin/python app.py
```

The development-only schema bootstrap seeds starter products, a shop record and delivery zones in that SQLite file. Do not point `CHICKEN_DATABASE_URL` at the shared managed `DATABASE_URL` when testing: the managed database is shared with production. Open the Webdev Preview from the project workspace.

## Schema migrations

The supplied migration history contains MySQL-specific `ALTER COLUMN` operations (including revision `z1a2b3`), so the complete history cannot be applied to SQLite. Keep the local Preview workflow above on its isolated SQLite database with `AUTO_CREATE_SCHEMA=true`; it creates tables from the current ORM models and does not run Alembic. The new feature migration was separately exercised against an isolated SQLite schema fixture.

For a full migration rehearsal, use an isolated disposable MySQL-compatible database. Set `CHICKEN_DATABASE_URL` to that private test DSN, keep `AUTO_CREATE_SCHEMA=false`, then run `.venv/bin/flask --app app db upgrade`. Do not point the rehearsal at the Webdev managed database.

The project includes the existing migration history and a merge-only revision joining the logistics workflow and operational-index branches. The merge revision does not alter application tables; it records that both parent migrations belong to one Alembic history. Before applying it to a production database, take the normal managed-database backup and verify that the database is at a compatible revision. Do not use `flask db stamp` to bypass pending schema changes.

For Railway, configure the service's **Pre-deploy Command** as `python -m scripts.railway_migrate`. This helper checks that the configured database accepts a connection (up to 45 attempts, two seconds apart) and then runs `flask --app app db upgrade`. It does not create, drop, stamp, or reset tables. The normal Gunicorn start command remains unchanged. Ensure production uses the intended `DATABASE_URL`; because `CHICKEN_DATABASE_URL` takes precedence in this project, remove that override from Railway unless it is deliberately intended to point at the production database.

## Production runtime

The Webdev container listens on `PORT` (default 3000), runs Gunicorn, and exposes `/health` for readiness. Runtime configuration must be supplied outside the repository. Production requires:

- `APP_ENV=production`
- a strong `SECRET_KEY`
- `ADMIN_PASSWORD_HASH` and `DISPATCH_RIDER_PASSWORD_HASH` (Werkzeug password hashes; do not use the development-only plaintext variables)
- the managed `DATABASE_URL`
- `PUBLIC_ORIGIN` set to the public HTTPS site origin for payment callback/return URLs and canonical links

Set `AUTO_CREATE_SCHEMA=false` in production and apply reviewed Alembic migrations explicitly. Never commit provider secrets or a `.env` file.

## Integrations

- OPay hosted checkout is disabled until the Owner supplies approved test/live merchant configuration; manual OPay transfer remains available. See [`OPAY_SETUP.md`](OPAY_SETUP.md) for the provider contracts and credential checklist.
- Email verification and owner email campaigns use a provider-neutral Resend transport. Resend is not used. Resend configuration is optional until the Owner activates it.
- Customer browser push and abandoned-cart recovery require VAPID settings. Cart recovery is processed by the separate recurring command `python -m scripts.process_abandoned_carts`, not by the Gunicorn web request worker; schedule it in the chosen deployment environment after configuration.
- WhatsApp customer broadcasts require customer consent, the Meta Cloud API configuration, and a separately approved campaign template with a single body parameter. Email attachments are validated and are sent only through configured Resend.

Account verification, online payment and messaging integrations remain unavailable until their respective server-only credentials and account approvals have been supplied by the Owner. Do not simulate successful payment or delivery in live mode.
