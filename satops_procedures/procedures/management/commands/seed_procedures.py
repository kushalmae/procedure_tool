from django.core.management.base import BaseCommand
from procedures.models import Satellite, Procedure


class Command(BaseCommand):
    help = 'Seed initial Procedure (bus_checkout) and sample Satellites.'

    def handle(self, *args, **options):
        proc, created = Procedure.objects.get_or_create(
            yaml_file='bus_checkout',
            defaults={'name': 'Bus Checkout', 'version': '1.0'},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created procedure: {proc.name}'))
        else:
            self.stdout.write(f'Procedure already exists: {proc.name}')
        for name in ['SAT-021', 'SAT-034', 'SAT-012']:
            sat, created = Satellite.objects.get_or_create(name=name, defaults={'name': name})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created satellite: {sat.name}'))
        self.stdout.write(self.style.SUCCESS('Seed complete.'))
