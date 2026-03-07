from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Procedure, ProcedureRun, Satellite, StepExecution, Tag


class SatelliteModelTest(TestCase):
    def test_str(self):
        sat = Satellite.objects.create(name="SAT-1")
        self.assertEqual(str(sat), "SAT-1")

    def test_ordering(self):
        Satellite.objects.create(name="Bravo")
        Satellite.objects.create(name="Alpha")
        names = list(Satellite.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Alpha", "Bravo"])


class TagModelTest(TestCase):
    def test_slug_auto_generated(self):
        tag = Tag.objects.create(name="Bus Checkout")
        self.assertEqual(tag.slug, "bus-checkout")

    def test_str(self):
        tag = Tag.objects.create(name="Thermal")
        self.assertEqual(str(tag), "Thermal")


class ProcedureModelTest(TestCase):
    def test_str(self):
        proc = Procedure.objects.create(name="Checkout", version="1.0", yaml_file="checkout.yaml")
        self.assertEqual(str(proc), "Checkout (1.0)")

    def test_tags_m2m(self):
        proc = Procedure.objects.create(name="Test", version="1", yaml_file="test.yaml")
        tag = Tag.objects.create(name="Safety")
        proc.tags.add(tag)
        self.assertIn(tag, proc.tags.all())


class ProcedureRunModelTest(TestCase):
    def setUp(self):
        self.sat = Satellite.objects.create(name="SAT-1")
        self.proc = Procedure.objects.create(name="Test", version="1", yaml_file="test.yaml")
        self.user = User.objects.create_user("operator", password="pass")

    def test_default_status(self):
        run = ProcedureRun.objects.create(satellite=self.sat, procedure=self.proc, operator=self.user)
        self.assertEqual(run.status, ProcedureRun.STATUS_RUNNING)

    def test_str(self):
        run = ProcedureRun.objects.create(satellite=self.sat, procedure=self.proc)
        self.assertIn("SAT-1", str(run))
        self.assertIn("RUNNING", str(run))


class StepExecutionModelTest(TestCase):
    def setUp(self):
        sat = Satellite.objects.create(name="SAT-1")
        proc = Procedure.objects.create(name="Test", version="1", yaml_file="test.yaml")
        self.run = ProcedureRun.objects.create(satellite=sat, procedure=proc)

    def test_create_step(self):
        step = StepExecution.objects.create(run=self.run, step_id="1", status="PASS")
        self.assertEqual(step.step_id, "1")
        self.assertEqual(step.status, "PASS")


class DashboardViewTest(TestCase):
    def test_dashboard_loads(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_search(self):
        response = self.client.get(reverse("dashboard"), {"q": "test"})
        self.assertEqual(response.status_code, 200)


class ProcedureListViewTest(TestCase):
    def test_procedure_list_loads(self):
        response = self.client.get(reverse("procedure_list"))
        self.assertEqual(response.status_code, 200)


class HistoryViewTest(TestCase):
    def test_history_loads(self):
        response = self.client.get(reverse("history"))
        self.assertEqual(response.status_code, 200)


class StartViewTest(TestCase):
    def test_start_requires_login(self):
        response = self.client.get(reverse("start"))
        self.assertEqual(response.status_code, 302)

    def test_start_loads_when_authenticated(self):
        User.objects.create_user("op", password="pass")
        self.client.login(username="op", password="pass")
        response = self.client.get(reverse("start"))
        self.assertEqual(response.status_code, 200)


class SeedCommandTest(TestCase):
    def test_seed_procedures(self):
        from django.core.management import call_command
        call_command("seed_procedures")
        self.assertTrue(Satellite.objects.exists())
        self.assertTrue(Procedure.objects.exists())

    def test_seed_all(self):
        from django.core.management import call_command
        call_command("seed_all")
        self.assertTrue(Satellite.objects.exists())
