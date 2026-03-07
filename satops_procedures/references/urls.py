from django.urls import path

from . import views

urlpatterns = [
    path('', views.reference_list, name='reference_list'),
    path('add/', views.reference_create, name='reference_create'),
    path('import/', views.reference_csv_import, name='reference_csv_import'),
    path('export/', views.reference_csv_export, name='reference_csv_export'),
    path('<int:entry_id>/', views.reference_detail, name='reference_detail'),
    path('<int:entry_id>/edit/', views.reference_edit, name='reference_edit'),
    path('<int:entry_id>/delete/', views.reference_delete, name='reference_delete'),
]
