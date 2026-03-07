from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events.models import Event, EventTimelineEntry
from procedures.models import Satellite


class EventModelTest(TestCase):
    def setUp(self):
        self.sat = Satellite.objects.create(name="SAT-1")

    def test_default_status(self):
        event = Event.objects.create(
            title="Test event",
            satellite=self.sat,
            detected_time=timezone.now(),
        )
        self.assertEqual(event.status, Event.STATUS_NEW)

    def test_default_severity(self):
        event = Event.objects.create(
            title="Test event",
            satellite=self.sat,
            detected_time=timezone.now(),
        )
        self.assertEqual(event.severity, Event.SEVERITY_L2)

    def test_str(self):
        event = Event.objects.create(
            title="Voltage dip",
            satellite=self.sat,
            detected_time=timezone.now(),
        )
        self.assertIn("Voltage dip", str(event))
        self.assertIn(f"EVT-{event.pk}", str(event))

    def test_is_open_new(self):
        event = Event.objects.create(
            title="Test", satellite=self.sat,
            detected_time=timezone.now(), status=Event.STATUS_NEW,
        )
        self.assertTrue(event.is_open)

    def test_is_open_investigating(self):
        event = Event.objects.create(
            title="Test", satellite=self.sat,
            detected_time=timezone.now(), status=Event.STATUS_INVESTIGATING,
        )
        self.assertTrue(event.is_open)

    def test_is_not_open_resolved(self):
        event = Event.objects.create(
            title="Test", satellite=self.sat,
            detected_time=timezone.now(), status=Event.STATUS_RESOLVED,
        )
        self.assertFalse(event.is_open)

    def test_is_not_open_closed(self):
        event = Event.objects.create(
            title="Test", satellite=self.sat,
            detected_time=timezone.now(), status=Event.STATUS_CLOSED,
        )
        self.assertFalse(event.is_open)

    def test_severity_rank(self):
        event = Event.objects.create(
            title="Test", satellite=self.sat,
            detected_time=timezone.now(), severity=Event.SEVERITY_L5,
        )
        self.assertEqual(event.severity_rank, 5)

    def test_severity_choices(self):
        self.assertEqual(len(Event.SEVERITY_CHOICES), 5)

    def test_status_choices_include_closed(self):
        status_vals = [val for val, _ in Event.STATUS_CHOICES]
        self.assertIn('CLOSED', status_vals)


class EventTimelineEntryModelTest(TestCase):
    def test_create_entry(self):
        sat = Satellite.objects.create(name="SAT-1")
        event = Event.objects.create(
            title="Test", satellite=sat, detected_time=timezone.now(),
        )
        entry = EventTimelineEntry.objects.create(
            event=event, body="Investigation started",
            entry_type=EventTimelineEntry.ENTRY_NOTE,
        )
        self.assertEqual(entry.body, "Investigation started")
        self.assertEqual(entry.event, event)

    def test_str(self):
        sat = Satellite.objects.create(name="SAT-1")
        event = Event.objects.create(
            title="Test", satellite=sat, detected_time=timezone.now(),
        )
        entry = EventTimelineEntry.objects.create(
            event=event, body="Note", entry_type=EventTimelineEntry.ENTRY_NOTE,
        )
        self.assertIn("Note", str(entry))


class EventListViewTest(TestCase):
    def test_list_loads(self):
        response = self.client.get(reverse("events_list"))
        self.assertEqual(response.status_code, 200)

    def test_list_with_filters(self):
        response = self.client.get(reverse("events_list"), {
            "severity": "L5", "status": "NEW",
        })
        self.assertEqual(response.status_code, 200)

    def test_list_with_search(self):
        sat = Satellite.objects.create(name="SAT-1")
        Event.objects.create(
            title="Voltage dip", satellite=sat,
            detected_time=timezone.now(), description="Bus voltage issue",
        )
        response = self.client.get(reverse("events_list"), {"q": "voltage"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Voltage dip")

    def test_list_clear_filters(self):
        response = self.client.get(reverse("events_list"), {"clear": "1"})
        self.assertEqual(response.status_code, 302)

    def test_list_shows_events(self):
        sat = Satellite.objects.create(name="SAT-1")
        Event.objects.create(
            title="Test event", satellite=sat, detected_time=timezone.now(),
        )
        response = self.client.get(reverse("events_list"))
        self.assertContains(response, "Test event")


class EventCreateViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="op1", password="testpass123")
        self.sat = Satellite.objects.create(name="SAT-1")

    def test_create_requires_login(self):
        response = self.client.get(reverse("events_create"))
        self.assertEqual(response.status_code, 302)

    def test_create_get(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.get(reverse("events_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Event")

    def test_create_post_success(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("events_create"), {
            'title': 'New voltage issue',
            'satellite': self.sat.id,
            'subsystem': Event.SUBSYSTEM_POWER,
            'severity': Event.SEVERITY_L3,
            'detected_time': '2026-03-07T10:00',
            'description': 'Bus voltage anomaly observed.',
        })
        self.assertEqual(response.status_code, 302)
        event = Event.objects.get(title='New voltage issue')
        self.assertEqual(event.status, Event.STATUS_NEW)
        self.assertEqual(event.satellite, self.sat)
        self.assertTrue(event.timeline_entries.exists())

    def test_create_post_missing_title(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("events_create"), {
            'title': '',
            'satellite': self.sat.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Event.objects.exists())

    def test_create_post_missing_satellite(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("events_create"), {
            'title': 'Test',
            'satellite': '',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Event.objects.exists())


class EventDetailViewTest(TestCase):
    def setUp(self):
        self.sat = Satellite.objects.create(name="SAT-1")
        self.event = Event.objects.create(
            title="Test detail event",
            satellite=self.sat,
            detected_time=timezone.now(),
            description="Details here.",
        )

    def test_detail_loads(self):
        response = self.client.get(reverse("events_detail", kwargs={"event_id": self.event.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test detail event")

    def test_detail_shows_timeline(self):
        EventTimelineEntry.objects.create(
            event=self.event, body="Investigation note",
            entry_type=EventTimelineEntry.ENTRY_NOTE,
        )
        response = self.client.get(reverse("events_detail", kwargs={"event_id": self.event.id}))
        self.assertContains(response, "Investigation note")

    def test_detail_shows_lifecycle_progress(self):
        response = self.client.get(reverse("events_detail", kwargs={"event_id": self.event.id}))
        self.assertContains(response, "Lifecycle Progress")

    def test_detail_404_missing(self):
        response = self.client.get(reverse("events_detail", kwargs={"event_id": 99999}))
        self.assertEqual(response.status_code, 404)


class EventUpdateViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="op1", password="testpass123")
        self.sat = Satellite.objects.create(name="SAT-1")
        self.event = Event.objects.create(
            title="Test update", satellite=self.sat,
            detected_time=timezone.now(),
        )

    def test_update_requires_login(self):
        response = self.client.post(reverse("events_update", kwargs={"event_id": self.event.id}), {
            'status': Event.STATUS_INVESTIGATING,
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_update_status(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("events_update", kwargs={"event_id": self.event.id}), {
            'status': Event.STATUS_INVESTIGATING,
            'severity': Event.SEVERITY_L2,
        })
        self.assertEqual(response.status_code, 302)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.STATUS_INVESTIGATING)
        self.assertTrue(
            self.event.timeline_entries.filter(
                entry_type=EventTimelineEntry.ENTRY_STATUS_CHANGE
            ).exists()
        )

    def test_update_severity(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("events_update", kwargs={"event_id": self.event.id}), {
            'status': Event.STATUS_NEW,
            'severity': Event.SEVERITY_L5,
        })
        self.assertEqual(response.status_code, 302)
        self.event.refresh_from_db()
        self.assertEqual(self.event.severity, Event.SEVERITY_L5)
        self.assertTrue(
            self.event.timeline_entries.filter(
                entry_type=EventTimelineEntry.ENTRY_SEVERITY_CHANGE
            ).exists()
        )

    def test_update_add_note(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("events_update", kwargs={"event_id": self.event.id}), {
            'status': Event.STATUS_NEW,
            'severity': Event.SEVERITY_L2,
            'note_body': 'Investigation in progress.',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            self.event.timeline_entries.filter(
                entry_type=EventTimelineEntry.ENTRY_NOTE,
                body='Investigation in progress.',
            ).exists()
        )

    def test_update_add_action(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("events_update", kwargs={"event_id": self.event.id}), {
            'status': Event.STATUS_NEW,
            'severity': Event.SEVERITY_L2,
            'action_body': 'Commanded safe mode.',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            self.event.timeline_entries.filter(
                entry_type=EventTimelineEntry.ENTRY_ACTION,
                body='Commanded safe mode.',
            ).exists()
        )

    def test_no_change_when_same_status(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("events_update", kwargs={"event_id": self.event.id}), {
            'status': Event.STATUS_NEW,
            'severity': Event.SEVERITY_L2,
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.event.timeline_entries.exists())


class EventCloseViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="op1", password="testpass123")
        self.sat = Satellite.objects.create(name="SAT-1")
        self.event = Event.objects.create(
            title="Closeable event", satellite=self.sat,
            detected_time=timezone.now(), status=Event.STATUS_RESOLVED,
        )

    def test_close_requires_login(self):
        response = self.client.get(reverse("events_close", kwargs={"event_id": self.event.id}))
        self.assertEqual(response.status_code, 302)

    def test_close_get_form(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.get(reverse("events_close", kwargs={"event_id": self.event.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Root Cause")

    def test_close_post(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("events_close", kwargs={"event_id": self.event.id}), {
            'root_cause': 'Faulty sensor reading.',
            'resolution_actions': 'Replaced sensor.',
            'recommendations': 'Add redundant sensor.',
        })
        self.assertEqual(response.status_code, 302)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.STATUS_CLOSED)
        self.assertEqual(self.event.root_cause, 'Faulty sensor reading.')
        self.assertEqual(self.event.resolution_actions, 'Replaced sensor.')
        self.assertEqual(self.event.recommendations, 'Add redundant sensor.')
        self.assertTrue(
            self.event.timeline_entries.filter(
                entry_type=EventTimelineEntry.ENTRY_STATUS_CHANGE,
            ).exists()
        )

    def test_close_post_empty_resolution(self):
        self.client.login(username="op1", password="testpass123")
        response = self.client.post(reverse("events_close", kwargs={"event_id": self.event.id}), {
            'root_cause': '',
            'resolution_actions': '',
            'recommendations': '',
        })
        self.assertEqual(response.status_code, 302)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.STATUS_CLOSED)


class SeedEventsCommandTest(TestCase):
    def test_seed_events(self):
        from django.core.management import call_command

        call_command("seed_procedures")
        call_command("seed_events", events=True)
        self.assertTrue(Event.objects.exists())
        self.assertTrue(EventTimelineEntry.objects.exists())

    def test_seed_events_idempotent(self):
        from django.core.management import call_command

        call_command("seed_procedures")
        call_command("seed_events", events=True)
        count1 = Event.objects.count()
        call_command("seed_events", events=True)
        count2 = Event.objects.count()
        self.assertEqual(count1, count2)
