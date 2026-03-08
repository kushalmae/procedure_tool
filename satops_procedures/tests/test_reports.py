from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from missions.models import Mission

User = get_user_model()


class ReportsDashboardTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_dashboard_loads(self):
        resp = self.client.get(reverse('reports_dashboard', kwargs={'mission_slug': 'test'}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Reports')


class ProcedurePerformanceReportTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_loads_empty(self):
        resp = self.client.get(reverse('report_procedure_performance', kwargs={'mission_slug': 'test'}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Procedure Performance')

    def test_with_date_filter(self):
        resp = self.client.get(
            reverse('report_procedure_performance', kwargs={'mission_slug': 'test'}),
            {'from': '2025-01-01', 'to': '2025-12-31'},
        )
        self.assertEqual(resp.status_code, 200)


class AnomalySummaryReportTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_loads(self):
        resp = self.client.get(reverse('report_anomaly_summary', kwargs={'mission_slug': 'test'}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Anomaly Summary')


class OperatorWorkloadReportTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_loads(self):
        resp = self.client.get(reverse('report_operator_workload', kwargs={'mission_slug': 'test'}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Operator Workload')


class MissionActivityReportTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_loads(self):
        resp = self.client.get(reverse('report_mission_activity', kwargs={'mission_slug': 'test'}))
        self.assertEqual(resp.status_code, 200)


class ReportCSVExportTest(TestCase):
    def setUp(self):
        self.mission = Mission.objects.create(name='Test', slug='test', color='#3B82F6')

    def test_procedure_performance_csv(self):
        resp = self.client.get(
            reverse('report_csv_export', kwargs={'mission_slug': 'test'}),
            {'report': 'procedure_performance'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')

    def test_anomaly_summary_csv(self):
        resp = self.client.get(
            reverse('report_csv_export', kwargs={'mission_slug': 'test'}),
            {'report': 'anomaly_summary'},
        )
        self.assertEqual(resp.status_code, 200)

    def test_operator_workload_csv(self):
        resp = self.client.get(
            reverse('report_csv_export', kwargs={'mission_slug': 'test'}),
            {'report': 'operator_workload'},
        )
        self.assertEqual(resp.status_code, 200)

    def test_mission_activity_csv(self):
        resp = self.client.get(
            reverse('report_csv_export', kwargs={'mission_slug': 'test'}),
            {'report': 'mission_activity'},
        )
        self.assertEqual(resp.status_code, 200)

    def test_unknown_report_type_returns_empty_csv(self):
        resp = self.client.get(
            reverse('report_csv_export', kwargs={'mission_slug': 'test'}),
            {'report': 'nonexistent'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
