from django.core.management.base import BaseCommand
from scribe.models import Role, EventCategory


DEFAULT_ROLES = [
    'Mission Director',
    'Flight Dynamics',
    'TNC',
    'Payload',
    'Ground Systems',
]

DEFAULT_CATEGORIES = [
    'Nominal',
    'Anomaly',
    'Command',
    'Configuration',
]


class Command(BaseCommand):
    help = 'Seed Scribe Roles and EventCategories for Mission Scribe MVP.'

    def handle(self, *args, **options):
        for name in DEFAULT_ROLES:
            _, created = Role.objects.get_or_create(name=name, defaults={'name': name})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created role: {name}'))
        for name in DEFAULT_CATEGORIES:
            _, created = EventCategory.objects.get_or_create(name=name, defaults={'name': name})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {name}'))
        self.stdout.write(self.style.SUCCESS('Scribe seed complete.'))
