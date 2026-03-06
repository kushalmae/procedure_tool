from django.core.management.base import BaseCommand
from procedures.models import Satellite, Tag, Procedure


PROCEDURES = [
    {'yaml_file': 'bus_checkout', 'name': 'Bus Checkout', 'version': '1.0', 'tags': ['checkout', 'bus']},
    {'yaml_file': 'payload_init', 'name': 'Payload Initialization', 'version': '2.1', 'tags': ['payload', 'commissioning']},
    {'yaml_file': 'thermal_safehold', 'name': 'Thermal Safehold Procedure', 'version': '1.2', 'tags': ['thermal', 'safehold']},
    {'yaml_file': 'orbit_maneuver', 'name': 'Orbit Correction Maneuver', 'version': '3.0', 'tags': ['orbit', 'maneuver', 'propulsion']},
]


class Command(BaseCommand):
    help = 'Seed Procedures, Tags, and sample Satellites.'

    def handle(self, *args, **options):
        for p in PROCEDURES:
            proc, created = Procedure.objects.get_or_create(
                yaml_file=p['yaml_file'],
                defaults={'name': p['name'], 'version': p['version']},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created procedure: {proc.name}'))
            else:
                self.stdout.write(f'Procedure already exists: {proc.name}')
            for tag_name in p.get('tags', []):
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                proc.tags.add(tag)
        for name in ['SAT-021', 'SAT-034', 'SAT-012']:
            sat, created = Satellite.objects.get_or_create(name=name, defaults={'name': name})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created satellite: {sat.name}'))
        self.stdout.write(self.style.SUCCESS('Seed complete.'))
