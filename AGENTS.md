# AGENTS.md

## Cursor Cloud specific instructions

This is a Django monolith (single project, multiple apps) for satellite operations. No Node.js, Docker, or external services are needed.

### Project layout

- Django project root: `satops_procedures/` (contains `manage.py`)
- Apps: `procedures`, `scribe`, `anomalies`, `handbook`, `fdir`
- Database: SQLite (`ops.db`), auto-created by `migrate`
- Config: `satops_procedures/satops/settings.py`

### Running the app

```bash
cd satops_procedures
source .venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

See `satops_procedures/README.md` for full setup/seed/run instructions.

### Key dev notes

- **Venv**: The virtualenv lives at `satops_procedures/.venv`. Always activate it before running any `manage.py` commands.
- **python3.12-venv**: The system package `python3.12-venv` must be installed to create the venv (handled by the update script).
- **No automated tests**: The codebase has zero test files. `python manage.py test` returns 0 tests. Validation relies on `python manage.py check` (Django system checks) and manual/browser testing.
- **Auth for writes**: Starting procedures, adding scribe entries, reporting anomalies, and editing handbook/FDIR entries all require login. Create a superuser with `python manage.py createsuperuser` (non-interactive: set `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_PASSWORD`, `DJANGO_SUPERUSER_EMAIL` env vars and pass `--noinput`).
- **Seeding**: `python manage.py seed_all` populates all apps with sample data (satellites, procedures, scribe roles, handbook alerts, FDIR entries, anomalies). Safe to re-run (creates duplicates but does not error).
- **No lint tooling configured**: No flake8/ruff/mypy/pylint config. Use `python manage.py check` for Django-level validation.
