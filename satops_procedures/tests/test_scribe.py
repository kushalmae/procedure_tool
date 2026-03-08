from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from missions.models import Mission
from scribe.models import EventCategory, MissionLogEntry, Role, ScribeTag, Shift


class RoleModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_str(self):
        role = Role.objects.create(name="Flight Controller", mission=self.mission)
        self.assertEqual(str(role), "Flight Controller")


class EventCategoryModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_str(self):
        cat = EventCategory.objects.create(name="Telemetry", mission=self.mission)
        self.assertEqual(str(cat), "Telemetry")


class ScribeTagModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_slug_auto_generated(self):
        tag = ScribeTag.objects.create(name="High Priority", mission=self.mission)
        self.assertEqual(tag.slug, "high-priority")


class ShiftModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_str(self):
        now = timezone.now()
        shift = Shift.objects.create(
            start_time=now, end_time=now, mission=self.mission
        )
        self.assertIn(str(now.year), str(shift))


class MissionLogEntryModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')
        self.role = Role.objects.create(name="Ops", mission=self.mission)
        self.cat = EventCategory.objects.create(name="Event", mission=self.mission)

    def test_create_entry(self):
        entry = MissionLogEntry.objects.create(
            timestamp=timezone.now(),
            role=self.role,
            category=self.cat,
            severity=MissionLogEntry.SEVERITY_INFO,
            description="Test entry",
            mission=self.mission,
        )
        self.assertEqual(entry.severity, "INFO")

    def test_default_severity(self):
        entry = MissionLogEntry.objects.create(
            timestamp=timezone.now(),
            role=self.role,
            category=self.cat,
            description="Test",
            mission=self.mission,
        )
        self.assertEqual(entry.severity, MissionLogEntry.SEVERITY_INFO)


class ScribeTimelineViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_timeline_loads(self):
        response = self.client.get(
            reverse("scribe_timeline", kwargs={"mission_slug": "test"})
        )
        self.assertEqual(response.status_code, 200)


class ScribeAddEntryViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_add_entry_requires_login(self):
        response = self.client.get(
            reverse("scribe_add_entry", kwargs={"mission_slug": "test"})
        )
        self.assertEqual(response.status_code, 302)


class ShiftListViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_shift_list_loads(self):
        response = self.client.get(
            reverse("scribe_shift_list", kwargs={"mission_slug": "test"})
        )
        self.assertEqual(response.status_code, 200)


class SeedScribeCommandTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_seed_scribe(self):
        from django.core.management import call_command

        call_command("seed_scribe")
        self.assertTrue(Role.objects.exists())
        self.assertTrue(EventCategory.objects.exists())
