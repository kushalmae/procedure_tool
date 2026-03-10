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

# Setup (once)
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_missions   # Simulation + Sandbox missions and all screen data
# Or: python manage.py seed_all
python manage.py createsuperuser

# Run
python manage.py runserver 0.0.0.0:8000
```

→ **http://localhost:8000**

---

## Option 2 — Docker Compose (local prod-like)

PostgreSQL + Gunicorn in containers. Mirrors Fly.io stack.

```bash
cd satops_procedures/

# Setup
cp .env.example .env
# Optional: uncomment DJANGO_SUPERUSER_* and SEED_ON_STARTUP=true in .env

# Run
docker compose up --build
```

→ **http://localhost:8000**

**Useful commands:**

| Action | Command |
|--------|---------|
| Background | `docker compose up -d` |
| Shell | `docker compose exec web bash` |
| Manage.py | `docker compose exec web python manage.py seed_missions --all-screens` or `seed_all` |
| Stop | `docker compose down` |
| Reset DB | `docker compose down -v` |

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
fly ssh console -C "python manage.py createsuperuser"   # optional
fly ssh console -C "python manage.py seed_missions --all-screens"  # optional (simulation + all screens)
```

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

---

## Quick reference

| Command | Purpose |
|---------|---------|
| `make run` | Bare Python — start dev server |
| `make docker-up` | Docker — start stack |
| `make fly-deploy` | Fly.io — deploy to production |
| `make ci` | Run lint + test locally |
