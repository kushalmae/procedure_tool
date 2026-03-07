from django.contrib import admin

from .models import FDIREntry, Subsystem


@admin.register(Subsystem)
class SubsystemAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ['name']}


@admin.register(FDIREntry)
class FDIREntryAdmin(admin.ModelAdmin):
    list_display = ['name', 'subsystem', 'severity', 'fault_type', 'updated_at']
    list_filter = ['subsystem', 'severity']
    search_fields = ['name', 'fault_code', 'triggering_conditions', 'onboard_automated_response']
    filter_horizontal = ['operator_procedures']
    readonly_fields = ['created_at', 'updated_at']
