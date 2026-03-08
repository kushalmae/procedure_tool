from django.db import models


class Subsystem(models.Model):
    mission = models.ForeignKey(
        'missions.Mission', on_delete=models.CASCADE,
        related_name='handbook_subsystems', null=True, blank=True,
    )
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class AlertDefinition(models.Model):
    SEVERITY_WARNING = 'WARNING'
    SEVERITY_CRITICAL = 'CRITICAL'
    SEVERITY_CHOICES = [
        (SEVERITY_WARNING, 'Warning'),
        (SEVERITY_CRITICAL, 'Critical'),
    ]

    mission = models.ForeignKey(
        'missions.Mission', on_delete=models.CASCADE,
        related_name='alert_definitions', null=True, blank=True,
    )
    parameter = models.CharField(max_length=120)
    mnemonic = models.CharField(
        max_length=80,
        blank=True,
        help_text='Telemetry mnemonic or short code (e.g. BAT_TEMP, V_BUS)',
    )
    mnemonic_description = models.TextField(
        blank=True,
        help_text='Extended description of what this mnemonic is (e.g. engineering unit, where it appears in telemetry)',
    )
    user_notes = models.TextField(
        blank=True,
        help_text='Operator or team notes (e.g. observed behavior, fleet-specific notes)',
    )
    apids = models.CharField(
        max_length=200,
        blank=True,
        help_text='APID(s) this parameter can come down on (e.g. 0x0801, 0x0802 or HK, Science)',
    )
    subsystem = models.ForeignKey(
        Subsystem,
        on_delete=models.PROTECT,
        related_name='alert_definitions',
    )
    description = models.TextField(help_text='Alert meaning and operational impact')
    alert_conditions = models.TextField(blank=True, help_text='When/how the alert triggers')
    warning_threshold = models.CharField(max_length=80, blank=True)
    critical_threshold = models.CharField(max_length=80, blank=True)
    recommended_response = models.TextField(
        blank=True,
        help_text='Operator actions or procedure reference',
    )
    procedure = models.ForeignKey(
        'procedures.Procedure',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handbook_alerts',
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_WARNING,
    )
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['subsystem__name', 'parameter']
        indexes = [
            models.Index(fields=['subsystem']),
            models.Index(fields=['parameter']),
            models.Index(fields=['severity']),
        ]

    def __str__(self):
        return f"{self.parameter} ({self.subsystem})"

    def save(self, *args, **kwargs):
        if self.pk:
            existing = AlertDefinition.objects.get(pk=self.pk)
            if (
                existing.parameter != self.parameter
                or                 existing.mnemonic != self.mnemonic
                or existing.mnemonic_description != self.mnemonic_description
                or existing.user_notes != self.user_notes
                or existing.apids != self.apids
                or existing.subsystem_id != self.subsystem_id
                or existing.description != self.description
                or existing.alert_conditions != self.alert_conditions
                or existing.warning_threshold != self.warning_threshold
                or existing.critical_threshold != self.critical_threshold
                or existing.recommended_response != self.recommended_response
                or existing.procedure_id != self.procedure_id
                or existing.severity != self.severity
            ):
                self.version = existing.version + 1
        super().save(*args, **kwargs)
