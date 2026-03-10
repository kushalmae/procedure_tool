"""
One-command local setup: migrate, collect static files, seed data, and
optionally create a superuser.

    python manage.py quickstart
    python manage.py quickstart --superuser admin
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Run migrate + collectstatic + seed_all in one step.  '
        'Use --superuser <username> to also create a superuser interactively.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--superuser',
            metavar='USERNAME',
            help='Create an interactive superuser with this username after seeding.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('==> Running migrations...'))
        call_command('migrate', '--noinput', verbosity=1)

        self.stdout.write(self.style.NOTICE('==> Collecting static files...'))
        call_command('collectstatic', '--noinput', verbosity=0)

        self.stdout.write(self.style.NOTICE('==> Seeding database...'))
        call_command('seed_all')

        if options.get('superuser'):
            from django.contrib.auth import get_user_model
            User = get_user_model()
            username = options['superuser']
            if User.objects.filter(username=username).exists():
                self.stdout.write(f'Superuser "{username}" already exists — skipping.')
            else:
                self.stdout.write(self.style.NOTICE(f'==> Creating superuser "{username}"...'))
                call_command('createsuperuser', '--username', username)

        self.stdout.write(self.style.SUCCESS(
            '\nAll done!  Run  python manage.py runserver  to start the app.'
        ))
