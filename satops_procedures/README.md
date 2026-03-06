# Satops Procedures (Django)

Satellite operations procedure tool: multi-user, fleet tracking, YAML procedures, SQLite, Django Admin. Runs offline.

## Setup

```bash
cd satops_procedures
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_procedures   # optional: Bus Checkout procedure + sample satellites
python manage.py createsuperuser   # optional: for Django Admin
```

## Run

```bash
python manage.py runserver
```

Open http://localhost:8000 — Dashboard, Start Procedure, Run, History.

- **Admin**: http://localhost:8000/admin/ (Satellites, Procedures, Runs, Step Executions)

## Structure

- `satops/` — project settings and URLs
- `procedures/` — app: models, views, `services/` (procedure_loader, runner)
- `templates/` — dashboard, start, run, history
- `procedures_yaml/` — YAML procedure definitions (e.g. `bus_checkout.yaml`)
