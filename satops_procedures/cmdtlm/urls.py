from django.urls import path

from . import views

urlpatterns = [
    path('', views.command_list, name='cmdtlm_command_list'),
    path('commands/<int:command_id>/', views.command_detail, name='cmdtlm_command_detail'),
    path('telemetry/', views.telemetry_list, name='cmdtlm_telemetry_list'),
    path('telemetry/<int:telemetry_id>/', views.telemetry_detail, name='cmdtlm_telemetry_detail'),
    path('import/', views.csv_import, name='cmdtlm_csv_import'),
]
