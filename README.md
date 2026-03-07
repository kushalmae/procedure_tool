# Procedure Tool

Satellite operations procedure runner: multi-user, fleet tracking, YAML procedures, offline-first. Run step-by-step checklists, mission logs, anomaly tracking, handbooks, and more.

**Requirements:** Python 3.10+. All commands below are run from the `satops_procedures/` directory.

---

## How to Get Started

```bash
cd satops_procedures
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_all
python manage.py createsuperuser   # optional
python manage.py runserver
```

Open **http://localhost:8000**. You’ll see:

- **Dashboard** — Recent runs, search, Start Procedure
- **Procedures** — List, review, create, edit, clone
- **Mission Scribe** — Timeline, shifts, handoff notes
- **Fleet Anomaly Tracker** — Report and track anomalies
- **Alerts & Limits Handbook**, **FDIR Handbook** — Alert and fault reference
- **Commands & Telemetry**, **References**, **SME Requests** — Catalogs and workflow

**Admin:** http://localhost:8000/admin/ (satellites, procedures, users, and all app data)

**Make shortcuts:** From `satops_procedures/`, run `make install` → `make migrate` → `make seed` → `make run`.

---

## Admin & login

- **First-time:** Run `python manage.py createsuperuser`, then log in at /admin/
- **Main app:** Starting a procedure requires login. Use the same accounts at `/login/`. You are recorded as the operator for each run.
- **Add users:** Admin → Authentication → Users → Add user (set Staff status for admin access)

---

## Seed commands (optional)

```bash
python manage.py seed_procedures   # Bus Checkout + sample satellites
python manage.py seed_scribe      # Mission Scribe roles + categories
python manage.py seed_handbook    # Alerts & Limits Handbook (--alerts for samples)
python manage.py seed_fdir        # FDIR Handbook (--entries for samples)
python manage.py seed_anomalies   # Fleet Anomaly Tracker
python manage.py seed_references  # Central Reference Page
python manage.py seed_all         # All of the above
```

After `seed_all`, you can start a run from the Dashboard (Start Procedure → pick a satellite and procedure).

---

## Structure

| Path | Purpose |
|------|---------|
| `satops_procedures/` | Django project root (manage.py, requirements.txt) |
| `satops/` | Project config (settings, URLs) |
| `procedures/` | Main app: runner, YAML loader, models |
| `scribe/` | Mission Scribe (timeline, shifts) |
| `anomalies/` | Fleet Anomaly Tracker |
| `handbook/` | Alerts & Limits Handbook |
| `fdir/` | FDIR Handbook |
| `cmdtlm/` | Commands & Telemetry |
| `references/` | Central Reference Page |
| `smerequests/` | SME Request Workflow |
| `procedures_yaml/` | YAML procedure definitions |

---

## Docker & deployment

For local runs with PostgreSQL or production on Fly.io, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Documentation

| Doc | Description |
|-----|-------------|
| [PRODUCT.md](PRODUCT.md) | Product overview, key features, modules |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Tech stack, URLs, data models, CI/CD |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Bare Python, Docker Compose, Fly.io |
