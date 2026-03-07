# Migration to align old anomalies_anomaly schema with current model.
# Old DB had: detection_time, reported_by_id, operational_impact, etc.
# Fresh DB (from 0001) has: title, detected_time, created_by_id, etc.
# This migration: adds missing columns, renames columns on old schema, creates timeline table.

from django.conf import settings
from django.db import migrations, models


def _get_columns(cursor, table):
    cursor.execute("PRAGMA table_info(%s)" % table)
    return {row[1] for row in cursor.fetchall()}


def add_missing_columns_and_rename(apps, schema_editor):
    from django.db import connection

    with connection.cursor() as cursor:
        cols = _get_columns(cursor, "anomalies_anomaly")

        # Add missing columns on old schema
        if "title" not in cols:
            cursor.execute(
                "ALTER TABLE anomalies_anomaly ADD COLUMN title VARCHAR(200) NOT NULL DEFAULT 'Untitled';"
            )
            cursor.execute(
                """UPDATE anomalies_anomaly SET title = SUBSTR(description, 1, 200)
                   WHERE description IS NOT NULL AND description != '';"""
            )
        if "root_cause" not in cols:
            cursor.execute(
                "ALTER TABLE anomalies_anomaly ADD COLUMN root_cause TEXT NOT NULL DEFAULT '';"
            )
        if "resolution_actions" not in cols:
            cursor.execute(
                "ALTER TABLE anomalies_anomaly ADD COLUMN resolution_actions TEXT NOT NULL DEFAULT '';"
            )
        if "recommendations" not in cols:
            cursor.execute(
                "ALTER TABLE anomalies_anomaly ADD COLUMN recommendations TEXT NOT NULL DEFAULT '';"
            )

        # Rename old-schema columns to match model (SQLite 3.25.2+)
        if "detection_time" in cols and "detected_time" not in cols:
            cursor.execute(
                "ALTER TABLE anomalies_anomaly RENAME COLUMN detection_time TO detected_time;"
            )
        if "reported_by_id" in cols and "created_by_id" not in cols:
            cursor.execute(
                "ALTER TABLE anomalies_anomaly RENAME COLUMN reported_by_id TO created_by_id;"
            )

        # Create timeline table if missing
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='anomalies_anomalytimelineentry'"
        )
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE anomalies_anomalytimelineentry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    entry_type VARCHAR(20) NOT NULL DEFAULT 'NOTE',
                    body TEXT NOT NULL,
                    old_value VARCHAR(50) NOT NULL DEFAULT '',
                    new_value VARCHAR(50) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    anomaly_id BIGINT NOT NULL REFERENCES anomalies_anomaly(id) ON DELETE CASCADE,
                    created_by_id INTEGER NULL REFERENCES auth_user(id) ON DELETE SET NULL
                )
            """)


class Migration(migrations.Migration):

    dependencies = [
        ("anomalies", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(add_missing_columns_and_rename, migrations.RunPython.noop),
    ]
