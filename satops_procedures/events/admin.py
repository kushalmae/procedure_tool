from django.contrib import admin

from .models import Event, EventTimelineEntry


class EventTimelineEntryInline(admin.TabularInline):
    model = EventTimelineEntry
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'satellite', 'subsystem', 'severity', 'status', 'detected_time', 'created_by']
    list_filter = ['satellite', 'subsystem', 'severity', 'status']
    search_fields = ['title', 'description', 'satellite__name']
    date_hierarchy = 'detected_time'
    inlines = [EventTimelineEntryInline]


@admin.register(EventTimelineEntry)
class EventTimelineEntryAdmin(admin.ModelAdmin):
    list_display = ['id', 'event', 'entry_type', 'created_at', 'created_by']
    list_filter = ['entry_type', 'created_at']
    search_fields = ['body']
    date_hierarchy = 'created_at'
