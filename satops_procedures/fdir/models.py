from django.db import models


class Subsystem(models.Model):
    """Subsystem for FDIR classification (e.g. ADCS, Power, Thermal)."""
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class FDIREntry(models.Model):
    """FDIR definition: fault detection conditions, onboard response, operator procedure references."""
    SEVERITY_INFO = 'INFO'
    SEVERITY_WARNING = 'WARNING'
    SEVERITY_CRITICAL = 'CRITICAL'
    SEVERITY_CHOICES = [
        (SEVERITY_INFO, 'Info'),
        (SEVERITY_WARNING, 'Warning'),
        (SEVERITY_CRITICAL, 'Critical'),
    ]

    name = models.CharField(max_length=200, help_text='Fault name')
    fault_code = models.CharField(max_length=80, blank=True, help_text='Short identifier or code')
    subsystem = models.ForeignKey(
        Subsystem,
        on_delete=models.PROTECT,
        related_name='fdir_entries',
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_INFO,
        blank=True,
    )
    fault_type = models.CharField(max_length=80, blank=True)
    triggering_conditions = models.TextField(blank=True, help_text='When/how the fault is detected')
    detection_thresholds = models.TextField(blank=True, help_text='Thresholds or criteria')
    onboard_automated_response = models.TextField(
        blank=True,
        help_text='What the spacecraft does automatically',
    )
    operator_procedures = models.ManyToManyField(
        'procedures.Procedure',
        related_name='fdir_entries',
        blank=True,
        help_text='Procedures operators should follow for recovery',
    )
    version = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['subsystem__name', 'name']
        verbose_name = 'FDIR entry'
        verbose_name_plural = 'FDIR entries'
        indexes = [
            models.Index(fields=['subsystem']),
            models.Index(fields=['severity']),
        ]

    def __str__(self):
        return f"{self.name} ({self.subsystem})"
