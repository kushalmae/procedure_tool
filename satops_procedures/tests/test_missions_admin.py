from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from missions.models import Mission, MissionMembership

User = get_user_model()


class MissionSettingsViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Alpha', slug='alpha', color='#3B82F6')
        self.admin_user = User.objects.create_user(username='admin', password='pass')
        MissionMembership.objects.create(
            user=self.admin_user, mission=self.mission, role='ADMIN',
        )
        self.client.login(username='admin', password='pass')

    def test_settings_loads(self):
        resp = self.client.get(reverse('mission_settings', kwargs={'mission_slug': 'alpha'}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Alpha')

    def test_update_name(self):
        resp = self.client.post(
            reverse('mission_settings', kwargs={'mission_slug': 'alpha'}),
            {'name': 'Alpha-Updated', 'description': 'New desc', 'color': '#10B981'},
        )
        self.assertEqual(resp.status_code, 302)
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.name, 'Alpha-Updated')
        self.assertEqual(self.mission.description, 'New desc')

    def test_non_admin_blocked(self):
        viewer = User.objects.create_user(username='viewer', password='pass')
        MissionMembership.objects.create(user=viewer, mission=self.mission, role='VIEWER')
        self.client.login(username='viewer', password='pass')
        resp = self.client.get(reverse('mission_settings', kwargs={'mission_slug': 'alpha'}))
        self.assertEqual(resp.status_code, 302)


class MissionMembersViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Alpha', slug='alpha', color='#3B82F6')
        self.admin_user = User.objects.create_user(username='admin', password='pass')
        self.membership = MissionMembership.objects.create(
            user=self.admin_user, mission=self.mission, role='ADMIN',
        )
        self.client.login(username='admin', password='pass')

    def test_members_list_loads(self):
        resp = self.client.get(reverse('mission_members', kwargs={'mission_slug': 'alpha'}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'admin')

    def test_add_member(self):
        new_user = User.objects.create_user(username='newop', password='pass')
        resp = self.client.post(
            reverse('mission_member_add', kwargs={'mission_slug': 'alpha'}),
            {'user_id': new_user.pk, 'role': 'OPERATOR'},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(
            MissionMembership.objects.filter(user=new_user, mission=self.mission).exists()
        )

    def test_change_role(self):
        other = User.objects.create_user(username='other', password='pass')
        mem = MissionMembership.objects.create(user=other, mission=self.mission, role='VIEWER')
        resp = self.client.post(
            reverse('mission_member_role', kwargs={'mission_slug': 'alpha', 'membership_id': mem.pk}),
            {'role': 'OPERATOR'},
        )
        self.assertEqual(resp.status_code, 302)
        mem.refresh_from_db()
        self.assertEqual(mem.role, 'OPERATOR')

    def test_cannot_change_own_role(self):
        resp = self.client.post(
            reverse('mission_member_role', kwargs={'mission_slug': 'alpha', 'membership_id': self.membership.pk}),
            {'role': 'VIEWER'},
        )
        self.assertEqual(resp.status_code, 302)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.role, 'ADMIN')

    def test_remove_member(self):
        other = User.objects.create_user(username='other', password='pass')
        mem = MissionMembership.objects.create(user=other, mission=self.mission, role='OPERATOR')
        resp = self.client.post(
            reverse('mission_member_remove', kwargs={'mission_slug': 'alpha', 'membership_id': mem.pk}),
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(MissionMembership.objects.filter(pk=mem.pk).exists())

    def test_cannot_remove_self(self):
        resp = self.client.post(
            reverse('mission_member_remove', kwargs={'mission_slug': 'alpha', 'membership_id': self.membership.pk}),
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(MissionMembership.objects.filter(pk=self.membership.pk).exists())


class MissionCreateViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='creator', password='pass')
        self.client.login(username='creator', password='pass')

    def test_create_page_loads(self):
        resp = self.client.get(reverse('mission_create'))
        self.assertEqual(resp.status_code, 200)

    def test_create_mission(self):
        resp = self.client.post(reverse('mission_create'), {
            'name': 'Delta-4',
            'description': 'A new mission',
            'color': '#EF4444',
        })
        self.assertEqual(resp.status_code, 302)
        mission = Mission.objects.get(slug='delta-4')
        self.assertEqual(mission.name, 'Delta-4')
        self.assertTrue(
            MissionMembership.objects.filter(
                user=self.user, mission=mission, role='ADMIN',
            ).exists()
        )
