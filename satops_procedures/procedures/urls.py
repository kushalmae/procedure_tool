from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('start/', views.start, name='start'),
    path('procedures/', views.procedure_list, name='procedure_list'),
    path('procedure/review/', views.procedure_review, name='procedure_review'),
    path('procedure/create/', views.procedure_create, name='procedure_create'),
    path('procedure/<int:procedure_id>/edit/', views.procedure_edit, name='procedure_edit'),
    path('procedure/<int:procedure_id>/delete/', views.procedure_delete, name='procedure_delete'),
    path('run/<int:run_id>/', views.run_procedure, name='run'),
    path('run/<int:run_id>/summary/', views.run_summary, name='run_summary'),
    path('history/', views.history, name='history'),
]
