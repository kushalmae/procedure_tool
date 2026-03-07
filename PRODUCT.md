# Procedure Tool — Product Overview

## What this product is

**Procedure Tool** is a satellite operations (satops) procedure runner: a web app for operators to run step-by-step checklists against a fleet of satellites, record pass/fail and notes per step, and keep a searchable history of runs. Procedures are defined in YAML and can be created, edited, cloned, and reviewed in the UI. The app runs **offline** (no external APIs), uses SQLite/PostgreSQL and file-based YAML, and supports multi-user login with operator attribution.

---

## Key features

| Module | Purpose |
|--------|---------|
| **Procedure Runner** | YAML procedures, step-by-step execution, pass/fail, run notes, print summary |
| **Procedure Management** | List, review, create, edit, clone, delete procedures in the UI |
| **Mission Scribe** | Role-based shift logs, timeline, handoff notes |
| **Fleet Anomaly Tracker** | Report and track anomalies by satellite, subsystem, severity, status |
| **Alerts & Limits Handbook** | Alert definitions, thresholds, recommended responses |
| **FDIR Handbook** | Fault detection/isolation/recovery definitions, links to procedures |
| **Commands & Telemetry** | Command/telemetry definitions, filters, CSV import/export |
| **Central Reference Page** | Document links (ICD, manuals) by subsystem |
| **SME Request Workflow** | Request queue, approval, assignment, notes |

---

## Feature details

### Procedure Runner

Execute procedures step-by-step with clear pass/fail and optional inputs per step. Run notes capture handover context and anomalies without leaving the flow. Every run produces a print-friendly summary for records and audits. Full history is searchable by satellite, procedure, or operator.

### Procedure Management

Create, edit, and clone procedures in the UI—no YAML editing required unless you prefer it. Review all steps before starting. Tag procedures (e.g. checkout, maneuver) and filter from the dashboard. One place to manage your entire procedure library.

### Mission Scribe

Single timeline for all roles (Mission Director, FDS, TNC, Payload, Ground). Log events with role, category, severity, and freeform notes. Associate entries with shifts and maintain handoff notes so the next shift knows exactly where things stand.

### Fleet Anomaly Tracker

Report anomalies with satellite, subsystem, type, severity, and operational impact. Track status from New through Investigating to Mitigated or Resolved. Add notes over time for a clear audit trail. Filter and search the registry to see fleet health at a glance.

### Alerts & Limits Handbook

One source of truth for what each alert means, when it triggers, and how to respond. Define warning and critical thresholds, recommended actions, and optional links to recovery procedures. Filter by subsystem or severity so operators find the right guidance fast.

### FDIR Handbook

Document fault detection, onboard automated response, and which operator procedures to run. Link FDIR entries to procedures so recovery steps are one click away. Search and filter by subsystem, severity, or fault type for quick reference during ops.

### Commands & Telemetry

Central catalog of command and telemetry definitions with subsystem, category, and data types. Filter and search; import/export CSV to adapt to your ICD or integrate with other tools. Keeps ops and engineering aligned on the same definitions.

### Central Reference Page

Quick access to ICDs, manuals, and guides by subsystem. Add links and short notes so the team knows where to find the authoritative doc. Reduces “where’s that spec?” time during procedures and anomalies.

### SME Request Workflow

Queue requests (e.g. analysis, review) with satellite, type, priority, and status. Approve, assign, and add notes so nothing falls through the cracks. Visibility into what’s queued, in progress, and done.

---

## Product description

Procedure Tool is built for **satellite operations teams** who need a simple, auditable way to execute and document procedures (e.g. bus checkout, payload init, orbit maneuvers, safehold). It provides **fleet context** (which satellite), **procedure context** (which checklist and version), and **run context** (who ran it, when, and what happened at each step).

The system keeps **procedure definitions** in human-editable YAML files and **run data** (runs, step results, timestamps, run notes) in a local database. Operators start a run by choosing a satellite and a procedure, then work through steps one at a time—recording pass/fail, optional inputs, and notes. Run notes support handover and anomaly documentation. Completed runs can be viewed as a summary and printed for records or shift handover.

The tool is **multi-user** and **offline-first**: no cloud dependency, suitable for lab or ops environments where connectivity is limited or data must stay on-premises.

---

## Typical workflow

1. **Prepare procedures** — Create or edit in the UI, or add YAML and seed. Use tags (e.g. "checkout", "maneuver").
2. **Review (optional)** — Open **Review** to see all steps before starting.
3. **Start a run** — Log in, pick satellite and procedure, click **Start**.
4. **Execute steps** — PASS/FAIL per step, optional input/notes. Add **Run notes** anytime.
5. **Finish** — View summary, print for handover. Search history by satellite, procedure, or operator.

