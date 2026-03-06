from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('start/', views.start, name='start'),
    path('run/<int:run_id>/', views.run_procedure, name='run'),
    path('history/', views.history, name='history'),
]
