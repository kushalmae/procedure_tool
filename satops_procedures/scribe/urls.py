from django.urls import path

from . import views

urlpatterns = [
    path('', views.timeline, name='scribe_timeline'),
    path('add/', views.add_entry, name='scribe_add_entry'),
    path('shifts/', views.shift_list, name='scribe_shift_list'),
    path('shifts/add/', views.shift_create, name='scribe_shift_create'),
    path('shifts/<int:shift_id>/', views.shift_detail, name='scribe_shift_detail'),
]
