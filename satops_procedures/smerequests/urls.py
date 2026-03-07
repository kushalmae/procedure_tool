from django.urls import path

from . import views

urlpatterns = [
    path('', views.request_list, name='sme_request_list'),
    path('queue/', views.ops_queue, name='sme_ops_queue'),
    path('new/', views.create_request, name='sme_request_create'),
    path('export/', views.request_csv_export, name='sme_request_csv_export'),
    path('import/', views.request_csv_import, name='sme_request_csv_import'),
    path('<int:request_id>/', views.request_detail, name='sme_request_detail'),
]
