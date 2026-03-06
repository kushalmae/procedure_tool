# Satops Procedures (Django)

Satellite operations procedure tool: multi-user, fleet tracking, YAML procedures, SQLite, Django Admin. Runs offline.

## Setup

```bash
cd satops_procedures
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
# source .venv/Scripts/activate # Linux/macOS
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_all          # optional: seed everything (procedures, scribe, handbook, fdir, anomalies) in one go
# Or seed individually:
# python manage.py seed_procedures   # Bus Checkout procedure + sample satellites
# python manage.py seed_scribe      # Mission Scribe roles + event categories
# python manage.py seed_handbook     # Alerts & Limits Handbook (seed_all uses --alerts)
# python manage.py seed_fdir        # FDIR Handbook (seed_all uses --entries if applicable)
# python manage.py seed_anomalies   # Fleet Anomaly Tracker
python manage.py createsuperuser   # optional: for Django Admin
```

## Run

```bash
python manage.py runserver
```

Open http://localhost:8000 — Dashboard, Start Procedure, Run, History, Mission Scribe, Fleet Anomaly Tracker, Alerts & Limits Handbook, FDIR Handbook.

- **Admin**: http://localhost:8000/admin/ (Satellites, Procedures, Runs, Step Executions, Scribe, Anomalies, Handbook, FDIR)

## Admin and logging in

**Get to Admin:** With the server running, open **http://localhost:8000/admin/** in your browser.

**First-time login:** You need a staff/superuser account. Create one (once) with:

```bash
python manage.py createsuperuser
```

Enter username, email (optional), and password. Then log in at http://localhost:8000/admin/ with those credentials.

**Log in as a different user:**

1. **Add more users (Admin):** Log in as a superuser → go to **Authentication and Authorization** → **Users** → **Add user**. Set username and password, then check **Staff status** if they should use the admin site. Save and optionally edit the user to set more permissions or add to groups.
2. **Switch user:** In the admin, click **Log out** (top right), then go to http://localhost:8000/admin/ again and log in with another username/password.
3. **Two users at once:** Use a different browser or an incognito/private window and log in there with the second user.

### User login (main app)

**Starting or running a procedure requires login.** Anonymous users can view the dashboard, procedures, and history, but cannot start a new procedure or resume/run steps.

- **Log in:** Click **Log in** in the top-right, or go to **http://localhost:8000/login/**.
- Use the **same user accounts** as Admin (e.g. the superuser from `createsuperuser`, or users added under Admin → Users).
- After login you’ll see your **username** in the top-right and **Log out**.
- When you start a procedure, **you are automatically recorded as the operator** (no operator field); the start page shows “You will be recorded as *username*”.
- If you click **Start Procedure** or **Resume** while not logged in, you’ll be sent to the login page and then back to the page you wanted.

## Structure

- `satops/` — project settings and URLs
- `procedures/` — app: models, views, `services/` (procedure_loader, runner)
- `scribe/` — Mission Scribe app (timeline, shifts, log entries)
- `anomalies/` — Fleet Anomaly Tracker app (anomaly registry, report form, notes)
- `handbook/` — Alerts & Limits Handbook app (alert definitions, subsystems)
- `fdir/` — FDIR Handbook app (fault detection, isolation, recovery reference)
- `templates/` — dashboard, start, run, history, scribe, anomalies, handbook, fdir
- `procedures_yaml/` — YAML procedure definitions (e.g. `bus_checkout.yaml`)
