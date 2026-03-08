from django.urls import path

from . import views

urlpatterns = [
    path('', views.reports_dashboard, name='reports_dashboard'),
    path('procedure-performance/', views.procedure_performance_report, name='report_procedure_performance'),
    path('anomaly-summary/', views.anomaly_summary_report, name='report_anomaly_summary'),
    path('operator-workload/', views.operator_workload_report, name='report_operator_workload'),
    path('mission-activity/', views.mission_activity_report, name='report_mission_activity'),
    path('export/csv/', views.report_csv_export, name='report_csv_export'),
]
