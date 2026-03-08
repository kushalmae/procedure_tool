from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from auditlog.models import AuditEntry
from auditlog.services import log_action
from missions.models import Mission, MissionMembership

User = get_user_model()


class AuditEntryModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')
        self.user = User.objects.create_user(username='op', password='pass')

    def test_create_entry(self):
        entry = AuditEntry.objects.create(
            mission=self.mission,
            user=self.user,
            action=AuditEntry.ACTION_CREATE,
            model_name='Procedure',
            object_id='42',
            object_repr='Bus Checkout (1.0)',
            detail='Created new procedure',
        )
        self.assertEqual(str(entry), f"{entry.timestamp} op Create Procedure Bus Checkout (1.0)")

    def test_ordering(self):
        AuditEntry.objects.create(
            mission=self.mission, user=self.user,
            action='CREATE', model_name='Procedure',
        )
        AuditEntry.objects.create(
            mission=self.mission, user=self.user,
            action='UPDATE', model_name='Procedure',
        )
        entries = list(AuditEntry.objects.all())
        self.assertEqual(entries[0].action, 'UPDATE')


class AuditLogViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')
        self.user = User.objects.create_user(username='op', password='pass')
        MissionMembership.objects.create(user=self.user, mission=self.mission, role='OPERATOR')
        AuditEntry.objects.create(
            mission=self.mission, user=self.user,
            action='CREATE', model_name='Procedure',
            object_repr='Bus Checkout', detail='Created',
        )

    def test_loads(self):
        resp = self.client.get(reverse('audit_log', kwargs={'mission_slug': 'test'}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Audit Log')
        self.assertContains(resp, 'Bus Checkout')

    def test_filter_by_action(self):
        resp = self.client.get(
            reverse('audit_log', kwargs={'mission_slug': 'test'}),
            {'action': 'CREATE'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Bus Checkout')

    def test_search(self):
        resp = self.client.get(
            reverse('audit_log', kwargs={'mission_slug': 'test'}),
            {'q': 'Bus'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Bus Checkout')


class AuditServicesTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')
        self.user = User.objects.create_user(username='op', password='pass')
        self.client.login(username='op', password='pass')

    def test_log_action(self):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user
        request.mission = self.mission
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        log_action(request, 'CREATE', 'Procedure', '1', 'Test Proc')
        self.assertEqual(AuditEntry.objects.count(), 1)
        entry = AuditEntry.objects.first()
        self.assertEqual(entry.action, 'CREATE')
        self.assertEqual(entry.ip_address, '127.0.0.1')
