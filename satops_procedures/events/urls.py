from django.urls import path

from . import views

urlpatterns = [
    path('', views.event_list, name='events_list'),
    path('create/', views.event_create, name='events_create'),
    path('<int:event_id>/', views.event_detail, name='events_detail'),
    path('<int:event_id>/update/', views.event_update, name='events_update'),
    path('<int:event_id>/close/', views.event_close, name='events_close'),
]
