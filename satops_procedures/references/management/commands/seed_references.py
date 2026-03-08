from django.core.management.base import BaseCommand

from missions.models import Mission
from references.models import ReferenceEntry, Subsystem

DEFAULT_SUBSYSTEMS = [
    'ADCS',
    'Communications',
    'Payload',
    'Power',
    'Thermal',
    'Other',
]

SAMPLE_REFERENCES = [
    {
        'title': 'ADCS ICD',
        'document_type': 'ICD',
        'subsystem': 'ADCS',
        'section': 'Command Interface',
        'version': 'v2.1',
        'location': 'https://sharepoint.example.com/docs/adcs-icd',
        'user_notes': 'Check section 4.2 for reset commands',
    },
    {
        'title': 'ADCS Modes & Transitions',
        'document_type': 'Reference',
        'subsystem': 'ADCS',
        'section': 'Mode Transitions',
        'version': 'v2.1',
        'location': 'https://sharepoint.example.com/docs/adcs-icd#modes',
        'user_notes': 'Key reference for safehold recovery',
    },
    {
        'title': 'Power User Manual',
        'document_type': 'Manual',
        'subsystem': 'Power',
        'section': 'Battery Ops',
        'version': 'v1.4',
        'location': 'https://drive.example.com/power-manual.pdf',
        'user_notes': 'Important limits near eclipse season',
    },
    {
        'title': 'Power Subsystem ICD',
        'document_type': 'ICD',
        'subsystem': 'Power',
        'section': 'Telemetry Definitions',
        'version': 'v3.0',
        'location': 'https://sharepoint.example.com/docs/power-icd',
        'user_notes': '',
    },
    {
        'title': 'Comm Troubleshooting Guide',
        'document_type': 'Guide',
        'subsystem': 'Communications',
        'section': 'RF Dropouts',
        'version': 'v3.0',
        'location': 'https://git.example.com/ops/comm-troubleshooting',
        'user_notes': 'Useful during contact issues',
    },
    {
        'title': 'Comm ICD',
        'document_type': 'ICD',
        'subsystem': 'Communications',
        'section': 'Command & Telemetry',
        'version': 'v2.5',
        'location': 'https://sharepoint.example.com/docs/comm-icd',
        'user_notes': 'Packet format updated in v2.5',
    },
    {
        'title': 'Payload ICD',
        'document_type': 'ICD',
        'subsystem': 'Payload',
        'section': 'Telemetry Mapping',
        'version': 'v1.8',
        'location': 'https://internal-docs.example.com/payload-icd',
        'user_notes': 'Verify packet format',
    },
    {
        'title': 'Payload Operator Guide',
        'document_type': 'Guide',
        'subsystem': 'Payload',
        'section': 'Data Collection',
        'version': 'v1.2',
        'location': 'https://drive.example.com/payload-ops-guide.pdf',
        'user_notes': 'Covers nominal and contingency data collection modes',
    },
    {
        'title': 'Thermal Control Reference',
        'document_type': 'Reference',
        'subsystem': 'Thermal',
        'section': 'Heater Logic',
        'version': 'v1.1',
        'location': 'https://sharepoint.example.com/docs/thermal-ref',
        'user_notes': 'Heater duty cycles and setpoints',
    },
    {
        'title': 'FDIR Summary Document',
        'document_type': 'Reference',
        'subsystem': 'Other',
        'section': 'All Subsystems',
        'version': 'v2.0',
        'location': 'https://git.example.com/ops/fdir-summary',
        'user_notes': 'Master FDIR reference across all subsystems',
    },
    {
        'title': 'Spacecraft User Manual',
        'document_type': 'Manual',
        'subsystem': 'Other',
        'section': '',
        'version': 'v4.0',
        'location': 'https://drive.example.com/sc-user-manual.pdf',
        'user_notes': 'Primary spacecraft reference for operations',
    },
    {
        'title': 'Alerts & Limits Database',
        'document_type': 'Reference',
        'subsystem': 'Other',
        'section': 'All Parameters',
        'version': 'v1.0',
        'location': 'https://satops.example.com/handbook/',
        'user_notes': 'Links to internal SatOps alerts handbook',
    },
]


class Command(BaseCommand):
    help = 'Seed Central Reference Page with subsystems and sample reference entries.'

    def handle(self, *args, **options):
        mission = Mission.objects.filter(slug='simulation').first() or Mission.objects.first()

        for name in DEFAULT_SUBSYSTEMS:
            _, created = Subsystem.objects.get_or_create(
                name=name, mission=mission, defaults={'name': name, 'mission': mission}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created subsystem: {name}'))

        for data in SAMPLE_REFERENCES:
            subsystem = Subsystem.objects.get(name=data['subsystem'], mission=mission)
            _, created = ReferenceEntry.objects.get_or_create(
                title=data['title'],
                subsystem=subsystem,
                mission=mission,
                defaults={
                    'document_type': data['document_type'],
                    'section': data['section'],
                    'version': data['version'],
                    'location': data['location'],
                    'user_notes': data['user_notes'],
                    'mission': mission,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created reference: {data["title"]}'))

        self.stdout.write(self.style.SUCCESS('Reference seed complete.'))
