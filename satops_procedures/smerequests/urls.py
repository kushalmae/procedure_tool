from django.urls import path

from . import views

urlpatterns = [
    path('', views.request_list, name='sme_request_list'),
    path('queue/', views.ops_queue, name='sme_ops_queue'),
    path('new/', views.create_request, name='sme_request_create'),
    path('<int:request_id>/', views.request_detail, name='sme_request_detail'),
]
