from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from missions.models import Mission, MissionMembership
from procedures.models import Satellite
from smerequests.models import RequestNote, RequestType, SMERequest

# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class RequestTypeModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_str(self):
        rt = RequestType.objects.create(name='Backorbit Data', mission=self.mission)
        self.assertEqual(str(rt), 'Backorbit Data')


class SMERequestModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')
        self.user = User.objects.create_user('ops', password='ops')
        self.sat = Satellite.objects.create(name='SAT-1', mission=self.mission)

    def test_str(self):
        req = SMERequest.objects.create(
            title='Test request',
            description='Need data',
            status=SMERequest.STATUS_SUBMITTED,
            requested_by=self.user,
            mission=self.mission,
        )
        self.assertIn('Test request', str(req))
        self.assertIn(str(req.pk), str(req))

    def test_default_status(self):
        req = SMERequest.objects.create(
            title='Test',
            description='Desc',
            requested_by=self.user,
            mission=self.mission,
        )
        self.assertEqual(req.status, SMERequest.STATUS_SUBMITTED)


class RequestNoteModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')
        self.user = User.objects.create_user('ops', password='ops')
        self.req = SMERequest.objects.create(
            title='Test',
            description='Desc',
            requested_by=self.user,
            mission=self.mission,
        )

    def test_str(self):
        note = RequestNote.objects.create(
            request=self.req, body='A note', created_by=self.user
        )
        self.assertIn(str(self.req.pk), str(note))


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------


class RequestListViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_loads_empty(self):
        resp = self.client.get(
            reverse('sme_request_list', kwargs={'mission_slug': 'test'})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'SME')

    def test_lists_requests(self):
        user = User.objects.create_user('ops', password='ops')
        SMERequest.objects.create(
            title='Test Request',
            description='Need data',
            requested_by=user,
            mission=self.mission,
        )
        resp = self.client.get(
            reverse('sme_request_list', kwargs={'mission_slug': 'test'})
        )
        self.assertContains(resp, 'Test Request')

    def test_clear_filters(self):
        resp = self.client.get(
            reverse('sme_request_list', kwargs={'mission_slug': 'test'}),
            {'clear': '1'},
        )
        self.assertEqual(resp.status_code, 302)


class OpsQueueViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_loads(self):
        resp = self.client.get(
            reverse('sme_ops_queue', kwargs={'mission_slug': 'test'})
        )
        self.assertEqual(resp.status_code, 200)


class CreateRequestViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')
        self.user = User.objects.create_user('ops', password='ops')
        MissionMembership.objects.create(
            user=self.user, mission=self.mission, role='OPERATOR'
        )
        Satellite.objects.create(name='SAT-1', mission=self.mission)

    def test_requires_login(self):
        resp = self.client.get(
            reverse('sme_request_create', kwargs={'mission_slug': 'test'})
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp.url)

    def test_get_when_logged_in(self):
        self.client.login(username='ops', password='ops')
        resp = self.client.get(
            reverse('sme_request_create', kwargs={'mission_slug': 'test'})
        )
        self.assertEqual(resp.status_code, 200)

    def test_post_creates_request(self):
        self.client.login(username='ops', password='ops')
        resp = self.client.post(
            reverse('sme_request_create', kwargs={'mission_slug': 'test'}),
            {
                'title': 'New Request',
                'description': 'Need telemetry export',
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(SMERequest.objects.filter(title='New Request').exists())


class RequestDetailViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')
        self.user = User.objects.create_user('ops', password='ops')
        self.req = SMERequest.objects.create(
            title='Detail Test',
            description='Desc',
            requested_by=self.user,
            mission=self.mission,
        )

    def test_detail_loads(self):
        resp = self.client.get(
            reverse(
                'sme_request_detail',
                kwargs={'mission_slug': 'test', 'request_id': self.req.pk},
            )
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Detail Test')

    def test_detail_404(self):
        resp = self.client.get(
            reverse(
                'sme_request_detail',
                kwargs={'mission_slug': 'test', 'request_id': 99999},
            )
        )
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Seed command test
# ---------------------------------------------------------------------------


class SeedSMERequestsCommandTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_seed_creates_types(self):
        from django.core.management import call_command

        call_command('seed_smerequests')
        self.assertTrue(RequestType.objects.exists())

    def test_seed_idempotent(self):
        from django.core.management import call_command

        call_command('seed_smerequests')
        count1 = RequestType.objects.count()
        call_command('seed_smerequests')
        count2 = RequestType.objects.count()
        self.assertEqual(count1, count2)
