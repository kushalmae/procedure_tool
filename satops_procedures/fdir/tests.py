from django.test import TestCase
from django.urls import reverse

from .models import FDIREntry, Subsystem


class SubsystemModelTest(TestCase):
    def test_str(self):
        sub = Subsystem.objects.create(name="ADCS")
        self.assertEqual(str(sub), "ADCS")

    def test_slug_auto_generated(self):
        sub = Subsystem.objects.create(name="Power System")
        self.assertEqual(sub.slug, "power-system")


class FDIREntryModelTest(TestCase):
    def setUp(self):
        self.sub = Subsystem.objects.create(name="ADCS")

    def test_str(self):
        entry = FDIREntry.objects.create(name="Gyro Failure", subsystem=self.sub)
        self.assertIn("Gyro Failure", str(entry))

    def test_default_severity(self):
        entry = FDIREntry.objects.create(name="Test", subsystem=self.sub)
        self.assertEqual(entry.severity, FDIREntry.SEVERITY_INFO)


class EntryListViewTest(TestCase):
    def test_entry_list_loads(self):
        response = self.client.get(reverse("fdir_entry_list"))
        self.assertEqual(response.status_code, 200)

    def test_entry_list_with_search(self):
        response = self.client.get(reverse("fdir_entry_list"), {"q": "gyro"})
        self.assertEqual(response.status_code, 200)


class EntryCreateViewTest(TestCase):
    def test_create_requires_login(self):
        response = self.client.get(reverse("fdir_entry_create"))
        self.assertEqual(response.status_code, 302)


class SeedFdirCommandTest(TestCase):
    def test_seed_fdir(self):
        from django.core.management import call_command
        call_command("seed_fdir")
        self.assertTrue(Subsystem.objects.exists())

    def test_seed_fdir_with_entries(self):
        from django.core.management import call_command
        call_command("seed_procedures")
        call_command("seed_fdir", entries=True)
        self.assertTrue(FDIREntry.objects.exists())
