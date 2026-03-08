from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from missions.models import Mission, MissionMembership

User = get_user_model()

MISSIONS = [
    {
        'name': 'Alpha-1',
        'slug': 'alpha-1',
        'description': 'Primary satellite operations mission for the Alpha constellation.',
        'color': '#3B82F6',
        'is_sandbox': False,
    },
    {
        'name': 'Bravo-2',
        'slug': 'bravo-2',
        'description': 'Secondary mission for Bravo constellation monitoring and maneuvers.',
        'color': '#10B981',
        'is_sandbox': False,
    },
    {
        'name': 'Sandbox',
        'slug': 'sandbox',
        'description': 'Training and testing environment. Data here does not affect operations.',
        'color': '#F59E0B',
        'is_sandbox': True,
    },
]


class Command(BaseCommand):
    help = 'Seed three missions: Alpha-1, Bravo-2, and Sandbox.'

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
