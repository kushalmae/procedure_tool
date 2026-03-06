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

For detailed layout, deployment, and offline use see `procedure_tool.wiki/Architecture.md`.
