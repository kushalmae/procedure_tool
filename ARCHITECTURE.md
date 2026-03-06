# Procedure Tool — Architecture

Quick reference for the satops procedure runner (Django app).

## Tech stack

| Layer | Choice |
|-------|--------|
| Framework | Django (ORM, auth, templates) |
| Database | SQLite (`ops.db`) |
| Procedures | YAML files in `procedures_yaml/` (PyYAML) |
| Front end | Server-rendered HTML + CSS (no JS framework) |

Runs offline; optional gunicorn for production.

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
  procedure_tool.wiki/         # User guide, admin, architecture (long form)
  ARCHITECTURE.md               # This file
```

---

## Data model

- **Satellite** — name (fleet).
- **Tag** — name, slug; M2M with Procedure (filtering, search).
- **Procedure** — name, version, `yaml_file` (path under `procedures_yaml/`), tags.
- **ProcedureRun** — satellite, procedure, operator (FK User), start/end time, status (RUNNING/PASS/FAIL/CANCELLED), **run_notes** (handover/anomaly).
- **StepExecution** — run, step_id, description, status, input_value, notes, timestamp.

Procedure *definition* lives in YAML; runs and step results live in SQLite.

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

For detailed layout, deployment, and offline use see `procedure_tool.wiki/Architecture.md`.
