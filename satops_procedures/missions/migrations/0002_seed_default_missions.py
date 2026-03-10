from django.db import migrations

DEFAULT_MISSIONS = [
    {
        'slug': 'simulation',
        'name': 'Simulation',
        'description': (
            'Simulation mission for training, testing, and '
            'demonstration of satellite operations workflows.'
        ),
        'color': '#8B5CF6',
        'is_sandbox': False,
        'is_active': True,
    },
    {
        'slug': 'sandbox',
        'name': 'Sandbox',
        'description': (
            'Sandbox environment for experimentation and learning. '
            'Feel free to create, edit, and delete anything here.'
        ),
        'color': '#F59E0B',
        'is_sandbox': True,
        'is_active': True,
    },
]


def create_default_missions(apps, schema_editor):
    Mission = apps.get_model('missions', 'Mission')
    for m in DEFAULT_MISSIONS:
        Mission.objects.get_or_create(slug=m['slug'], defaults=m)


def remove_default_missions(apps, schema_editor):
    Mission = apps.get_model('missions', 'Mission')
    Mission.objects.filter(slug__in=[m['slug'] for m in DEFAULT_MISSIONS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('missions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_missions, remove_default_missions),
    ]
