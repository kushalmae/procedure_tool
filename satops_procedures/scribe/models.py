from django.conf import settings
from django.db import models


class Role(models.Model):
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class EventCategory(models.Model):
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'event categories'

    def __str__(self):
        return self.name


class ScribeTag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Shift(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    handoff_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.start_time} – {self.end_time}"


class MissionLogEntry(models.Model):
    SEVERITY_INFO = 'INFO'
    SEVERITY_WARNING = 'WARNING'
    SEVERITY_CRITICAL = 'CRITICAL'
    SEVERITY_CHOICES = [
        (SEVERITY_INFO, 'Info'),
        (SEVERITY_WARNING, 'Warning'),
        (SEVERITY_CRITICAL, 'Critical'),
    ]

    timestamp = models.DateTimeField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scribe_entries',
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='entries')
    satellite = models.ForeignKey(
        'procedures.Satellite',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scribe_entries',
    )
    category = models.ForeignKey(
        EventCategory,
        on_delete=models.PROTECT,
        related_name='entries',
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_INFO,
    )
    description = models.TextField()
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entries',
    )
    tags = models.ManyToManyField(ScribeTag, related_name='entries', blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'mission log entries'

    def __str__(self):
        return f"{self.timestamp} {self.role} – {self.description[:50]}"


class EntryTemplate(models.Model):
    """Quick-entry template: pre-filled role, category, description, severity for one-click log entries."""
    name = models.CharField(max_length=120, help_text='Short label (e.g. Pass complete, Contact logged)')
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entry_templates',
    )
    category = models.ForeignKey(
        EventCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entry_templates',
    )
    default_description = models.TextField(
        blank=True,
        help_text='Pre-filled description; user can edit before saving.',
    )
    default_severity = models.CharField(
        max_length=20,
        choices=MissionLogEntry.SEVERITY_CHOICES,
        default=MissionLogEntry.SEVERITY_INFO,
    )
    display_order = models.PositiveIntegerField(default=0, help_text='Lower = first in list.')

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name
