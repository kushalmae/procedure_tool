# Rename detection_time -> detected_time and reported_by_id -> created_by_id
# for databases that still have the old column names.
# No-op on fresh DBs (from 0001) which already have detected_time, created_by_id.

from django.conf import settings
from django.db import migrations, models


def rename_old_columns(apps, schema_editor):
    from django.db import connection

    # Only run on SQLite; PostgreSQL 0001 already has correct column names
    if connection.vendor != 'sqlite':
        return

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(anomalies_anomaly)")
        cols = {row[1] for row in cursor.fetchall()}
        if "detection_time" in cols and "detected_time" not in cols:
            cursor.execute(
                "ALTER TABLE anomalies_anomaly RENAME COLUMN detection_time TO detected_time;"
            )
        if "reported_by_id" in cols and "created_by_id" not in cols:
            cursor.execute(
                "ALTER TABLE anomalies_anomaly RENAME COLUMN reported_by_id TO created_by_id;"
            )


def reverse_rename(apps, schema_editor):
    from django.db import connection

    if connection.vendor != 'sqlite':
        return

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(anomalies_anomaly)")
        cols = {row[1] for row in cursor.fetchall()}
        if "detected_time" in cols and "detection_time" not in cols:
            cursor.execute(
                "ALTER TABLE anomalies_anomaly RENAME COLUMN detected_time TO detection_time;"
            )
        if "created_by_id" in cols and "reported_by_id" not in cols:
            cursor.execute(
                "ALTER TABLE anomalies_anomaly RENAME COLUMN created_by_id TO reported_by_id;"
            )


class Migration(migrations.Migration):

    dependencies = [
        ("anomalies", "0002_align_schema_with_model"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(rename_old_columns, reverse_rename),
        # Remove db_column so model matches actual column names
        migrations.AlterField(
            model_name="anomaly",
            name="detected_time",
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name="anomaly",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="created_anomalies",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
