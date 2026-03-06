# Procedure Tool — Product Overview

## What this product is

**Procedure Tool** is a satellite operations (satops) procedure runner: a web app that lets operators run step-by-step checklists against a fleet of satellites, record pass/fail and notes per step, and keep a searchable history of runs. Procedures are defined in YAML and can be created, edited, cloned, and reviewed in the UI. The app runs fully offline (no external APIs), uses SQLite and file-based YAML, and supports multiple users with login; the logged-in user is recorded as the operator for each run.

---

## Product description

Procedure Tool is built for **satellite operations teams** who need a simple, auditable way to execute and document procedures (e.g. bus checkout, payload init, orbit maneuvers, safehold). It provides **fleet context** (which satellite), **procedure context** (which checklist and version), and **run context** (who ran it, when, and what happened at each step).

The system keeps **procedure definitions** in human-editable YAML files and **run data** (runs, step results, timestamps, run notes) in a local database. Operators start a run by choosing a satellite and a procedure, then work through steps one at a time—recording pass/fail, optional inputs, and notes. Run notes support handover and anomaly documentation. Completed runs can be viewed as a summary and printed for records or shift handover.

The tool is **multi-user** and **offline-first**: no cloud dependency, suitable for lab or ops environments where connectivity is limited or data must stay on-premises. It fits teams that want versioned procedures, operator attribution, and searchable history without heavy infrastructure.

---

## Features

- **Fleet and procedures**
  - **Satellites** — Run procedures per satellite (e.g. SAT-021, SAT-034); satellites are created on first use or managed in Admin.
  - **Procedures** — Defined in YAML (name, version, ordered steps with optional inputs). Stored under `procedures_yaml/` and referenced in the database.
  - **Tags** — Procedures can have tags; filter by tag on the start page and on dashboard/history.

- **Procedure management (UI)**
  - **List** — View all procedures with step count and tags; **Review**, **Edit**, **Clone**, **Start**, **Delete** per procedure.
  - **Review** — Read all steps of a procedure before starting; optional “Start this procedure” from the review page.
  - **Create** — Add a new procedure (name, version, steps); creates both the YAML file and the database record.
  - **Edit** — Change name, version, or steps; updates the same YAML and procedure record.
  - **Clone** — Create “Copy of &lt;name&gt;” as a new procedure and YAML; then edit as needed.

- **Running procedures**
  - **Start run** — Pick satellite and procedure (login required); a new run is created and you are recorded as the operator.
  - **Step-by-step execution** — One step per screen: PASS/FAIL, optional input value, notes, automatic timestamp. Navigate back to previous steps (read-only).
  - **Run notes** — Add or edit handover/anomaly notes during the run; saved without advancing the step; shown on the run summary.
  - **Run summary** — View all steps and run notes in one page; print-friendly layout for records or handover.

- **History and search**
  - **Dashboard** — Recent runs; search by satellite, procedure, or operator; filter by tag; **Resume** for running procedures, **View / Print** for completed.
  - **History** — Full list of past runs with the same search and tag filter; open run summary for any run.

- **Accessibility and UX**
  - Skip link, ARIA labels, logical focus order, and print styles for step list and summary.
  - Breadcrumbs on run, summary, edit, and delete pages.

- **Security and users**
  - **Login** — Starting or running a procedure requires login; operator = logged-in user.
  - **Logout** — POST-only to avoid accidental logout via link.
  - **Admin** — Django Admin for satellites, procedures, runs, step executions, users, and tags (staff/superuser).

- **Deployment**
  - Runs offline (no external API calls). SQLite + YAML can live on a single server or shared drive. Optional gunicorn and reverse proxy for production.

---

## How it can be used

### Typical workflow

1. **Prepare procedures** — Create or edit procedures in the UI (or add YAML files and seed the database). Use tags (e.g. “checkout”, “maneuver”) for filtering.
2. **Review (optional)** — From the procedure list or start page, open **Review** to see all steps before starting.
3. **Start a run** — Log in, go to **Start Procedure** (or **Start** from the procedure list). Choose satellite and procedure; click **Start**. You are taken to step 1.
4. **Execute steps** — For each step: set PASS/FAIL, enter any required input and notes, click **Submit step**. Use **Previous** to view past steps (read-only). Add **Run notes** anytime (e.g. anomaly or handover); click **Save run notes**.
5. **Finish** — After the last step, the run is marked complete and you are redirected to the dashboard. Open **View all steps / Print** (or the run summary from dashboard/history) to see the full run and run notes and print if needed.
6. **Handover** — Use run notes and the printed summary to brief the next shift or document anomalies.

### Use cases

- **Bus checkout / payload init** — Run a fixed checklist per satellite, record results and timestamps, keep history for compliance or debugging.
- **Orbit maneuvers / thermal safehold** — Execute procedure steps in order, capture inputs (e.g. parameters) and notes; clone a procedure to create a variant (e.g. “Copy of Orbit Maneuver”) and edit.
- **Audit and traceability** — Search history by satellite, procedure, or operator; filter by tag; open any run summary for a full record with timestamps and run notes.
- **Multi-user ops** — Several operators use the same instance; each run is tied to the logged-in user; run notes support shift handover.

### Getting started

- **Install and run:** See `satops_procedures/README.md` (venv, `pip install`, `migrate`, `seed_procedures`, `runserver`).
- **First procedure:** Run `python manage.py seed_procedures` for a sample procedure and satellites, or create one via **Procedures** → **Create procedure**.
- **Users:** Create a superuser with `createsuperuser`; use the same account to log in at `/login/` and start/run procedures. Add more users in Django Admin if needed.

For detailed usage see the wiki: **User Guide**, **Procedures**, **Admin and Users**. For technical layout see **ARCHITECTURE.md** and the wiki **Architecture** page.

---

# Mission Operations Scribe Tool (Mission Scribe)

## What it is

**Mission Scribe** is a lightweight web application for satellite mission operations teams to record and share structured shift logs across multiple roles (e.g. Mission Director, Flight Dynamics, TNC, Payload, Ground Systems).

The tool lets operators log events during a shift with structured metadata (timestamp, role, satellite, event category, severity, tags) and a freeform description. All logs appear in a unified mission timeline. Users can filter by role, satellite, category, severity, or shift and search the log history. Shifts can have handoff notes for shift handover.

## Product description

Mission Scribe is designed for **mission operations** where multiple roles (Mission Director, FDS, TNC, Payload, Ground Systems) need to log events in one place. Each entry captures key fields plus a freeform note for operational context. The **unified mission timeline** gives program managers and operators a single chronological view of activity across all roles. Filters (role, satellite, category, severity, shift) and search make it easy to understand what happened when. **Shift-based logging** and **shift handoff notes** support shift handoff without adding operational overhead.

The MVP focuses on real-time shift logging, cross-role visibility, and shift handoff summaries.

## Core MVP features

- **Role-based event logging** — Log as Mission Director, Flight Dynamics, TNC, Payload, Ground Systems (and other roles configurable in Admin).
- **Structured event metadata + flexible note body** — Timestamp, role, satellite, category, severity, tags; freeform description.
- **Unified chronological mission timeline** — All entries in one list, ordered by time.
- **Filters** — By role, satellite, category, severity, and shift.
- **Shift-based logging and shift handoff notes** — Create shifts (start/end time); attach handoff notes; optionally associate log entries with a shift.
- **Searchable mission log history** — Text search on description; filter and search together.

## Key design principles

- **Structured + flexible** — Required structured fields (role, category, description) plus optional satellite, severity, tags, shift; one freeform body.
- **Minimal friction** — Default timestamp to now; dropdowns for role/category/satellite; single “Add entry” form; “Save and add another” option.
- **Single source of truth** — One mission log table; one timeline view with filters and search; shift handoff notes stored on the shift.

## How to use Mission Scribe

- **Timeline** — Open **Mission Scribe** in the nav. View all entries; use the filter form (role, satellite, category, severity, shift, tag) and search box; click **Filter** or **Clear**.
- **Add entry** — Click **Add entry** (requires login). Set timestamp (defaults to now), role, category, description; optionally satellite, severity, shift, tags. **Save entry** or **Save and add another**.
- **Shifts** — Click **Shifts** to list shifts. **Add shift** to create a shift (start time, end time, handoff notes). Open a shift to view handoff notes and entries in that shift; **Update handoff notes** to edit. When adding a log entry, you can assign it to a shift.
- **Seed data** — Run `python manage.py seed_scribe` to create default roles and event categories. Add Scribe tags in Django Admin (**/admin/scribe/scribetag/**) if needed.
