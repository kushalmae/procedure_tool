from django.core.management.base import BaseCommand

from missions.models import Mission
from smerequests.models import RequestType

DEFAULT_REQUEST_TYPES = [
    'Backorbit Data',
    'Telemetry Export',
    'Maneuver Reconstruction',
    'Pass Log / Contact Report',
    'Anomaly Data Package',
    'Post-Event Analysis',
    'General Data Request',
]


class Command(BaseCommand):
    help = 'Seed SME Request types for the SME Request Workflow.'

    def handle(self, *args, **options):
        mission = Mission.objects.filter(is_sandbox=False).first() or Mission.objects.first()

        for name in DEFAULT_REQUEST_TYPES:
            _, created = RequestType.objects.get_or_create(
                name=name, mission=mission, defaults={'name': name, 'mission': mission},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created request type: {name}'))

        self.stdout.write(self.style.SUCCESS('SME Request seed complete.'))
