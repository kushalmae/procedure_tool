"""
One-off fix for InconsistentMigrationHistory when anomalies.0001_initial
(or smerequests.0001_initial) was applied before procedures.0005_subsystem.

Removes those migration records from django_migrations so you can run
migrate; procedures.0005_subsystem will run first. Then re-mark the
dependent migrations as applied with --fake if their tables already exist.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Fix migration history when anomalies/smerequests were applied before procedures.0005_subsystem"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show what would be removed, do not change the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        to_remove = [
            ("anomalies", "0001_initial"),
            ("smerequests", "0001_initial"),
        ]
        with connection.cursor() as cursor:
            for app, name in to_remove:
                cursor.execute(
                    "SELECT 1 FROM django_migrations WHERE app = %s AND name = %s",
                    [app, name],
                )
                if cursor.fetchone():
                    if dry_run:
                        self.stdout.write(
                            self.style.WARNING(f"Would remove: {app}.{name}")
                        )
                    else:
                        cursor.execute(
                            "DELETE FROM django_migrations WHERE app = %s AND name = %s",
                            [app, name],
                        )
                        self.stdout.write(
                            self.style.SUCCESS(f"Removed migration record: {app}.{name}")
                        )
                else:
                    self.stdout.write(f"No record to remove for {app}.{name}")

        if not dry_run:
            self.stdout.write("")
            self.stdout.write(
                "Next, run:  python manage.py migrate"
            )
            self.stdout.write(
                "If you get 'table already exists' for anomalies or smerequests, run:"
            )
            self.stdout.write("  python manage.py migrate anomalies 0001_initial --fake")
            self.stdout.write("  python manage.py migrate smerequests 0001_initial --fake")
            self.stdout.write("  python manage.py migrate")
            self.stdout.write("")
