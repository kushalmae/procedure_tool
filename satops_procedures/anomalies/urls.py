from django.urls import path
from . import views

urlpatterns = [
    path('', views.registry, name='anomalies_registry'),
    path('add/', views.add_anomaly, name='anomalies_add'),
    path('<int:anomaly_id>/', views.anomaly_detail, name='anomalies_detail'),
]
