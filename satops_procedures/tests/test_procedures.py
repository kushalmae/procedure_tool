from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from missions.models import Mission, MissionMembership
from procedures.models import Procedure, ProcedureRun, Satellite, StepExecution, Tag


class SatelliteModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_str(self):
        sat = Satellite.objects.create(name="SAT-1", mission=self.mission)
        self.assertEqual(str(sat), "SAT-1")

    def test_ordering(self):
        Satellite.objects.create(name="Bravo", mission=self.mission)
        Satellite.objects.create(name="Alpha", mission=self.mission)
        names = list(Satellite.objects.filter(mission=self.mission).values_list("name", flat=True))
        self.assertEqual(names, ["Alpha", "Bravo"])


class TagModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_slug_auto_generated(self):
        tag = Tag.objects.create(name="Bus Checkout", mission=self.mission)
        self.assertEqual(tag.slug, "bus-checkout")

    def test_str(self):
        tag = Tag.objects.create(name="Thermal", mission=self.mission)
        self.assertEqual(str(tag), "Thermal")


class ProcedureModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_str(self):
        proc = Procedure.objects.create(
            name="Checkout", version="1.0", yaml_file="checkout.yaml", mission=self.mission
        )
        self.assertEqual(str(proc), "Checkout (1.0)")

    def test_tags_m2m(self):
        proc = Procedure.objects.create(
            name="Test", version="1", yaml_file="test.yaml", mission=self.mission
        )
        tag = Tag.objects.create(name="Safety", mission=self.mission)
        proc.tags.add(tag)
        self.assertIn(tag, proc.tags.all())


class ProcedureRunModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')
        self.sat = Satellite.objects.create(name="SAT-1", mission=self.mission)
        self.proc = Procedure.objects.create(
            name="Test", version="1", yaml_file="test.yaml", mission=self.mission
        )
        self.user = User.objects.create_user("operator", password="pass")
        MissionMembership.objects.create(user=self.user, mission=self.mission, role='OPERATOR')

    def test_default_status(self):
        run = ProcedureRun.objects.create(
            satellite=self.sat,
            procedure=self.proc,
            operator=self.user,
            mission=self.mission,
        )
        self.assertEqual(run.status, ProcedureRun.STATUS_RUNNING)

    def test_str(self):
        run = ProcedureRun.objects.create(
            satellite=self.sat, procedure=self.proc, mission=self.mission
        )
        self.assertIn("SAT-1", str(run))
        self.assertIn("RUNNING", str(run))


class StepExecutionModelTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')
        sat = Satellite.objects.create(name="SAT-1", mission=self.mission)
        proc = Procedure.objects.create(
            name="Test", version="1", yaml_file="test.yaml", mission=self.mission
        )
        self.run = ProcedureRun.objects.create(
            satellite=sat, procedure=proc, mission=self.mission
        )

    def test_create_step(self):
        step = StepExecution.objects.create(run=self.run, step_id="1", status="PASS")
        self.assertEqual(step.step_id, "1")
        self.assertEqual(step.status, "PASS")


class DashboardViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_dashboard_loads(self):
        response = self.client.get(
            reverse("dashboard", kwargs={"mission_slug": "test"})
        )
        self.assertEqual(response.status_code, 200)

    def test_dashboard_search(self):
        response = self.client.get(
            reverse("dashboard", kwargs={"mission_slug": "test"}),
            {"q": "test"},
        )
        self.assertEqual(response.status_code, 200)


class ProcedureListViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_procedure_list_loads(self):
        response = self.client.get(
            reverse("procedure_list", kwargs={"mission_slug": "test"})
        )
        self.assertEqual(response.status_code, 200)


class HistoryViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_history_loads(self):
        response = self.client.get(
            reverse("history", kwargs={"mission_slug": "test"})
        )
        self.assertEqual(response.status_code, 200)


class StartViewTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_start_requires_login(self):
        response = self.client.get(
            reverse("start", kwargs={"mission_slug": "test"})
        )
        self.assertEqual(response.status_code, 302)

    def test_start_loads_when_authenticated(self):
        self.user = User.objects.create_user("op", password="pass")
        MissionMembership.objects.create(user=self.user, mission=self.mission, role='OPERATOR')
        self.client.login(username="op", password="pass")
        response = self.client.get(
            reverse("start", kwargs={"mission_slug": "test"})
        )
        self.assertEqual(response.status_code, 200)


class SeedCommandTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_seed_procedures(self):
        from django.core.management import call_command

        call_command("seed_procedures")
        self.assertTrue(Satellite.objects.exists())
        self.assertTrue(Procedure.objects.exists())

    def test_seed_all(self):
        from django.core.management import call_command

        call_command("seed_all")
        self.assertTrue(Satellite.objects.exists())
