from django.contrib.auth import get_user_model
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
        'description': 'Sandbox environment for experimentation and learning. Feel free to create, edit, and delete anything here.',
        'color': '#F59E0B',
        'is_sandbox': True,
    },
]


class Command(BaseCommand):
    help = 'Seed the default missions (Simulation and Sandbox).'

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

        self.stdout.write(self.style.SUCCESS('Mission seeding complete.'))
