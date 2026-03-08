from django.urls import path

from . import views

urlpatterns = [
    path('', views.mission_selector, name='mission_selector'),
    path('new/', views.mission_create, name='mission_create'),
]
