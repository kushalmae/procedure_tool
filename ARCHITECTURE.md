# Procedure Tool — Architecture

Quick reference for the satops procedure runner (Django app).

## Tech stack

| Layer | Choice |
|-------|--------|
| Framework | Django (ORM, auth, templates) |
| Database | SQLite (local dev) / PostgreSQL (production via Fly.io) |
| Procedures | YAML files in `procedures_yaml/` (PyYAML) |
| Front end | Server-rendered HTML + CSS (no JS framework) |
| Static files | WhiteNoise (compressed, cache-friendly serving) |
| App server | Gunicorn (WSGI) |
| Container | Docker |
| Hosting | Fly.io |

Local development uses SQLite; production runs on Fly.io with PostgreSQL.

---

## Repository layout

```
procedure_tool/
  satops_procedures/           # Django project
    manage.py, requirements.txt, ops.db
    satops/                    # Project config (settings, root urls, wsgi)
    procedures/                # Main app
      models.py                # Satellite, Tag, Procedure, ProcedureRun, StepExecution
      views.py, urls.py, admin.py
      services/
        procedure_loader.py    # load_procedure, save_procedure, YAML I/O
        runner.py              # get_next_step, get_step_context
      management/commands/seed_procedures.py
    templates/                 # base, dashboard, start, run, run_summary, history,
                               # procedure_list, procedure_review, procedure_create,
                               # procedure_edit, procedure_delete_confirm, login
    procedures_yaml/           # One YAML per procedure (name, version, steps)
    static/css/style.css
    scribe/                     # Mission Scribe app
      models.py                 # Role, EventCategory, ScribeTag, Shift, MissionLogEntry
      views.py, urls.py, admin.py
      management/commands/seed_scribe.py
    templates/scribe/           # timeline, entry_form, shift_list, shift_form, shift_detail
    anomalies/                  # Fleet Anomaly Tracker app
      models.py                 # Subsystem, AnomalyType, Anomaly, AnomalyNote
      views.py, urls.py, admin.py
      management/commands/seed_anomalies.py
    templates/anomalies/        # registry, anomaly_form, anomaly_detail
    handbook/                   # Alerts & Limits Handbook app
      models.py                 # Subsystem, AlertDefinition
      views.py, urls.py, admin.py
      management/commands/seed_handbook.py
    templates/handbook/         # alert_list, alert_detail, alert_form, alert_confirm_delete
    fdir/                       # FDIR Handbook app
      models.py                 # Subsystem, FDIREntry
      views.py, urls.py, admin.py
      management/commands/seed_fdir.py
    templates/fdir/             # entry_list, entry_detail, entry_form
    tests/                      # Centralized test suite
      test_procedures.py        # Procedures app tests
      test_scribe.py            # Mission Scribe tests
      test_anomalies.py         # Fleet Anomaly Tracker tests
      test_handbook.py          # Alerts & Limits Handbook tests
      test_fdir.py              # FDIR Handbook tests
  .github/workflows/           # CI/CD pipelines
    ci.yml                     # Lint + test on push/PR
    deploy.yml                 # Auto-deploy to Fly.io on main
  ARCHITECTURE.md               # This file
```

---

## Data model

- **Satellite** — name (fleet).
- **Tag** — name, slug; M2M with Procedure (filtering, search).
- **Procedure** — name, version, `yaml_file` (path under `procedures_yaml/`), tags.
- **ProcedureRun** — satellite, procedure, operator (FK User), start/end time, status (RUNNING/PASS/FAIL/CANCELLED), **run_notes** (handover/anomaly).
- **StepExecution** — run, step_id, description, status, input_value, notes, timestamp.

Procedure *definition* lives in YAML; runs and step results live in the database (SQLite locally, PostgreSQL in production).

- **Handbook:** `Subsystem` (name); `AlertDefinition` — parameter, subsystem FK, description, alert_conditions, warning/critical threshold (text), recommended_response, optional procedure FK, severity (Warning/Critical), version, created_at, updated_at.
- **FDIR:** `fdir.Subsystem` (name, slug); `FDIREntry` — name, fault_code, subsystem FK, severity (Info/Warning/Critical), fault_type, triggering_conditions, detection_thresholds, onboard_automated_response, M2M to `procedures.Procedure` (operator_procedures), version, created_at, updated_at.

- **Fleet Anomaly (anomalies):** `Subsystem` (name); `AnomalyType` (name); `Anomaly` — satellite FK, subsystem FK, anomaly_type FK, severity (Low/Medium/High/Critical), detection_time, operational_impact (choices), status (New/Investigating/Mitigated/Resolved), description, created_at, updated_at, reported_by FK; `AnomalyNote` — anomaly FK, created_at, created_by FK, body.

---

## Main URLs

| Path | Purpose |
|------|---------|
| `/` | Dashboard: recent runs, search, tag filter, Start Procedure |
| `/start/` | Start run (login required): pick satellite + procedure → new run |
| `/procedures/` | List procedures: Review, Edit, **Clone**, Start, Delete |
| `/procedure/review/?procedure=<id>` | Read-only procedure steps; “Start this procedure” |
| `/procedure/create/` | Create procedure (name, version, steps) → YAML + DB |
| `/procedure/<id>/edit/` | Edit procedure (YAML + DB) |
| `/procedure/<id>/clone/` | Clone procedure (“Copy of …”) → new YAML + Procedure, redirect to edit |
| `/procedure/<id>/delete/` | Confirm and delete procedure (YAML + DB, CASCADE runs) |
| `/run/<id>/` | Execute steps; run notes form (save without advancing step) |
| `/run/<id>/summary/` | All steps + run notes; print-friendly |
| `/history/` | Past runs, search, tag filter |
| `/login/`, `/logout/` | App auth (logout via POST) |
| `/scribe/` | Mission Scribe timeline (filters, search) |
| `/scribe/add/` | Add log entry (login required) |
| `/scribe/shifts/` | List shifts |
| `/scribe/shifts/add/` | Create shift |
| `/scribe/shifts/<id>/` | Shift detail (handoff notes, entries in shift) |
| `/anomalies/` | Fleet Anomaly Tracker: registry list (filters: satellite, subsystem, severity, status; search: description) |
| `/anomalies/add/` | Report anomaly (login required) |
| `/anomalies/<id>/` | Anomaly detail (view, add note, update status; note/status update requires login) |
| `/handbook/` | Alerts & Limits Handbook: list alerts (filters: subsystem, severity; search: parameter/description) |
| `/handbook/add/` | Add alert (login required) |
| `/handbook/<id>/` | Alert detail (read-only) |
| `/handbook/<id>/edit/` | Edit alert (login required); version incremented on save |
| `/handbook/<id>/delete/` | Confirm and delete alert (login required) |
| `/fdir/` | FDIR Handbook: list FDIR entries (filters: subsystem, severity, fault_type; search: name, conditions, response) |
| `/fdir/<id>/` | FDIR entry detail (read-only); links to operator procedures (procedure review) |
| `/fdir/add/` | Add FDIR entry (login required) |
| `/fdir/<id>/edit/` | Edit FDIR entry (login required) |

---

## Mission Scribe (scribe app)

- **Models:** `Role`, `EventCategory`, `ScribeTag`, `Shift`, `MissionLogEntry`. `MissionLogEntry` has FK to `procedures.Satellite` (shared fleet) and optional FK to `Shift`. Severity: Info, Warning, Critical.
- **Timeline** — Chronological list of `MissionLogEntry`; filter by role, satellite, category, severity, shift, tag; search on description.
- **Add entry** — Form: timestamp (default now), role, satellite, category, severity, description, optional shift and tags; `@login_required`; `created_by` = request.user.
- **Shifts** — Create shift (start_time, end_time, handoff_notes); shift detail shows entries in that shift and allows editing handoff notes.
- **Seed:** `python manage.py seed_scribe` creates default roles and event categories.

---

## Fleet Anomaly Tracker (anomalies app)

- **Models:** `Subsystem`, `AnomalyType`, `Anomaly`, `AnomalyNote`. `Anomaly` has FK to `procedures.Satellite`, optional FK to `Subsystem` and `AnomalyType`; severity (Low/Medium/High/Critical), status (New/Investigating/Mitigated/Resolved), operational_impact (choices), detection_time, description, reported_by (User). `AnomalyNote` is CASCADE on Anomaly; body, created_by.
- **Registry** — List anomalies; filter by satellite, subsystem, severity, status; search on description; session-persist filters; order by `-detection_time`; limit 200.
- **Report anomaly** — Form: satellite (required), subsystem, anomaly_type, severity, detection_time (default now), operational_impact, description; `@login_required`; reported_by = request.user; "Save and add another" option.
- **Anomaly detail** — View full anomaly; list notes (newest first); form to add note and/or update status (login required).
- **Seed:** `python manage.py seed_anomalies` creates default subsystems (Power, Thermal, C&DH, Comm, GNC, Payload, Ground) and anomaly types (Fault, Performance Degradation, Unexpected Behavior).

---

## Alerts & Limits Handbook (handbook app)

- **Models:** `Subsystem` (Power, ADCS, Thermal, Communications, Payload, Other); `AlertDefinition` — parameter, subsystem, description, alert_conditions, warning/critical thresholds (text), recommended_response, optional FK to `procedures.Procedure`, severity, version, created_at, updated_at.
- **List** — Filter by subsystem, severity; search on parameter and description; session-persist filters; limit 200.
- **Detail** — Full alert definition; link to linked procedure if set; Edit/Delete when logged in.
- **Create/Edit** — Form for all fields; on edit, version auto-incremented when content changes.
- **Seed:** `python manage.py seed_handbook` creates default subsystems; `seed_handbook --alerts` adds sample alert definitions.

---

## FDIR Handbook (fdir app)

- **Models:** `fdir.Subsystem` (name, slug); `FDIREntry` — name, fault_code, subsystem FK, severity, fault_type, triggering_conditions, detection_thresholds, onboard_automated_response, M2M to `procedures.Procedure` (operator_procedures), version, created_at, updated_at.
- **List** — Filter by subsystem, severity, fault_type; search on name, triggering_conditions, detection_thresholds, onboard_automated_response, fault_code; optional session-persist filters; limit 200.
- **Detail** — Full FDIR definition; operator procedures listed with links to procedure review; Edit when logged in.
- **Create/Edit** — Form for all fields; operator procedures as multi-select (checkboxes). Cross-link: FDIR entries reference Procedure; procedure review can later show “Referenced by FDIR” as an enhancement.
- **Seed:** `python manage.py seed_fdir` creates default subsystems (ADCS, Power, Thermal, Communications, Payload, Other); `seed_fdir --entries` adds sample FDIR entries.

---

## Data flow

1. **Procedure definition** — YAML under `procedures_yaml/`; `Procedure.yaml_file` points to it. `procedure_loader.load_procedure(name)` reads at runtime; create/edit/clone use `save_procedure()`.
2. **Start run** — POST on `/start/`: create `ProcedureRun`, redirect to `/run/<id>/?step=0`.
3. **Run steps** — GET shows current step (read-only if already executed). POST: create `StepExecution`, then next step or dashboard. Separate POST with `save_run_notes` updates `run_notes` only.
4. **Run notes** — Editable on run page; shown on run summary for handover/print.

---

## Security

- CSRF on all POST forms.
- `@login_required` on start and run; operator = `request.user`.
- Logout via POST form only (no GET logout).
- Admin is separate (staff/superuser).

---

## Running the app — three modes

There are three ways to run the application. Each uses the same codebase; the
only difference is which environment variables are set.

| Mode | Database | Server | When to use |
|------|----------|--------|-------------|
| **Bare Python** | SQLite (`ops.db`) | Django `runserver` | Quick local hacking, no Docker needed |
| **Docker Compose** | PostgreSQL 16 (container) | Gunicorn (container) | Testing the full production stack locally |
| **Fly.io** | Fly Postgres (managed) | Gunicorn (Fly Machine) | Production deployment |

---

### Deployment & configuration files

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds the app image: Python 3.12-slim, deps, collectstatic |
| `.dockerignore` | Keeps dev-only files out of the image |
| `docker-compose.yml` | Local stack: PostgreSQL + app, reads `.env` |
| `.env.example` | Annotated template — copy to `.env` for Docker Compose |
| `fly.toml` | Fly.io app config: region, VM size, env vars, HTTP routing |
| `entrypoint.sh` | Container startup: migrate → collectstatic → superuser → seed → Gunicorn |
| `Makefile` | Shortcuts for every common operation (see `make help`) |

---

### Environment variables — complete reference

| Variable | Default (no env) | Local Docker (`.env`) | Fly.io | Purpose |
|----------|-------------------|-----------------------|--------|---------|
| `DATABASE_URL` | *(unset → SQLite)* | `postgres://satops:satops@db:5432/satops` | *(auto-set by `fly postgres attach`)* | Database connection string. When set, Django uses PostgreSQL; when absent, falls back to SQLite. |
| `DJANGO_SECRET_KEY` | `dev-secret-change-in-production` | same default (fine locally) | **Set via `fly secrets set`** — must be a long random string | Django cryptographic signing key |
| `DJANGO_DEBUG` | `True` | `True` | `False` (set in `fly.toml`) | Enables debug pages and disables HTTPS security settings |
| `DJANGO_ALLOWED_HOSTS` | `*` | `*` | `.fly.dev` (set in `fly.toml`) | Comma-separated hostnames Django will serve |
| `CSRF_TRUSTED_ORIGINS` | *(empty)* | *(empty — not needed for HTTP localhost)* | `https://satops-procedures.fly.dev` (in `fly.toml`) | Required when behind HTTPS to allow POST requests |
| `SECURE_SSL_REDIRECT` | `True` when DEBUG=False | N/A (DEBUG=True) | `True` (default) or `False` if Fly handles redirect | HTTP → HTTPS redirect at Django level |
| `POSTGRES_DB` | — | `satops` | — | Used only by the `docker-compose` PostgreSQL container |
| `POSTGRES_USER` | — | `satops` | — | Used only by the `docker-compose` PostgreSQL container |
| `POSTGRES_PASSWORD` | — | `satops` | — | Used only by the `docker-compose` PostgreSQL container |
| `DJANGO_SUPERUSER_USERNAME` | *(unset)* | `admin` *(optional)* | Set via `fly secrets set` *(optional)* | If all three `SUPERUSER_*` vars are set, entrypoint auto-creates the account |
| `DJANGO_SUPERUSER_EMAIL` | *(unset)* | `admin@example.com` *(optional)* | Set via `fly secrets set` *(optional)* | Superuser email |
| `DJANGO_SUPERUSER_PASSWORD` | *(unset)* | `changeme` *(optional)* | Set via `fly secrets set` *(optional)* | Superuser password |
| `SEED_ON_STARTUP` | *(unset)* | `true` *(optional)* | *(unset — seed manually)* | If `true`, entrypoint runs `seed_all` on every container start |
| `GUNICORN_WORKERS` | `2` | `2` | `2` | Number of Gunicorn worker processes |

**How variables escalate from local → Docker → Fly.io:**

- **Bare Python** — zero env vars required. Everything has safe defaults (SQLite, DEBUG=True, SECRET_KEY placeholder, ALLOWED_HOSTS=*).
- **Docker Compose** — you add `DATABASE_URL` and the `POSTGRES_*` trio to switch to PostgreSQL. Optionally set `DJANGO_SUPERUSER_*` and `SEED_ON_STARTUP` for one-command bootstrapping.
- **Fly.io** — you add `DJANGO_DEBUG=False` (activates HTTPS security), a real `DJANGO_SECRET_KEY` (via secrets), `DJANGO_ALLOWED_HOSTS` restricted to your domain, and `CSRF_TRUSTED_ORIGINS` for HTTPS POST forms. `DATABASE_URL` is auto-injected by `fly postgres attach`.

---

### Mode 1 — Bare Python (SQLite, no Docker)

Fastest way to develop. No env vars needed.

```bash
cd satops_procedures/

# One-time setup
pip install -r requirements.txt   # or: make install
python manage.py migrate           # or: make migrate
python manage.py seed_all          # or: make seed
python manage.py createsuperuser   # or: make superuser

# Run
python manage.py runserver 0.0.0.0:8000   # or: make run
# → http://localhost:8000
```

Uses SQLite (`ops.db`), Django dev server, DEBUG=True. No static
collection needed — Django serves files directly in debug mode.

---

### Mode 2 — Docker Compose (PostgreSQL, mirrors production)

Tests the exact same container, database engine, and Gunicorn process that
will run on Fly.io — but entirely on your machine.

```bash
cd satops_procedures/

# 1. Create your .env from the template
cp .env.example .env

# 2. (Optional) Uncomment the DJANGO_SUPERUSER_* lines in .env
#    to auto-create an admin account on first boot.

# 3. (Optional) Add SEED_ON_STARTUP=true to .env
#    to populate sample data automatically.

# 4. Build and start
docker compose up --build          # or: make docker-up
# → http://localhost:8000

# Run in background instead:
docker compose up --build -d       # or: make docker-up-d
docker compose logs -f             # or: make docker-logs
```

#### Useful Docker commands

```bash
# Open a shell inside the running container
docker compose exec web bash              # or: make docker-shell

# Run any manage.py command
docker compose exec web python manage.py seed_all      # or: make docker-manage CMD="seed_all"
docker compose exec web python manage.py createsuperuser

# Connect to PostgreSQL directly
docker compose exec db psql -U satops -d satops         # or: make docker-psql

# Stop everything
docker compose down                # or: make docker-down

# Stop and wipe the database volume (full reset)
docker compose down -v             # or: make docker-down-v
```

#### What happens on `docker compose up`

1. PostgreSQL 16 container starts and waits to be healthy.
2. App container builds from `Dockerfile` (Python 3.12, deps, collectstatic).
3. `entrypoint.sh` runs:
   - `migrate` — applies all pending migrations to PostgreSQL.
   - `collectstatic` — gathers static files for WhiteNoise.
   - Creates superuser if `DJANGO_SUPERUSER_*` env vars are set.
   - Runs `seed_all` if `SEED_ON_STARTUP=true`.
   - Starts Gunicorn on port 8000.

#### Docker Compose `.env` — quick-start values

Copy `.env.example` and uncomment the lines you want:

```
DJANGO_SECRET_KEY=dev-secret-change-in-production
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=*
DATABASE_URL=postgres://satops:satops@db:5432/satops
POSTGRES_DB=satops
POSTGRES_USER=satops
POSTGRES_PASSWORD=satops
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=changeme
SEED_ON_STARTUP=true
```

---

### Mode 3 — Fly.io (production)

#### First deployment

```bash
cd satops_procedures/

# Create the Fly.io app (writes fly.toml app name)
fly launch --no-deploy

# Create a managed PostgreSQL cluster and attach it
# (this automatically sets DATABASE_URL as a Fly secret)
fly postgres create --name satops-db
fly postgres attach satops-db

# Set the Django secret key (long, random)
fly secrets set DJANGO_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"

# Deploy
fly deploy

# (Optional) Create a superuser interactively
fly ssh console -C "python manage.py createsuperuser"

# (Optional) Seed initial data
fly ssh console -C "python manage.py seed_all"
```

Or create the superuser automatically by setting secrets:

```bash
fly secrets set \
  DJANGO_SUPERUSER_USERNAME=admin \
  DJANGO_SUPERUSER_EMAIL=admin@example.com \
  DJANGO_SUPERUSER_PASSWORD=<strong-password>

fly deploy   # entrypoint.sh will create the account
```

#### Subsequent deployments

```bash
fly deploy                         # or: make fly-deploy
```

The entrypoint runs `migrate` on every deploy, so schema changes apply
automatically.

#### Fly.io operations

```bash
fly logs                           # or: make fly-logs
fly ssh console                    # or: make fly-ssh
fly ssh console -C "python manage.py seed_all"   # or: make fly-manage CMD="seed_all"
fly postgres connect -a satops-db  # or: make fly-psql
```

#### VM sizing

For ~10 users: `shared-cpu-1x`, 256 MB RAM (set in `fly.toml`).
To scale later:

```bash
fly scale vm shared-cpu-2x         # bigger machine
fly scale count 2                  # add a second machine
```

---

### Side-by-side comparison

| Concern | Bare Python | Docker Compose | Fly.io |
|---------|-------------|----------------|--------|
| Database | SQLite (`ops.db`) | PostgreSQL 16 (container) | Fly Postgres (managed) |
| Server | Django `runserver` | Gunicorn (2 workers) | Gunicorn (2 workers) |
| Static files | Django serves directly | WhiteNoise | WhiteNoise |
| DEBUG | True | True | **False** |
| HTTPS | No | No | **Yes** (forced by Fly) |
| Secret key | Placeholder | Placeholder | **Real secret** (Fly secrets) |
| ALLOWED_HOSTS | `*` | `*` | `.fly.dev` |
| CSRF origins | *(none)* | *(none)* | `https://satops-procedures.fly.dev` |
| SSL redirect | Disabled (DEBUG on) | Disabled (DEBUG on) | **Enabled** |
| Secure cookies | Disabled (DEBUG on) | Disabled (DEBUG on) | **Enabled** |
| Cost | Free | Free | ~$0/month (auto-stop) to ~$3/month |
| Start command | `make run` | `make docker-up` | `make fly-deploy` |

---

## CI/CD (GitHub Actions)

Two workflows in `.github/workflows/` automate linting, testing, and deployment.

### CI — runs on every push and pull request to `main`

**Workflow:** `.github/workflows/ci.yml`

| Step | What it does | Runs against |
|------|-------------|--------------|
| **Lint** | `ruff check .` — enforces code style, import ordering, catches bugs | Source files only |
| **Test** | `python manage.py test` — 56+ tests covering models, views, and seed commands | PostgreSQL 16 (service container) |
| **Django checks** | `python manage.py check` — validates models, URLs, settings | PostgreSQL 16 |
| **Deploy checks** | `python manage.py check --deploy` — warns about security settings | Informational (non-blocking) |

The test job runs against a real PostgreSQL service container, not SQLite,
so CI catches any database-specific issues before they reach production.

### CD — auto-deploys to Fly.io on push to `main`

**Workflow:** `.github/workflows/deploy.yml`

1. CI pipeline runs first (lint + test must pass).
2. If CI passes, the deploy job runs `flyctl deploy --remote-only`.
3. Fly.io builds the Docker image and rolls out the new version.

The `concurrency` setting ensures only one deployment runs at a time;
if a new push arrives while deploying, the in-progress deploy is cancelled.

### One-time setup for CD

Add a Fly.io API token to your GitHub repository secrets:

```bash
# Generate a token
fly tokens create deploy -x 999999h

# Add to GitHub → Settings → Secrets and variables → Actions → New repository secret
#   Name:  FLY_API_TOKEN
#   Value: <the token from above>
```

### Running CI locally

```bash
cd satops_procedures/
make ci          # runs: lint → check → test (all in one command)

# Or individually:
make lint        # ruff check .
make test        # python manage.py test
make check       # python manage.py check
```

### Linting

The project uses [Ruff](https://docs.astral.sh/ruff/) for linting and import sorting.
Configuration is in `ruff.toml`. Migrations are excluded.

```bash
make lint        # check for issues
make lint-fix    # auto-fix what's fixable
```

### Test suite

All tests live in one place: `satops_procedures/tests/`. One file per app:

| File | App | Tests |
|------|-----|-------|
| `test_procedures.py` | `procedures` | Models (Satellite, Tag, Procedure, ProcedureRun, StepExecution), views (dashboard, procedure list, history, start), seed commands |
| `test_scribe.py` | `scribe` | Models (Role, EventCategory, ScribeTag, Shift, MissionLogEntry), views (timeline, shift list), seed command |
| `test_anomalies.py` | `anomalies` | Models (Subsystem, AnomalyType, Anomaly, AnomalyNote), views (registry, add), seed command |
| `test_handbook.py` | `handbook` | Models (Subsystem, AlertDefinition + version auto-increment), views (alert list, create), seed command |
| `test_fdir.py` | `fdir` | Models (Subsystem + slug, FDIREntry), views (entry list, create), seed command |

```bash
make test                                  # run all 56 tests
python manage.py test tests.test_procedures  # run one file
python manage.py test tests                  # run everything in tests/
```

---

### Full pipeline flow

```
Developer pushes code
        │
        ▼
  ┌─────────────┐     ┌──────────────────┐     ┌────────────────┐
  │   Lint       │────▶│  Test (Postgres)  │────▶│ Django checks  │
  │  ruff check  │     │  56+ tests        │     │  manage.py     │
  └─────────────┘     └──────────────────┘     └────────────────┘
                                                        │
                              Push to main? ────────────┤
                              │ No (PR)                 │ Yes
                              ▼                         ▼
                           Done                ┌────────────────┐
                                               │ Deploy to Fly  │
                                               │ flyctl deploy  │
                                               └────────────────┘
```

---

For detailed layout, deployment, and offline use see `procedure_tool.wiki/Architecture.md`.
