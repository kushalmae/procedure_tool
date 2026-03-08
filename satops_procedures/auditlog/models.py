from django.conf import settings
from django.db import models


class AuditEntry(models.Model):
    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    ACTION_RUN_START = 'RUN_START'
    ACTION_RUN_COMPLETE = 'RUN_COMPLETE'
    ACTION_RUN_ABORT = 'RUN_ABORT'
    ACTION_STATUS_CHANGE = 'STATUS_CHANGE'
    ACTION_IMPORT = 'IMPORT'
    ACTION_EXPORT = 'EXPORT'
    ACTION_LOGIN = 'LOGIN'
    ACTION_LOGOUT = 'LOGOUT'
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Create'),
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
        (ACTION_RUN_START, 'Run Started'),
        (ACTION_RUN_COMPLETE, 'Run Completed'),
        (ACTION_RUN_ABORT, 'Run Aborted'),
        (ACTION_STATUS_CHANGE, 'Status Change'),
        (ACTION_IMPORT, 'CSV Import'),
        (ACTION_EXPORT, 'CSV Export'),
        (ACTION_LOGIN, 'Login'),
        (ACTION_LOGOUT, 'Logout'),
    ]

    mission = models.ForeignKey(
        'missions.Mission',
        on_delete=models.CASCADE,
        related_name='audit_entries',
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_entries',
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(
        max_length=80,
        help_text='e.g. Procedure, Anomaly, AlertDefinition',
    )
    object_id = models.CharField(max_length=40, blank=True)
    object_repr = models.CharField(
        max_length=200,
        blank=True,
        help_text='Human-readable representation at time of action',
    )
    detail = models.TextField(
        blank=True,
        help_text='Additional context: changed fields, notes, etc.',
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'audit entries'
        indexes = [
            models.Index(fields=['mission', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action']),
            models.Index(fields=['model_name']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else 'system'
        return f"{self.timestamp} {user_str} {self.get_action_display()} {self.model_name} {self.object_repr}"
