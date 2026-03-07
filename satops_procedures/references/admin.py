from django.contrib import admin

from .models import ReferenceEntry, Subsystem


@admin.register(Subsystem)
class SubsystemAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(ReferenceEntry)
class ReferenceEntryAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'document_type', 'subsystem', 'section',
        'version', 'updated_at',
    ]
    list_filter = ['subsystem', 'document_type']
    search_fields = ['title', 'section', 'location', 'user_notes']
    readonly_fields = ['created_at', 'updated_at']
