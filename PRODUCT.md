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

---

# Fleet Anomaly Tracker

## What it is

**Fleet Anomaly Tracker** is a lightweight web application for capturing, tracking, and managing anomalies across a fleet of satellites. It provides a centralized place for operators and engineers to record operational issues, unexpected behaviors, and system faults using structured forms.

The tool standardizes anomaly reporting by capturing key metadata (satellite, subsystem, anomaly type, severity, detection time, operational impact) and allows flexible notes. Each record is part of a centralized anomaly registry so mission teams can view active issues, monitor fleet health, and track investigation progress.

## Core MVP features

- **Structured anomaly reporting** — Report form with satellite (required), subsystem, anomaly type, severity, detection time, operational impact, and description.
- **Satellite and subsystem tagging** — Filter and display by satellite and subsystem (configurable in Admin).
- **Severity and impact classification** — Severity: Low, Medium, High, Critical; operational impact: None, Minor, Moderate, Major, Mission-Critical.
- **Centralized anomaly registry** — Fleet-wide list with filters (satellite, subsystem, severity, status) and search on description.
- **Status tracking** — New, Investigating, Mitigated, Resolved; update status from anomaly detail.
- **Notes and updates** — Attach operational notes to an anomaly; notes listed on detail page with timestamp and author.

## How to use Fleet Anomaly Tracker

- **Registry** — Open **Fleet Anomaly Tracker** in the nav. View all anomalies; use the filter form (satellite, subsystem, severity, status) and search box (description); click **Filter** or **Clear filters**. Click an anomaly row to open detail.
- **Report anomaly** — Click **Report anomaly** (requires login). Fill satellite (required), optionally subsystem, anomaly type, severity, detection time (defaults to now), operational impact, description. **Save** or **Save and add another**.
- **Anomaly detail** — View full metadata and description; see notes and updates; when logged in, add a note and/or change status and click **Save**.
- **Seed data** — Run `python manage.py seed_anomalies` to create default subsystems and anomaly types. Run `python manage.py seed_anomalies --anomalies` to also add sample anomalies (and notes) across SAT-021, SAT-034, SAT-012 so you can try the registry and detail views. Manage in Django Admin (**/admin/anomalies/**) if needed.

---

# Alerts & Limits Handbook

## What it is

**Alerts & Limits Handbook** is a centralized web application that documents and organizes operational alerts, monitoring rules, and telemetry limits used across the fleet. It provides a single source of truth for alert conditions, telemetry thresholds, and recommended operator response when limits are exceeded.

Each alert entry captures the monitored parameter, subsystem, alert conditions, warning and critical thresholds, and recommended actions. The handbook helps mission operations teams quickly understand what an alert means, why it triggers, and how to respond.

## Core features

- **Structured alert and limit definitions** — Parameter, subsystem (Power, ADCS, Thermal, Communications, Payload, etc.), description (meaning and operational impact), alert conditions, warning/critical thresholds (text, e.g. "> 45 C"), recommended response, optional link to a procedure.
- **Search and filtering** — Filter by subsystem or severity; search by parameter or description. Filters persist in session.
- **Version tracking** — Each alert has a version number and last-updated timestamp; version increments when the definition is edited.
- **Create, edit, delete** — Logged-in users can add, edit, and delete alert definitions; list and detail are viewable by all.

## How to use the Handbook

- **List** — Open **Alerts & Limits Handbook** in the nav. View all alerts; use the filter form (subsystem, severity) and search box (parameter or description); click **Filter** or **Clear filters**.
- **Detail** — Click an alert parameter or **View** to see the full definition, thresholds, recommended response, and linked procedure (if any).
- **Add alert** — Click **Add alert** (requires login). Fill parameter, subsystem, description; optionally alert conditions, warning/critical thresholds, recommended response, linked procedure, severity. Save.
- **Edit / Delete** — From the list or detail, use **Edit** or **Delete** (login required). Edits increment the alert version.
- **Seed data** — Run `python manage.py seed_handbook` to create default subsystems (Power, ADCS, Thermal, Communications, Payload, Other). Run `python manage.py seed_handbook --alerts` to add sample alert definitions. Manage subsystems and alerts in Django Admin (**/admin/handbook/**) if needed.

---

# FDIR Handbook

## What it is

**FDIR Handbook** is a centralized web application that documents and organizes all Fault Detection, Isolation, and Recovery (FDIR) logic for a fleet of satellites. The system provides a single source of truth describing how faults are detected onboard, what automatic responses are executed by the spacecraft, and what operational procedures operators should follow if additional intervention is required.

Each FDIR entry captures structured information including the fault name, subsystem, triggering conditions, detection thresholds, and associated responses. The handbook clearly distinguishes between onboard automated responses executed by flight software and ground operational procedures that operators should reference during recovery or investigation.

## Core MVP features

- **Structured FDIR definitions** — Fault name, optional fault code, subsystem (ADCS, Power, Thermal, Communications, Payload, Other), severity (Info, Warning, Critical), optional fault type, triggering conditions, detection thresholds, onboard automated response (text), and optional version string.
- **Documentation of onboard automated responses** — Each entry has a dedicated field for what the spacecraft does automatically when the fault is detected.
- **References to operator recovery procedures** — M2M link to Procedure; one FDIR entry can reference multiple procedures; procedures can be linked from the create/edit form and shown on the detail page with links to procedure review.
- **Subsystem tagging** — Filter and display by subsystem; subsystems are seedable and manageable in Admin.
- **Search and filtering** — Filter by subsystem, severity, and fault type; full-text search on fault name, triggering conditions, detection thresholds, onboard response, and fault code. Filters can be cleared; optional session persistence.
- **Cross-links** — From FDIR detail, linked procedures are listed with links to procedure review. List and detail are viewable by all; create and edit require login.
- **Version tracking** — Optional version field and last-updated timestamp on each entry.

## Key design principles

- **Single source of truth** for FDIR logic; procedure definitions remain in YAML; FDIR stores only references.
- **Clear separation** between onboard automated response (text on FDIR) and operator procedures (links to Procedure).
- **Fleet-wide** — FDIR entries are not tied to a specific satellite in the MVP.

## How to use FDIR Handbook

- **List** — Open **FDIR Handbook** in the nav. View all FDIR entries; use the filter form (subsystem, severity, fault type) and search box (fault name, conditions, response); click **Filter** or **Clear filters**.
- **Detail** — Click a fault name or **View** to see the full definition, triggering conditions, thresholds, onboard automated response, and linked operator procedures (with links to procedure review).
- **Add entry** — Click **Add FDIR entry** (requires login). Fill fault name and subsystem; optionally fault code, severity, fault type, triggering conditions, detection thresholds, onboard automated response, operator procedures (multi-select), and version. Save.
- **Edit** — From the list or detail, use **Edit** (login required). Save updates last-updated timestamp.
- **Seed data** — Run `python manage.py seed_fdir` to create default subsystems (ADCS, Power, Thermal, Communications, Payload, Other). Run `python manage.py seed_fdir --entries` to add sample FDIR entries. Manage subsystems and FDIR entries in Django Admin (**/admin/fdir/**) if needed.
