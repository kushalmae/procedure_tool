from django.contrib import admin

from .models import RequestNote, RequestType, SMERequest


@admin.register(RequestType)
class RequestTypeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(SMERequest)
class SMERequestAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'satellite', 'request_type', 'priority',
        'status', 'requested_by', 'assigned_to', 'created_at',
    ]
    list_filter = ['status', 'priority', 'satellite', 'request_type']
    search_fields = ['title', 'description']
    date_hierarchy = 'created_at'


@admin.register(RequestNote)
class RequestNoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'request', 'created_at', 'created_by']
    list_filter = ['created_at']
    search_fields = ['body']
    date_hierarchy = 'created_at'
