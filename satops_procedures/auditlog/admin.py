from django.contrib import admin

from .models import AuditEntry


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'model_name', 'object_repr', 'mission')
    list_filter = ('action', 'model_name', 'mission')
    search_fields = ('object_repr', 'detail', 'user__username')
    readonly_fields = (
        'mission', 'user', 'action', 'model_name', 'object_id',
        'object_repr', 'detail', 'ip_address', 'timestamp',
    )
    date_hierarchy = 'timestamp'
