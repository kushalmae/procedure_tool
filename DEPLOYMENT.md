# Deployment Guide

Three ways to run the SatOps Procedures app. Same codebase; only environment differs.

| Mode | Database | Server | Use case |
|------|----------|--------|----------|
| **1. Bare Python** | SQLite | Django runserver | Local dev, quick iteration |
| **2. Docker Compose** | PostgreSQL | Gunicorn | Local testing, mirrors production |
| **3. Fly.io** | Fly Postgres | Gunicorn | Production |

---

## Option 1 — Bare Python (local dev)

No Docker. No env vars. Fastest setup.

```bash
cd satops_procedures/

# Full setup in one command (migrate + collectstatic + seed all data)
pip install -r requirements.txt
python manage.py quickstart
python manage.py createsuperuser   # optional — or use: quickstart --superuser admin

# Run
python manage.py runserver 0.0.0.0:8000
```

→ **http://localhost:8000**

### After a database reset

If you delete `ops.db` or start fresh, just run `quickstart` again:

```bash
python manage.py quickstart
```

This runs `migrate`, `collectstatic`, and `seed_all` in one step. The two default missions (Simulation and Sandbox) are created automatically during `migrate` via a data migration, so they're always present.

### Step-by-step alternative

If you prefer running each step manually:

```bash
python manage.py migrate           # Creates tables + seeds Simulation & Sandbox missions
python manage.py collectstatic     # Collects admin CSS/JS (auto-detected on startup too)
python manage.py seed_all          # Seeds procedures, anomalies, handbooks, etc.
python manage.py createsuperuser   # Create admin account
```

---

## Option 2 — Docker Compose (local prod-like)

PostgreSQL + Gunicorn in containers. Mirrors Fly.io stack.

```bash
cd satops_procedures/

# Setup
cp .env.example .env
# Optional: uncomment DJANGO_SUPERUSER_* lines in .env to auto-create an admin

# Run
docker compose up --build
```

→ **http://localhost:8000**

The Docker entrypoint (`entrypoint.sh`) automatically runs on every startup:
1. `migrate` — applies migrations and seeds default missions
2. `collectstatic` — gathers static files for Gunicorn/WhiteNoise
3. `createsuperuser` — if `DJANGO_SUPERUSER_*` env vars are set
4. `seed_all` — seeds all sample data (set `SKIP_SEED=true` to disable)

**Useful commands:**

| Action | Command |
|--------|---------|
| Background | `docker compose up -d` |
| Shell | `docker compose exec web bash` |
| Manage.py | `docker compose exec web python manage.py quickstart` |
| Stop | `docker compose down` |
| Reset DB | `docker compose down -v` (deletes PostgreSQL volume — fresh start) |

After `docker compose down -v`, the next `docker compose up` will re-run all migrations and seeding automatically.

---

## Option 3 — Fly.io (production)

**First deploy:**

```bash
cd satops_procedures/

fly launch --no-deploy
fly postgres create --name satops-db
fly postgres attach satops-db

fly secrets set DJANGO_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"

fly deploy
fly ssh console -C "python manage.py createsuperuser"
```

The entrypoint runs `migrate`, `collectstatic`, and `seed_all` automatically on every deploy.

**Later deploys:**

```bash
cd satops_procedures/
fly deploy
```

**Optional:** Auto-create superuser on boot — set secrets before deploy:

```bash
fly secrets set DJANGO_SUPERUSER_USERNAME=admin
fly secrets set DJANGO_SUPERUSER_EMAIL=admin@example.com
fly secrets set DJANGO_SUPERUSER_PASSWORD=<strong-password>
fly deploy
```

**Optional:** Skip seeding on deploy (if you only want your own data):

```bash
fly secrets set SKIP_SEED=true
fly deploy
```

---

## What happens on startup

| Step | Bare Python | Docker / Fly.io |
|------|-------------|-----------------|
| Migrations | `quickstart` or `migrate` | `entrypoint.sh` runs `migrate` |
| Static files | `quickstart` or `collectstatic` (auto-detected if missing) | `entrypoint.sh` runs `collectstatic` |
| Default missions | Created by data migration (`missions/0002`) | Same |
| Sample data | `quickstart` runs `seed_all` | `entrypoint.sh` runs `seed_all` (unless `SKIP_SEED=true`) |
| Superuser | `quickstart --superuser admin` or `createsuperuser` | Auto-created if `DJANGO_SUPERUSER_*` env vars set |
| Admin CSS/JS | Auto-collected if missing on app startup | Collected by `entrypoint.sh` |

---

## Environment variables

See `.env.example` for the full list. Key variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | *(unset = SQLite)* | PostgreSQL connection string |
| `DJANGO_SECRET_KEY` | `dev-secret-...` | Must be random in production |
| `DJANGO_DEBUG` | `True` | Set `False` in production |
| `DJANGO_ALLOWED_HOSTS` | `*` | Comma-separated hostnames |
| `SKIP_SEED` | *(unset)* | Set `true` to skip seeding on Docker/Fly startup |
| `DJANGO_SUPERUSER_USERNAME` | *(unset)* | Auto-create superuser on startup |
| `DJANGO_SUPERUSER_EMAIL` | *(unset)* | Auto-create superuser on startup |
| `DJANGO_SUPERUSER_PASSWORD` | *(unset)* | Auto-create superuser on startup |

---

## Quick reference

| Command | Purpose |
|---------|---------|
| `make quickstart` | One-step setup: migrate + collectstatic + seed |
| `make run` | Bare Python — start dev server |
| `make docker-up` | Docker — start stack |
| `make fly-deploy` | Fly.io — deploy to production |
| `make ci` | Run lint + test locally |
