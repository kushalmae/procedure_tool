from django.contrib import admin
from .models import Subsystem, AnomalyType, Anomaly, AnomalyNote


@admin.register(Subsystem)
class SubsystemAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(AnomalyType)
class AnomalyTypeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Anomaly)
class AnomalyAdmin(admin.ModelAdmin):
    list_display = ['id', 'satellite', 'subsystem', 'anomaly_type', 'severity', 'status', 'detection_time', 'reported_by']
    list_filter = ['satellite', 'subsystem', 'severity', 'status']
    search_fields = ['description', 'satellite__name', 'subsystem__name']
    date_hierarchy = 'detection_time'


@admin.register(AnomalyNote)
class AnomalyNoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'anomaly', 'created_at', 'created_by']
    list_filter = ['created_at']
    search_fields = ['body']
    date_hierarchy = 'created_at'
