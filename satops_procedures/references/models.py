from django.db import models


class Subsystem(models.Model):
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ReferenceEntry(models.Model):
    TYPE_ICD = 'ICD'
    TYPE_MANUAL = 'Manual'
    TYPE_GUIDE = 'Guide'
    TYPE_REFERENCE = 'Reference'
    TYPE_CHOICES = [
        (TYPE_ICD, 'ICD'),
        (TYPE_MANUAL, 'User Manual'),
        (TYPE_GUIDE, 'Guide'),
        (TYPE_REFERENCE, 'Reference'),
    ]

    title = models.CharField(max_length=200)
    document_type = models.CharField(max_length=40, choices=TYPE_CHOICES, default=TYPE_REFERENCE)
    subsystem = models.ForeignKey(
        Subsystem,
        on_delete=models.PROTECT,
        related_name='reference_entries',
    )
    section = models.CharField(
        max_length=200,
        blank=True,
        help_text='Section or topic within the document',
    )
    version = models.CharField(
        max_length=40,
        blank=True,
        help_text='Document version (e.g. v2.1)',
    )
    location = models.CharField(
        max_length=500,
        help_text='Link or path to the document (SharePoint, Git repo, internal drive, PDF, etc.)',
    )
    user_notes = models.TextField(
        blank=True,
        help_text='Operator or engineer notes for operational context',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['subsystem__name', 'title']
        verbose_name_plural = 'reference entries'
        indexes = [
            models.Index(fields=['subsystem']),
            models.Index(fields=['document_type']),
            models.Index(fields=['title']),
        ]

    def __str__(self):
        return f"{self.title} ({self.subsystem})"
