from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from anomalies.models import Anomaly, AnomalyNote, AnomalyType, Subsystem
from procedures.models import Satellite


class SubsystemModelTest(TestCase):
    def test_str(self):
        sub = Subsystem.objects.create(name="Power")
        self.assertEqual(str(sub), "Power")


class AnomalyTypeModelTest(TestCase):
    def test_str(self):
        at = AnomalyType.objects.create(name="Fault")
        self.assertEqual(str(at), "Fault")


class AnomalyModelTest(TestCase):
    def setUp(self):
        self.sat = Satellite.objects.create(name="SAT-1")

    def test_default_status(self):
        anomaly = Anomaly.objects.create(
            satellite=self.sat,
            detection_time=timezone.now(),
        )
        self.assertEqual(anomaly.status, Anomaly.STATUS_NEW)

    def test_default_severity(self):
        anomaly = Anomaly.objects.create(
            satellite=self.sat,
            detection_time=timezone.now(),
        )
        self.assertEqual(anomaly.severity, Anomaly.SEVERITY_MEDIUM)

    def test_str(self):
        anomaly = Anomaly.objects.create(
            satellite=self.sat,
            detection_time=timezone.now(),
        )
        self.assertIn("SAT-1", str(anomaly))


class AnomalyNoteModelTest(TestCase):
    def test_create_note(self):
        sat = Satellite.objects.create(name="SAT-1")
        anomaly = Anomaly.objects.create(satellite=sat, detection_time=timezone.now())
        note = AnomalyNote.objects.create(anomaly=anomaly, body="Test note")
        self.assertEqual(note.body, "Test note")


class RegistryViewTest(TestCase):
    def test_registry_loads(self):
        response = self.client.get(reverse("anomalies_registry"))
        self.assertEqual(response.status_code, 200)

    def test_registry_with_filters(self):
        response = self.client.get(reverse("anomalies_registry"), {"severity": "HIGH", "status": "NEW"})
        self.assertEqual(response.status_code, 200)


class AddAnomalyViewTest(TestCase):
    def test_add_requires_login(self):
        response = self.client.get(reverse("anomalies_add"))
        self.assertEqual(response.status_code, 302)


class SeedAnomaliesCommandTest(TestCase):
    def test_seed_anomalies(self):
        from django.core.management import call_command

        call_command("seed_procedures")
        call_command("seed_anomalies", anomalies=True)
        self.assertTrue(Subsystem.objects.exists())
        self.assertTrue(AnomalyType.objects.exists())
