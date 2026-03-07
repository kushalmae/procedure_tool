from django.urls import path

from . import views

urlpatterns = [
    path('', views.alert_list, name='handbook_alert_list'),
    path('add/', views.alert_create, name='handbook_alert_create'),
    path('<int:alert_id>/', views.alert_detail, name='handbook_alert_detail'),
    path('<int:alert_id>/edit/', views.alert_edit, name='handbook_alert_edit'),
    path('<int:alert_id>/delete/', views.alert_delete, name='handbook_alert_delete'),
]
