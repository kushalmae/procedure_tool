"""
Single entry point to run all seed commands for the satops project.
Run: python manage.py seed_all
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand

# Order matters: procedures first (satellites), then others. All use "full" sample data flags.
# seed_missions with missions_only=True so we only create the two missions; we run the rest here.
SEED_COMMANDS = [
    ('seed_missions', {'missions_only': True}, 'Simulation and Sandbox missions'),
    ('seed_procedures', {}, 'Procedures, tags, satellites'),
    ('seed_scribe', {'entries': True}, 'Scribe roles, categories, templates, sample log entries'),
    ('seed_handbook', {'alerts': True}, 'Handbook subsystems and sample alerts'),
    ('seed_fdir', {'entries': True}, 'FDIR subsystems and sample entries'),
    ('seed_anomalies', {}, 'Anomaly tracker sample anomalies'),
    ('seed_references', {}, 'Central Reference Page subsystems and sample references'),
    ('seed_cmdtlm', {}, 'Command & Telemetry reference definitions'),
    ('seed_smerequests', {}, 'SME Request types'),
]


class Command(BaseCommand):
    help = 'Run all seed commands (procedures, scribe, handbook, fdir, anomalies, references, cmdtlm, smerequests) in one go.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only list which seed commands would be run.',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        if dry_run:
            self.stdout.write('Would run:')
            for cmd_name, _cmd_kwargs, desc in SEED_COMMANDS:
                self.stdout.write(f'  {cmd_name}  ({desc})')
            return

        for cmd_name, cmd_kwargs, _desc in SEED_COMMANDS:
            try:
                self.stdout.write(self.style.NOTICE(f'Running {cmd_name}...'))
                call_command(cmd_name, **cmd_kwargs)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Skipped {cmd_name}: {e}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'  Done: {cmd_name}'))

        self.stdout.write(self.style.SUCCESS('All seeds complete.'))
