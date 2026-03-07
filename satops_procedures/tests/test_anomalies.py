from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from anomalies.models import Anomaly, AnomalyTimelineEntry
from procedures.models import Satellite, Subsystem


class AnomalyModelTest(TestCase):
    def setUp(self):
        self.sat = Satellite.objects.create(name="SAT-1")

    def test_default_status(self):
        anomaly = Anomaly.objects.create(
            title="Test anomaly",
            satellite=self.sat,
            detected_time=timezone.now(),
        )
        self.assertEqual(anomaly.status, Anomaly.STATUS_NEW)

    def test_default_severity(self):
        anomaly = Anomaly.objects.create(
            title="Test anomaly",
            satellite=self.sat,
            detected_time=timezone.now(),
        )
        self.assertEqual(anomaly.severity, Anomaly.SEVERITY_L2)

    def test_str(self):
        anomaly = Anomaly.objects.create(
            title="Voltage dip",
            satellite=self.sat,
            detected_time=timezone.now(),
        )
        self.assertIn("Voltage dip", str(anomaly))
        self.assertIn(f"ANOM-{anomaly.pk}", str(anomaly))

    def test_is_open_new(self):
        anomaly = Anomaly.objects.create(
            title="Test", satellite=self.sat,
            detected_time=timezone.now(), status=Anomaly.STATUS_NEW,
        )
        self.assertTrue(anomaly.is_open)

    def test_is_open_investigating(self):
        anomaly = Anomaly.objects.create(
            title="Test", satellite=self.sat,
            detected_time=timezone.now(), status=Anomaly.STATUS_INVESTIGATING,
        )
        self.assertTrue(anomaly.is_open)

    def test_is_not_open_resolved(self):
        anomaly = Anomaly.objects.create(
            title="Test", satellite=self.sat,
            detected_time=timezone.now(), status=Anomaly.STATUS_RESOLVED,
        )
        self.assertFalse(anomaly.is_open)

    def test_is_not_open_closed(self):
        anomaly = Anomaly.objects.create(
            title="Test", satellite=self.sat,
            detected_time=timezone.now(), status=Anomaly.STATUS_CLOSED,
        )
        self.assertFalse(anomaly.is_open)

    def test_severity_rank(self):
        anomaly = Anomaly.objects.create(
            title="Test", satellite=self.sat,
            detected_time=timezone.now(), severity=Anomaly.SEVERITY_L5,
        )
        self.assertEqual(anomaly.severity_rank, 5)

    def test_severity_choices(self):
        self.assertEqual(len(Anomaly.SEVERITY_CHOICES), 5)

    def test_status_choices_include_closed(self):
        status_vals = [val for val, _ in Anomaly.STATUS_CHOICES]
        self.assertIn('CLOSED', status_vals)


class AnomalyTimelineEntryModelTest(TestCase):
    def test_create_entry(self):
        sat = Satellite.objects.create(name="SAT-1")
        anomaly = Anomaly.objects.create(
            title="Test", satellite=sat, detected_time=timezone.now(),
        )
        entry = AnomalyTimelineEntry.objects.create(
            anomaly=anomaly, body="Investigation started",
            entry_type=AnomalyTimelineEntry.ENTRY_NOTE,
        )
        self.assertEqual(entry.body, "Investigation started")
        self.assertEqual(entry.anomaly, anomaly)

    def test_str(self):
        sat = Satellite.objects.create(name="SAT-1")
        anomaly = Anomaly.objects.create(
            title="Test", satellite=sat, detected_time=timezone.now(),
        )
        entry = AnomalyTimelineEntry.objects.create(
            anomaly=anomaly, body="Note", entry_type=AnomalyTimelineEntry.ENTRY_NOTE,
        )
        self.assertIn("Note", str(entry))


class AnomalyListViewTest(TestCase):
    def test_list_loads(self):
        response = self.client.get(reverse("anomalies_list"))
        self.assertEqual(response.status_code, 200)

    def test_list_with_filters(self):
        response = self.client.get(reverse("anomalies_list"), {
            "severity": "L5", "status": "NEW",
        })
        self.assertEqual(response.status_code, 200)

    def test_list_with_search(self):
        sat = Satellite.objects.create(name="SAT-1")
        Anomaly.objects.create(
            title="Voltage dip", satellite=sat,
            detected_time=timezone.now(), description="Bus voltage issue",
        )
        response = self.client.get(reverse("anomalies_list"), {"q": "voltage"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Voltage dip")

    def test_list_clear_filters(self):
        response = self.client.get(reverse("anomalies_list"), {"clear": "1"})
        self.assertEqual(response.status_code, 302)

    def test_list_shows_anomalies(self):
        sat = Satellite.objects.create(name="SAT-1")
        Anomaly.objects.create(
            title="Test anomaly", satellite=sat, detected_time=timezone.now(),
        )
        response = self.client.get(reverse("anomalies_list"))
        self.assertContains(response, "Test anomaly")


class AnomalyCreateViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="op1", password="testpass123")
        self.sat = Satellite.objects.create(name="SAT-1")
        self.subsystem = Subsystem.objects.create(name="Power")

    def test_create_requires_login(self):
        response = self.client.get(reverse("anomalies_create"))
        self.assertEqual(response.status_code, 302)

    def test_create_get(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.get(reverse("anomalies_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Report Anomaly")

    def test_create_post_success(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("anomalies_create"), {
            'title': 'New voltage issue',
            'satellite': self.sat.id,
            'subsystem': self.subsystem.id,
            'severity': Anomaly.SEVERITY_L3,
            'detected_time': '2026-03-07T10:00',
            'description': 'Bus voltage anomaly observed.',
        })
        self.assertEqual(response.status_code, 302)
        anomaly = Anomaly.objects.get(title='New voltage issue')
        self.assertEqual(anomaly.status, Anomaly.STATUS_NEW)
        self.assertEqual(anomaly.satellite, self.sat)
        self.assertEqual(anomaly.subsystem, self.subsystem)
        self.assertTrue(anomaly.timeline_entries.exists())

    def test_create_post_missing_title(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("anomalies_create"), {
            'title': '',
            'satellite': self.sat.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Anomaly.objects.exists())

    def test_create_post_missing_satellite(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("anomalies_create"), {
            'title': 'Test',
            'satellite': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Anomaly.objects.exists())


class AnomalyDetailViewTest(TestCase):
    def setUp(self):
        self.sat = Satellite.objects.create(name="SAT-1")
        self.anomaly = Anomaly.objects.create(
            title="Test detail anomaly",
            satellite=self.sat,
            detected_time=timezone.now(),
            description="Details here.",
        )

    def test_detail_loads(self):
        response = self.client.get(reverse("anomalies_detail", kwargs={"anomaly_id": self.anomaly.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test detail anomaly")

    def test_detail_shows_timeline(self):
        AnomalyTimelineEntry.objects.create(
            anomaly=self.anomaly, body="Investigation note",
            entry_type=AnomalyTimelineEntry.ENTRY_NOTE,
        )
        response = self.client.get(reverse("anomalies_detail", kwargs={"anomaly_id": self.anomaly.id}))
        self.assertContains(response, "Investigation note")

    def test_detail_shows_lifecycle_progress(self):
        response = self.client.get(reverse("anomalies_detail", kwargs={"anomaly_id": self.anomaly.id}))
        self.assertContains(response, "Lifecycle Progress")

    def test_detail_404_missing(self):
        response = self.client.get(reverse("anomalies_detail", kwargs={"anomaly_id": 99999}))
        self.assertEqual(response.status_code, 404)


class AnomalyUpdateViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="op1", password="testpass123")
        self.sat = Satellite.objects.create(name="SAT-1")
        self.anomaly = Anomaly.objects.create(
            title="Test update", satellite=self.sat,
            detected_time=timezone.now(),
        )

    def test_update_requires_login(self):
        response = self.client.post(reverse("anomalies_update", kwargs={"anomaly_id": self.anomaly.id}), {
            'status': Anomaly.STATUS_INVESTIGATING,
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_update_status(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("anomalies_update", kwargs={"anomaly_id": self.anomaly.id}), {
            'status': Anomaly.STATUS_INVESTIGATING,
            'severity': Anomaly.SEVERITY_L2,
        })
        self.assertEqual(response.status_code, 302)
        self.anomaly.refresh_from_db()
        self.assertEqual(self.anomaly.status, Anomaly.STATUS_INVESTIGATING)
        self.assertTrue(
            self.anomaly.timeline_entries.filter(
                entry_type=AnomalyTimelineEntry.ENTRY_STATUS_CHANGE
            ).exists()
        )

    def test_update_severity(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("anomalies_update", kwargs={"anomaly_id": self.anomaly.id}), {
            'status': Anomaly.STATUS_NEW,
            'severity': Anomaly.SEVERITY_L5,
        })
        self.assertEqual(response.status_code, 302)
        self.anomaly.refresh_from_db()
        self.assertEqual(self.anomaly.severity, Anomaly.SEVERITY_L5)
        self.assertTrue(
            self.anomaly.timeline_entries.filter(
                entry_type=AnomalyTimelineEntry.ENTRY_SEVERITY_CHANGE
            ).exists()
        )

    def test_update_add_note(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("anomalies_update", kwargs={"anomaly_id": self.anomaly.id}), {
            'status': Anomaly.STATUS_NEW,
            'severity': Anomaly.SEVERITY_L2,
            'note_body': 'Investigation in progress.',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            self.anomaly.timeline_entries.filter(
                entry_type=AnomalyTimelineEntry.ENTRY_NOTE,
                body='Investigation in progress.',
            ).exists()
        )

    def test_update_add_action(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("anomalies_update", kwargs={"anomaly_id": self.anomaly.id}), {
            'status': Anomaly.STATUS_NEW,
            'severity': Anomaly.SEVERITY_L2,
            'action_body': 'Commanded safe mode.',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            self.anomaly.timeline_entries.filter(
                entry_type=AnomalyTimelineEntry.ENTRY_ACTION,
                body='Commanded safe mode.',
            ).exists()
        )

    def test_no_change_when_same_status(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("anomalies_update", kwargs={"anomaly_id": self.anomaly.id}), {
            'status': Anomaly.STATUS_NEW,
            'severity': Anomaly.SEVERITY_L2,
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.anomaly.timeline_entries.exists())


class AnomalyCloseViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="op1", password="testpass123")
        self.sat = Satellite.objects.create(name="SAT-1")
        self.anomaly = Anomaly.objects.create(
            title="Closeable anomaly", satellite=self.sat,
            detected_time=timezone.now(), status=Anomaly.STATUS_RESOLVED,
        )

    def test_close_requires_login(self):
        response = self.client.get(reverse("anomalies_close", kwargs={"anomaly_id": self.anomaly.id}))
        self.assertEqual(response.status_code, 302)

    def test_close_get_form(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.get(reverse("anomalies_close", kwargs={"anomaly_id": self.anomaly.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Root Cause")

    def test_close_post(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("anomalies_close", kwargs={"anomaly_id": self.anomaly.id}), {
            'root_cause': 'Faulty sensor reading.',
            'resolution_actions': 'Replaced sensor.',
            'recommendations': 'Add redundant sensor.',
        })
        self.assertEqual(response.status_code, 302)
        self.anomaly.refresh_from_db()
        self.assertEqual(self.anomaly.status, Anomaly.STATUS_CLOSED)
        self.assertEqual(self.anomaly.root_cause, 'Faulty sensor reading.')
        self.assertEqual(self.anomaly.resolution_actions, 'Replaced sensor.')
        self.assertEqual(self.anomaly.recommendations, 'Add redundant sensor.')
        self.assertTrue(
            self.anomaly.timeline_entries.filter(
                entry_type=AnomalyTimelineEntry.ENTRY_STATUS_CHANGE,
            ).exists()
        )

    def test_close_post_empty_resolution(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("anomalies_close", kwargs={"anomaly_id": self.anomaly.id}), {
            'root_cause': '',
            'resolution_actions': '',
            'recommendations': '',
        })
        self.assertEqual(response.status_code, 302)
        self.anomaly.refresh_from_db()
        self.assertEqual(self.anomaly.status, Anomaly.STATUS_CLOSED)


class SeedAnomaliesCommandTest(TestCase):
    def test_seed_anomalies(self):
        from django.core.management import call_command

        call_command("seed_procedures")
        call_command("seed_anomalies", anomalies=True)
        self.assertTrue(Anomaly.objects.exists())
        self.assertTrue(AnomalyTimelineEntry.objects.exists())

    def test_seed_anomalies_idempotent(self):
        from django.core.management import call_command

        call_command("seed_procedures")
        call_command("seed_anomalies", anomalies=True)
        count1 = Anomaly.objects.count()
        call_command("seed_anomalies", anomalies=True)
        count2 = Anomaly.objects.count()
        self.assertEqual(count1, count2)
