from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from missions.models import DashboardLayout, Mission, MissionMembership

User = get_user_model()


class DashboardCustomizeViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')
        self.user = User.objects.create_user(username='op', password='pass')
        MissionMembership.objects.create(user=self.user, mission=self.mission, role='OPERATOR')
        self.client.login(username='op', password='pass')

    def test_customize_page_loads(self):
        resp = self.client.get(reverse('dashboard_customize', kwargs={'mission_slug': 'test'}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Customize Dashboard')
        self.assertContains(resp, 'Summary Cards')
        self.assertContains(resp, 'Recent Runs')

    def test_save_layout(self):
        resp = self.client.post(
            reverse('dashboard_customize', kwargs={'mission_slug': 'test'}),
            {
                'widget_order': ['summary_cards', 'runs_table', 'recent_anomalies'],
                'enabled_summary_cards': '1',
                'enabled_runs_table': '1',
                'enabled_recent_anomalies': '0',
            },
        )
        self.assertEqual(resp.status_code, 302)
        layout = DashboardLayout.objects.get(user=self.user, mission=self.mission)
        widget_map = {w['widget']: w for w in layout.layout_json}
        self.assertTrue(widget_map['summary_cards']['enabled'])
        self.assertTrue(widget_map['runs_table']['enabled'])

    def test_save_overwrites_existing(self):
        DashboardLayout.objects.create(
            user=self.user, mission=self.mission,
            layout_json=[{'widget': 'summary_cards', 'enabled': False, 'order': 0}],
        )
        self.client.post(
            reverse('dashboard_customize', kwargs={'mission_slug': 'test'}),
            {
                'widget_order': ['summary_cards'],
                'enabled_summary_cards': '1',
            },
        )
        layout = DashboardLayout.objects.get(user=self.user, mission=self.mission)
        widget_map = {w['widget']: w for w in layout.layout_json}
        self.assertTrue(widget_map['summary_cards']['enabled'])


class DashboardWidgetRenderTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_dashboard_with_default_layout(self):
        resp = self.client.get(reverse('dashboard', kwargs={'mission_slug': 'test'}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Fleet health')
        self.assertContains(resp, 'Fleet Procedures')

    def test_dashboard_with_custom_layout_hides_disabled(self):
        user = User.objects.create_user(username='op', password='pass')
        MissionMembership.objects.create(user=user, mission=self.mission, role='OPERATOR')
        DashboardLayout.objects.create(
            user=user, mission=self.mission,
            layout_json=[
                {'widget': 'summary_cards', 'enabled': False, 'order': 0},
                {'widget': 'runs_table', 'enabled': True, 'order': 1},
                {'widget': 'recent_anomalies', 'enabled': False, 'order': 2},
                {'widget': 'recent_scribe', 'enabled': False, 'order': 3},
            ],
        )
        self.client.login(username='op', password='pass')
        resp = self.client.get(reverse('dashboard', kwargs={'mission_slug': 'test'}))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'Fleet health')

    def test_unauthenticated_gets_default_layout(self):
        resp = self.client.get(reverse('dashboard', kwargs={'mission_slug': 'test'}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Fleet health')
