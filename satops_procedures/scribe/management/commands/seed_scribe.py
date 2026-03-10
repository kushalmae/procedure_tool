from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

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

# (role_name, category_name, description, severity) for sample MissionLogEntry
SAMPLE_LOG_ENTRIES = [
    ('Mission Director', 'Nominal', 'Pass complete. No issues.', MissionLogEntry.SEVERITY_INFO),
    ('TNC', 'Nominal', 'Contact logged. AOS/LOS nominal.', MissionLogEntry.SEVERITY_INFO),
    ('Mission Director', 'Anomaly', 'Anomaly acknowledged. Under investigation.', MissionLogEntry.SEVERITY_WARNING),
    ('Flight Dynamics', 'Command', 'Orbit maneuver commanded; nominal execution.', MissionLogEntry.SEVERITY_INFO),
    ('Payload', 'Nominal', 'Payload activated; telemetry nominal.', MissionLogEntry.SEVERITY_INFO),
]


class Command(BaseCommand):
    help = 'Seed Scribe Roles, EventCategories, EntryTemplates, and optional sample Mission Log entries for Simulation and Sandbox.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--entries',
            action='store_true',
            help='Also create sample mission log entries so the Scribe timeline has content.',
        )

    def handle(self, *args, **options):
        missions = list(Mission.objects.filter(slug__in=['simulation', 'sandbox']).order_by('slug'))
        if not missions:
            m = Mission.objects.first()
            missions = [m] if m else []

        for mission in missions:
            self.stdout.write(self.style.NOTICE(f'Seeding Scribe for mission: {mission.name}'))
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

            if options.get('entries'):
                self._seed_log_entries(mission)

        self.stdout.write(self.style.SUCCESS('Scribe seed complete.'))

    def _seed_log_entries(self, mission):
        """Create sample MissionLogEntry for this mission so the timeline has content."""
        from procedures.models import Satellite

        now = timezone.now()
        role_by_name = {r.name: r for r in Role.objects.filter(mission=mission)}
        category_by_name = {c.name: c for c in EventCategory.objects.filter(mission=mission)}
        satellite = Satellite.objects.filter(mission=mission).first()

        for i, (role_name, cat_name, description, severity) in enumerate(SAMPLE_LOG_ENTRIES):
            role = role_by_name.get(role_name)
            category = category_by_name.get(cat_name)
            if not role or not category:
                continue
            ts = now - timedelta(hours=2 - i, minutes=15 * i)
            _, created = MissionLogEntry.objects.get_or_create(
                mission=mission,
                timestamp=ts,
                role=role,
                category=category,
                description=description,
                defaults={
                    'severity': severity,
                    'satellite': satellite,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  Created log entry: {description[:50]}…'))
