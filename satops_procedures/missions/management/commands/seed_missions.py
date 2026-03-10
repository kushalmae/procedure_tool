from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from missions.models import Mission, MissionMembership

User = get_user_model()

MISSIONS = [
    {
        'name': 'Simulation',
        'slug': 'simulation',
        'description': 'Simulation mission for training, testing, and demonstration of satellite operations workflows.',
        'color': '#8B5CF6',
        'is_sandbox': False,
    },
    {
        'name': 'Sandbox',
        'slug': 'sandbox',
        'description': 'Sandbox mission for testing and exploration. Seeded with the same sample data as Simulation.',
        'color': '#10B981',
        'is_sandbox': True,
    },
]

# Same order and flags as procedures.management.commands.seed_all (minus seed_missions).
SEED_ALL_SCREENS = [
    ('seed_procedures', {}),
    ('seed_scribe', {'entries': True}),
    ('seed_handbook', {'alerts': True}),
    ('seed_fdir', {'entries': True}),
    ('seed_anomalies', {}),
    ('seed_references', {}),
    ('seed_cmdtlm', {}),
    ('seed_smerequests', {}),
]


class Command(BaseCommand):
    help = 'Seed Simulation and Sandbox missions and all screen data (procedures, scribe, handbook, fdir, anomalies, references, cmdtlm, smerequests). Use --missions-only to only create the two missions.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--missions-only',
            action='store_true',
            help='Only create Simulation and Sandbox missions; do not run seed commands for screens.',
        )

    def handle(self, *args, **options):
        for m_data in MISSIONS:
            mission, created = Mission.objects.get_or_create(
                slug=m_data['slug'],
                defaults=m_data,
            )
            action = 'Created' if created else 'Already exists'
            self.stdout.write(f'  {action}: {mission.name}')

        for user in User.objects.filter(is_superuser=False):
            for mission in Mission.objects.all():
                _, created = MissionMembership.objects.get_or_create(
                    user=user,
                    mission=mission,
                    defaults={'role': MissionMembership.ROLE_OPERATOR},
                )
                if created:
                    self.stdout.write(f'  Added {user.username} to {mission.name} as Operator')

        if not options.get('missions_only'):
            self.stdout.write(self.style.NOTICE('Seeding all screens for Simulation and Sandbox missions...'))
            for cmd_name, cmd_kwargs in SEED_ALL_SCREENS:
                try:
                    self.stdout.write(self.style.NOTICE(f'  Running {cmd_name}...'))
                    call_command(cmd_name, **cmd_kwargs)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Skipped {cmd_name}: {e}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'  Done: {cmd_name}'))

        self.stdout.write(self.style.SUCCESS('Mission seeding complete.'))
