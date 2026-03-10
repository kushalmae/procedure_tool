from django.db import migrations


def create_simulation_mission(apps, schema_editor):
    Mission = apps.get_model('missions', 'Mission')
    Mission.objects.get_or_create(
        slug='simulation',
        defaults={
            'name': 'Simulation',
            'description': (
                'Simulation mission for training, testing, and '
                'demonstration of satellite operations workflows.'
            ),
            'color': '#8B5CF6',
            'is_sandbox': False,
            'is_active': True,
        },
    )


def remove_simulation_mission(apps, schema_editor):
    Mission = apps.get_model('missions', 'Mission')
    Mission.objects.filter(slug='simulation').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('missions', '0002_dashboardlayout'),
    ]

    operations = [
        migrations.RunPython(create_simulation_mission, remove_simulation_mission),
    ]
