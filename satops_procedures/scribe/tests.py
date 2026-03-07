from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import EventCategory, MissionLogEntry, Role, ScribeTag, Shift


class RoleModelTest(TestCase):
    def test_str(self):
        role = Role.objects.create(name="Flight Controller")
        self.assertEqual(str(role), "Flight Controller")


class EventCategoryModelTest(TestCase):
    def test_str(self):
        cat = EventCategory.objects.create(name="Telemetry")
        self.assertEqual(str(cat), "Telemetry")


class ScribeTagModelTest(TestCase):
    def test_slug_auto_generated(self):
        tag = ScribeTag.objects.create(name="High Priority")
        self.assertEqual(tag.slug, "high-priority")


class ShiftModelTest(TestCase):
    def test_str(self):
        now = timezone.now()
        shift = Shift.objects.create(start_time=now, end_time=now)
        self.assertIn(str(now.year), str(shift))


class MissionLogEntryModelTest(TestCase):
    def setUp(self):
        self.role = Role.objects.create(name="Ops")
        self.cat = EventCategory.objects.create(name="Event")

    def test_create_entry(self):
        entry = MissionLogEntry.objects.create(
            timestamp=timezone.now(),
            role=self.role,
            category=self.cat,
            severity=MissionLogEntry.SEVERITY_INFO,
            description="Test entry",
        )
        self.assertEqual(entry.severity, "INFO")

    def test_default_severity(self):
        entry = MissionLogEntry.objects.create(
            timestamp=timezone.now(),
            role=self.role,
            category=self.cat,
            description="Test",
        )
        self.assertEqual(entry.severity, MissionLogEntry.SEVERITY_INFO)


class ScribeTimelineViewTest(TestCase):
    def test_timeline_loads(self):
        response = self.client.get(reverse("scribe_timeline"))
        self.assertEqual(response.status_code, 200)


class ScribeAddEntryViewTest(TestCase):
    def test_add_entry_requires_login(self):
        response = self.client.get(reverse("scribe_add_entry"))
        self.assertEqual(response.status_code, 302)


class ShiftListViewTest(TestCase):
    def test_shift_list_loads(self):
        response = self.client.get(reverse("scribe_shift_list"))
        self.assertEqual(response.status_code, 200)


class SeedScribeCommandTest(TestCase):
    def test_seed_scribe(self):
        from django.core.management import call_command
        call_command("seed_scribe")
        self.assertTrue(Role.objects.exists())
        self.assertTrue(EventCategory.objects.exists())
