from django.conf import settings
from django.db import models


class Satellite(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Tag(models.Model):
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


class Procedure(models.Model):
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=20)
    yaml_file = models.CharField(max_length=200)
    tags = models.ManyToManyField('Tag', related_name='procedures', blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.version})"


class ProcedureRun(models.Model):
    STATUS_RUNNING = 'RUNNING'
    STATUS_PASS = 'PASS'
    STATUS_FAIL = 'FAIL'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = [
        (STATUS_RUNNING, 'Running'),
        (STATUS_PASS, 'Pass'),
        (STATUS_FAIL, 'Fail'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    satellite = models.ForeignKey(Satellite, on_delete=models.CASCADE)
    procedure = models.ForeignKey(Procedure, on_delete=models.CASCADE)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    operator_name = models.CharField(max_length=100, blank=True)

    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RUNNING)
    run_notes = models.TextField(blank=True, help_text='Handover or anomaly notes for this run.')

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.satellite.name} — {self.procedure.name} ({self.status})"


class StepExecution(models.Model):
    run = models.ForeignKey(ProcedureRun, on_delete=models.CASCADE, related_name='step_executions')
    step_id = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    status = models.CharField(max_length=20)
    input_value = models.CharField(max_length=200, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.run_id} step {self.step_id} — {self.status}"
