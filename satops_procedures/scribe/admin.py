from django.contrib import admin
from .models import Role, EventCategory, ScribeTag, Shift, MissionLogEntry


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(EventCategory)
class EventCategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(ScribeTag)
class ScribeTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ['name']}


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['id', 'start_time', 'end_time']
    list_filter = ['start_time']
    date_hierarchy = 'start_time'


@admin.register(MissionLogEntry)
class MissionLogEntryAdmin(admin.ModelAdmin):
    list_display = ['id', 'timestamp', 'role', 'satellite', 'category', 'severity', 'created_by']
    list_filter = ['role', 'category', 'severity', 'shift']
    search_fields = ['description', 'role__name', 'category__name']
    date_hierarchy = 'timestamp'
    filter_horizontal = ['tags']
