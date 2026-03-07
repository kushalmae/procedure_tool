from django.urls import path

from . import views

urlpatterns = [
    path('', views.anomaly_list, name='anomalies_list'),
    path('create/', views.anomaly_create, name='anomalies_create'),
    path('export/', views.anomaly_csv_export, name='anomalies_csv_export'),
    path('import/', views.anomaly_csv_import, name='anomalies_csv_import'),
    path('<int:anomaly_id>/', views.anomaly_detail, name='anomalies_detail'),
    path('<int:anomaly_id>/add-note/', views.anomaly_add_note, name='anomalies_add_note'),
    path('<int:anomaly_id>/update/', views.anomaly_update, name='anomalies_update'),
    path('<int:anomaly_id>/close/', views.anomaly_close, name='anomalies_close'),
]
