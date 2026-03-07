from django.urls import path

from . import views

urlpatterns = [
    path('', views.entry_list, name='fdir_entry_list'),
    path('<int:entry_id>/', views.entry_detail, name='fdir_entry_detail'),
    path('add/', views.entry_create, name='fdir_entry_create'),
    path('<int:entry_id>/edit/', views.entry_edit, name='fdir_entry_edit'),
]
