from django.contrib import admin
from .models import Subsystem, AlertDefinition


@admin.register(Subsystem)
class SubsystemAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(AlertDefinition)
class AlertDefinitionAdmin(admin.ModelAdmin):
    list_display = [
        'parameter', 'subsystem', 'severity',
        'warning_threshold', 'critical_threshold', 'version', 'updated_at',
    ]
    list_filter = ['subsystem', 'severity']
    search_fields = ['parameter', 'description', 'recommended_response']
    raw_id_fields = ['procedure']
    readonly_fields = ['version', 'created_at', 'updated_at']
