from django.test import TestCase
from django.urls import reverse

from handbook.models import AlertDefinition, Subsystem
from missions.models import Mission


class SubsystemModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_str(self):
        sub = Subsystem.objects.create(name="Thermal", mission=self.mission)
        self.assertEqual(str(sub), "Thermal")


class AlertDefinitionModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')
        self.sub = Subsystem.objects.create(name="Power", mission=self.mission)

    def test_str(self):
        alert = AlertDefinition.objects.create(
            parameter="BAT_TEMP",
            subsystem=self.sub,
            mission=self.mission,
            description="Battery temperature alert",
        )
        self.assertIn("BAT_TEMP", str(alert))

    def test_default_severity(self):
        alert = AlertDefinition.objects.create(
            parameter="V_BUS",
            subsystem=self.sub,
            mission=self.mission,
            description="Bus voltage",
        )
        self.assertEqual(alert.severity, AlertDefinition.SEVERITY_WARNING)

    def test_version_increments_on_change(self):
        alert = AlertDefinition.objects.create(
            parameter="V_BUS",
            subsystem=self.sub,
            mission=self.mission,
            description="Bus voltage",
        )
        self.assertEqual(alert.version, 1)
        alert.description = "Updated description"
        alert.save()
        alert.refresh_from_db()
        self.assertEqual(alert.version, 2)

    def test_version_unchanged_on_no_change(self):
        alert = AlertDefinition.objects.create(
            parameter="V_BUS",
            subsystem=self.sub,
            mission=self.mission,
            description="Bus voltage",
        )
        alert.save()
        alert.refresh_from_db()
        self.assertEqual(alert.version, 1)


class AlertListViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_alert_list_loads(self):
        response = self.client.get(
            reverse("handbook_alert_list", kwargs={"mission_slug": self.mission.slug})
        )
        self.assertEqual(response.status_code, 200)

    def test_alert_list_with_search(self):
        response = self.client.get(
            reverse("handbook_alert_list", kwargs={"mission_slug": self.mission.slug}),
            {"q": "battery"},
        )
        self.assertEqual(response.status_code, 200)


class AlertCreateViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_create_requires_login(self):
        response = self.client.get(
            reverse("handbook_alert_create", kwargs={"mission_slug": self.mission.slug})
        )
        self.assertEqual(response.status_code, 302)


class SeedHandbookCommandTest(TestCase):
    def test_seed_handbook(self):
        from django.core.management import call_command

        call_command("seed_handbook")
        self.assertTrue(Subsystem.objects.exists())

    def test_seed_handbook_with_alerts(self):
        from django.core.management import call_command

        call_command("seed_handbook", alerts=True)
        self.assertTrue(AlertDefinition.objects.exists())
