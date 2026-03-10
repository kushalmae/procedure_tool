# Add operational_impact to Anomaly. Column may already exist on some DBs (legacy schema).

from django.db import migrations, models


def add_operational_impact_if_missing(apps, schema_editor):
    from django.db import connection

    if connection.vendor != 'sqlite':
        return
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(anomalies_anomaly)")
        cols = {row[1] for row in cursor.fetchall()}
        if "operational_impact" not in cols:
            cursor.execute(
                "ALTER TABLE anomalies_anomaly ADD COLUMN operational_impact VARCHAR(100) NOT NULL DEFAULT '';"
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('anomalies', '0004_anomaly_mission'),
    ]

    operations = [
        migrations.RunPython(add_operational_impact_if_missing, noop_reverse),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='anomaly',
                    name='operational_impact',
                    field=models.CharField(
                        blank=True,
                        default='',
                        help_text='Short description of operational impact (e.g. None, Low, Mission delay).',
                        max_length=100,
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
