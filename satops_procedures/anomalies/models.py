from django.db import models
from django.conf import settings


class Subsystem(models.Model):
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class AnomalyType(models.Model):
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'anomaly types'

    def __str__(self):
        return self.name


class Anomaly(models.Model):
    STATUS_NEW = 'NEW'
    STATUS_INVESTIGATING = 'INVESTIGATING'
    STATUS_MITIGATED = 'MITIGATED'
    STATUS_RESOLVED = 'RESOLVED'
    STATUS_CHOICES = [
        (STATUS_NEW, 'New'),
        (STATUS_INVESTIGATING, 'Investigating'),
        (STATUS_MITIGATED, 'Mitigated'),
        (STATUS_RESOLVED, 'Resolved'),
    ]

    SEVERITY_LOW = 'LOW'
    SEVERITY_MEDIUM = 'MEDIUM'
    SEVERITY_HIGH = 'HIGH'
    SEVERITY_CRITICAL = 'CRITICAL'
    SEVERITY_CHOICES = [
        (SEVERITY_LOW, 'Low'),
        (SEVERITY_MEDIUM, 'Medium'),
        (SEVERITY_HIGH, 'High'),
        (SEVERITY_CRITICAL, 'Critical'),
    ]

    IMPACT_NONE = 'NONE'
    IMPACT_MINOR = 'MINOR'
    IMPACT_MODERATE = 'MODERATE'
    IMPACT_MAJOR = 'MAJOR'
    IMPACT_MISSION_CRITICAL = 'MISSION_CRITICAL'
    IMPACT_CHOICES = [
        (IMPACT_NONE, 'None'),
        (IMPACT_MINOR, 'Minor'),
        (IMPACT_MODERATE, 'Moderate'),
        (IMPACT_MAJOR, 'Major'),
        (IMPACT_MISSION_CRITICAL, 'Mission-Critical'),
    ]

    satellite = models.ForeignKey(
        'procedures.Satellite',
        on_delete=models.PROTECT,
        related_name='anomalies',
    )
    subsystem = models.ForeignKey(
        Subsystem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anomalies',
    )
    anomaly_type = models.ForeignKey(
        AnomalyType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anomalies',
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_MEDIUM,
    )
    detection_time = models.DateTimeField()
    operational_impact = models.CharField(
        max_length=20,
        choices=IMPACT_CHOICES,
        default=IMPACT_NONE,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reported_anomalies',
    )

    class Meta:
        ordering = ['-detection_time']
        verbose_name_plural = 'anomalies'

    def __str__(self):
        return f"{self.satellite} – {self.detection_time} ({self.status})"


class AnomalyNote(models.Model):
    anomaly = models.ForeignKey(
        Anomaly,
        on_delete=models.CASCADE,
        related_name='notes',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='anomaly_notes',
    )
    body = models.TextField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.anomaly_id} – {self.created_at}"
