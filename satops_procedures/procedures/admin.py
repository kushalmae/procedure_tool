from django.contrib import admin
from .models import Satellite, Procedure, ProcedureRun, StepExecution


@admin.register(Satellite)
class SatelliteAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Procedure)
class ProcedureAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'yaml_file']
    search_fields = ['name', 'yaml_file']


@admin.register(ProcedureRun)
class ProcedureRunAdmin(admin.ModelAdmin):
    list_display = ['id', 'satellite', 'procedure', 'operator', 'operator_name', 'status', 'start_time', 'end_time']
    list_filter = ['status', 'satellite', 'procedure']
    search_fields = ['satellite__name', 'procedure__name', 'operator_name']
    date_hierarchy = 'start_time'


@admin.register(StepExecution)
class StepExecutionAdmin(admin.ModelAdmin):
    list_display = ['id', 'run', 'step_id', 'status', 'input_value', 'timestamp']
    list_filter = ['status', 'run']
    search_fields = ['step_id', 'notes', 'input_value']
    date_hierarchy = 'timestamp'
