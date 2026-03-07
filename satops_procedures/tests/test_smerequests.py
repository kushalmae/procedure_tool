from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from procedures.models import Satellite
from smerequests.models import RequestNote, RequestType, SMERequest


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class RequestTypeModelTest(TestCase):
    def test_str(self):
        rt = RequestType.objects.create(name='Backorbit Data')
        self.assertEqual(str(rt), 'Backorbit Data')


class SMERequestModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ops', password='ops')
        self.sat = Satellite.objects.create(name='SAT-1')

    def test_str(self):
        req = SMERequest.objects.create(
            title='Test request',
            description='Need data',
            status=SMERequest.STATUS_SUBMITTED,
            requested_by=self.user,
        )
        self.assertIn('Test request', str(req))
        self.assertIn(str(req.pk), str(req))

    def test_default_status(self):
        req = SMERequest.objects.create(
            title='Test',
            description='Desc',
            requested_by=self.user,
        )
        self.assertEqual(req.status, SMERequest.STATUS_SUBMITTED)


class RequestNoteModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ops', password='ops')
        self.req = SMERequest.objects.create(
            title='Test',
            description='Desc',
            requested_by=self.user,
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
    def test_loads_empty(self):
        resp = self.client.get(reverse('sme_request_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'SME')

    def test_lists_requests(self):
        user = User.objects.create_user('ops', password='ops')
        SMERequest.objects.create(
            title='Test Request',
            description='Need data',
            requested_by=user,
        )
        resp = self.client.get(reverse('sme_request_list'))
        self.assertContains(resp, 'Test Request')

    def test_clear_filters(self):
        resp = self.client.get(reverse('sme_request_list'), {'clear': '1'})
        self.assertEqual(resp.status_code, 302)


class OpsQueueViewTest(TestCase):
    def test_loads(self):
        resp = self.client.get(reverse('sme_ops_queue'))
        self.assertEqual(resp.status_code, 200)


class CreateRequestViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ops', password='ops')
        Satellite.objects.create(name='SAT-1')

    def test_requires_login(self):
        resp = self.client.get(reverse('sme_request_create'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp.url)

    def test_get_when_logged_in(self):
        self.client.login(username='ops', password='ops')
        resp = self.client.get(reverse('sme_request_create'))
        self.assertEqual(resp.status_code, 200)

    def test_post_creates_request(self):
        self.client.login(username='ops', password='ops')
        resp = self.client.post(
            reverse('sme_request_create'),
            {
                'title': 'New Request',
                'description': 'Need telemetry export',
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(SMERequest.objects.filter(title='New Request').exists())


class RequestDetailViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ops', password='ops')
        self.req = SMERequest.objects.create(
            title='Detail Test',
            description='Desc',
            requested_by=self.user,
        )

    def test_detail_loads(self):
        resp = self.client.get(
            reverse('sme_request_detail', args=[self.req.pk])
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Detail Test')

    def test_detail_404(self):
        resp = self.client.get(
            reverse('sme_request_detail', args=[99999])
        )
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Seed command test
# ---------------------------------------------------------------------------


class SeedSMERequestsCommandTest(TestCase):
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
