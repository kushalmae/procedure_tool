# AGENTS.md

## Cursor Cloud specific instructions

This is a Django project in `satops_procedures/`. All `manage.py` commands run from that directory with the venv activated.

### Services

| Service | Command | Notes |
|---------|---------|-------|
| Django dev server | `source .venv/bin/activate && python manage.py runserver 0.0.0.0:8000` | Single process; serves all 5 apps on port 8000 |

No external services (databases, caches, queues) are required. SQLite is embedded (`ops.db`).

### Quick reference

- **Setup/run instructions**: see `satops_procedures/README.md`
- **Lint**: `python manage.py check` (Django system checks; no separate linter configured)
- **Tests**: `python manage.py test` (standard Django test runner; test files exist but have no cases yet)
- **Migrations**: `python manage.py migrate` (run after model changes)
- **Seed data**: `python manage.py seed_all` (populates all apps with sample data)
- **Superuser**: `DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_PASSWORD=admin123 DJANGO_SUPERUSER_EMAIL=admin@example.com python manage.py createsuperuser --noinput`

### Gotchas

- The venv lives at `satops_procedures/.venv`. Always activate it before running commands.
- `python3.12-venv` system package is required to create the venv (not installed by default on the base image).
- Login is required to start/run procedures, add scribe entries, report anomalies, and create/edit handbook and FDIR entries. The admin account (admin / admin123) works for all features.
- The dev server must bind to `0.0.0.0:8000` (not just `127.0.0.1`) for browser access from the Desktop pane.
