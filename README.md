# Procedure Tool

Satellite operations procedure runner: multi-user, fleet tracking, YAML procedures, offline-first. Run step-by-step checklists, mission logs, anomaly tracking, handbooks, and more.

**Requirements:** Python 3.10+. All commands below are run from the `satops_procedures/` directory.

---

## How to Get Started

One command sets up everything after a fresh clone or database reset:

```bash
cd satops_procedures
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
python manage.py quickstart
python manage.py runserver
```

`quickstart` runs migrations, collects static files, and seeds all sample data in one step. To also create a superuser:

```bash
python manage.py quickstart --superuser admin
```

Open **http://localhost:8000**.

- **Visitors** see a product landing page (homepage) describing SatOps features.
- **Logged-in users** see the mission selector with two default missions: **Simulation** and **Sandbox**.
- Selecting a mission opens the full dashboard with all tools.

**What's inside each mission:**

- **Dashboard** — Recent runs, search, Start Procedure
- **Procedures** — List, review, create, edit, clone
- **Mission Scribe** — Timeline, shifts, handoff notes
- **Fleet Anomaly Tracker** — Report and track anomalies
- **Alerts & Limits Handbook**, **FDIR Handbook** — Alert and fault reference
- **Commands & Telemetry**, **References**, **SME Requests** — Catalogs and workflow

**Admin:** http://localhost:8000/admin/ (satellites, procedures, users, and all app data)

**Make shortcuts:** From `satops_procedures/`, run `make install` → `make quickstart` → `make run`.

---

## After a Database Reset

If you drop or delete the database and start fresh, just run:

```bash
python manage.py quickstart
```

This single command handles everything:
1. **migrate** — creates all tables and seeds the two default missions (Simulation & Sandbox)
2. **collectstatic** — gathers Django admin CSS/JS so the admin panel looks correct
3. **seed_all** — loads procedures, satellites, anomalies, scribe roles, handbooks, and all other sample data

The Simulation and Sandbox missions are created automatically by a data migration during `migrate`, so even a bare `python manage.py migrate` will give you the two missions.

---

## Admin & login

- **First-time:** Run `python manage.py createsuperuser`, then log in at /admin/
- **Main app:** Starting a procedure requires login. Use the same accounts at `/login/`. You are recorded as the operator for each run.
- **Add users:** Admin → Authentication → Users → Add user (set Staff status for admin access)

---

## Default Missions

Two missions are created automatically when the database is set up:

| Mission | Color | Purpose |
|---------|-------|---------|
| **Simulation** | Purple | Training, testing, and demonstration of satellite operations workflows |
| **Sandbox** | Amber | Experimentation and learning — create, edit, and delete freely |

You can create additional missions from the mission selector page or via the admin panel.

---

## Homepage

The product landing page at `/` is shown to unauthenticated visitors. It describes SatOps features, tools, and workflow. Logged-in users are taken straight to the mission selector. The homepage is also always available at `/homepage/`.

---

## Seed commands (optional)

The `quickstart` command runs all seeds automatically. If you need to run them individually:

```bash
python manage.py seed_missions     # Simulation + Sandbox missions and all screen data
python manage.py seed_procedures   # Procedures, tags, subsystems, satellites, sample runs
python manage.py seed_scribe       # Mission Scribe roles, categories, entry templates
python manage.py seed_handbook     # Alerts & Limits Handbook (--alerts for samples)
python manage.py seed_fdir         # FDIR Handbook (--entries for samples)
python manage.py seed_anomalies    # Fleet Anomaly Tracker sample anomalies
python manage.py seed_references   # Central Reference Page
python manage.py seed_cmdtlm       # Command & Telemetry definitions
python manage.py seed_smerequests   # SME Request types
python manage.py seed_all          # All of the above in one go
```

All seed commands are idempotent — safe to run multiple times without creating duplicates.

---

## Migrations

Each app has a single `0001_initial.py` migration. The only extra migration is `missions/0002_seed_default_missions.py`, which creates the Simulation and Sandbox missions automatically.

| App | Migrations |
|-----|------------|
| missions | `0001_initial` + `0002_seed_default_missions` (data) |
| procedures, scribe, handbook, fdir, anomalies, cmdtlm, references, smerequests, auditlog | `0001_initial` each |

---

## Structure

| Path | Purpose |
|------|---------|
| `satops_procedures/` | Django project root (manage.py, requirements.txt) |
| `satops/` | Project config (settings, URLs) |
| `missions/` | Mission models, selector, quickstart command |
| `procedures/` | Procedure runner, YAML loader, models |
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
