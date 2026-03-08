from django.core.management.base import BaseCommand

from missions.models import Mission
from scribe.models import EntryTemplate, EventCategory, MissionLogEntry, Role

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

# (name, category_name, role_name, default_description, display_order)
DEFAULT_ENTRY_TEMPLATES = [
    ('Pass complete', 'Nominal', 'Mission Director', 'Pass complete. No issues.', 0),
    ('Contact logged', 'Nominal', 'TNC', 'Contact logged. AOS/LOS nominal.', 1),
    ('Anomaly acknowledged', 'Anomaly', 'Mission Director', 'Anomaly acknowledged. Under investigation.', 2),
    ('Configuration change', 'Configuration', None, 'Configuration change as planned.', 3),
]


class Command(BaseCommand):
    help = 'Seed Scribe Roles, EventCategories, and EntryTemplates for Mission Scribe MVP.'

    def handle(self, *args, **options):
        mission = Mission.objects.filter(is_sandbox=False).first() or Mission.objects.first()

        for name in DEFAULT_ROLES:
            _, created = Role.objects.get_or_create(
                name=name, mission=mission, defaults={'name': name, 'mission': mission}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created role: {name}'))
        for name in DEFAULT_CATEGORIES:
            _, created = EventCategory.objects.get_or_create(
                name=name, mission=mission, defaults={'name': name, 'mission': mission}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {name}'))

        for name, cat_name, role_name, desc, order in DEFAULT_ENTRY_TEMPLATES:
            category = EventCategory.objects.filter(name=cat_name, mission=mission).first()
            role = Role.objects.filter(name=role_name, mission=mission).first() if role_name else None
            _, created = EntryTemplate.objects.get_or_create(
                name=name,
                mission=mission,
                defaults={
                    'category': category,
                    'role': role,
                    'default_description': desc,
                    'display_order': order,
                    'default_severity': MissionLogEntry.SEVERITY_INFO,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created entry template: {name}'))

        self.stdout.write(self.style.SUCCESS('Scribe seed complete.'))
