from django.conf import settings
from django.db import models


class Anomaly(models.Model):
    STATUS_NEW = 'NEW'
    STATUS_INVESTIGATING = 'INVESTIGATING'
    STATUS_MITIGATED = 'MITIGATED'
    STATUS_RESOLVED = 'RESOLVED'
    STATUS_CLOSED = 'CLOSED'
    STATUS_CHOICES = [
        (STATUS_NEW, 'New'),
        (STATUS_INVESTIGATING, 'Investigating'),
        (STATUS_MITIGATED, 'Mitigated'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_CLOSED, 'Closed'),
    ]

    SEVERITY_L1 = 'L1'
    SEVERITY_L2 = 'L2'
    SEVERITY_L3 = 'L3'
    SEVERITY_L4 = 'L4'
    SEVERITY_L5 = 'L5'
    SEVERITY_CHOICES = [
        (SEVERITY_L1, 'L1 — Informational'),
        (SEVERITY_L2, 'L2 — Minor'),
        (SEVERITY_L3, 'L3 — Operational'),
        (SEVERITY_L4, 'L4 — Major'),
        (SEVERITY_L5, 'L5 — Critical'),
    ]

    title = models.CharField(max_length=200)
    satellite = models.ForeignKey(
        'procedures.Satellite',
        on_delete=models.PROTECT,
        related_name='anomalies',
    )
    subsystem = models.ForeignKey(
        'procedures.Subsystem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anomalies',
    )
    severity = models.CharField(
        max_length=5,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_L2,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
    )
    description = models.TextField(blank=True)
    detected_time = models.DateTimeField()

    root_cause = models.TextField(
        blank=True,
        help_text='Root cause summary documented at resolution.',
    )
    resolution_actions = models.TextField(
        blank=True,
        help_text='Actions taken to resolve the issue.',
    )
    recommendations = models.TextField(
        blank=True,
        help_text='Follow-up recommendations or lessons learned.',
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_anomalies',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-detected_time']
        verbose_name_plural = 'anomalies'

    def __str__(self):
        return f"ANOM-{self.pk} {self.title}"

    @property
    def is_open(self):
        return self.status not in (self.STATUS_RESOLVED, self.STATUS_CLOSED)

    @property
    def severity_rank(self):
        """Numeric rank for sorting: higher = more severe."""
        return {'L1': 1, 'L2': 2, 'L3': 3, 'L4': 4, 'L5': 5}.get(self.severity, 0)


class AnomalyTimelineEntry(models.Model):
    ENTRY_NOTE = 'NOTE'
    ENTRY_STATUS_CHANGE = 'STATUS_CHANGE'
    ENTRY_SEVERITY_CHANGE = 'SEVERITY_CHANGE'
    ENTRY_ACTION = 'ACTION'
    ENTRY_PROCEDURE = 'PROCEDURE'
    ENTRY_TYPE_CHOICES = [
        (ENTRY_NOTE, 'Note'),
        (ENTRY_STATUS_CHANGE, 'Status Change'),
        (ENTRY_SEVERITY_CHANGE, 'Severity Change'),
        (ENTRY_ACTION, 'Action Taken'),
        (ENTRY_PROCEDURE, 'Procedure Run'),
    ]

    anomaly = models.ForeignKey(
        Anomaly,
        on_delete=models.CASCADE,
        related_name='timeline_entries',
    )
    entry_type = models.CharField(
        max_length=20,
        choices=ENTRY_TYPE_CHOICES,
        default=ENTRY_NOTE,
    )
    body = models.TextField()
    old_value = models.CharField(max_length=50, blank=True)
    new_value = models.CharField(max_length=50, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anomaly_timeline_entries',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'anomaly timeline entries'

    def __str__(self):
        return f"{self.anomaly_id} — {self.get_entry_type_display()} — {self.created_at}"
