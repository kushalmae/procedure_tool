from django.urls import path

from . import admin_views

urlpatterns = [
    path('', admin_views.mission_settings, name='mission_settings'),
    path('members/', admin_views.mission_members, name='mission_members'),
    path('members/add/', admin_views.mission_member_add, name='mission_member_add'),
    path('members/<int:membership_id>/role/', admin_views.mission_member_role, name='mission_member_role'),
    path('members/<int:membership_id>/remove/', admin_views.mission_member_remove, name='mission_member_remove'),
]
