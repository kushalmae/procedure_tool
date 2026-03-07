from django.db import models


class CommandDefinition(models.Model):
    name = models.CharField(max_length=200)
    command_id = models.CharField(
        max_length=80,
        blank=True,
        help_text='Command opcode or numeric identifier',
    )
    subsystem = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=120,
        blank=True,
        help_text='Command group or category',
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['subsystem', 'name']
        indexes = [
            models.Index(fields=['subsystem']),
            models.Index(fields=['name']),
            models.Index(fields=['command_id']),
        ]

    def __str__(self):
        label = self.name
        if self.command_id:
            label += f' ({self.command_id})'
        return label

    @property
    def input_count(self):
        return self.inputs.count()


class CommandInput(models.Model):
    command = models.ForeignKey(
        CommandDefinition,
        on_delete=models.CASCADE,
        related_name='inputs',
    )
    name = models.CharField(max_length=200)
    order = models.PositiveIntegerField(
        default=0,
        help_text='Position of this input in the command argument list',
    )
    data_type = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    default_value = models.CharField(max_length=200, blank=True)
    constraints = models.TextField(
        blank=True,
        help_text='Valid ranges, enums, or other constraints',
    )

    class Meta:
        ordering = ['command', 'order', 'name']
        indexes = [
            models.Index(fields=['command']),
        ]

    def __str__(self):
        return f'{self.command.name} / {self.name}'


class TelemetryDefinition(models.Model):
    name = models.CharField(max_length=200)
    mnemonic = models.CharField(max_length=120, blank=True)
    apid = models.CharField(
        max_length=120,
        blank=True,
        help_text='APID or packet reference',
    )
    subsystem = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    data_type = models.CharField(max_length=80, blank=True)
    units = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['subsystem', 'name']
        indexes = [
            models.Index(fields=['subsystem']),
            models.Index(fields=['name']),
            models.Index(fields=['mnemonic']),
        ]

    def __str__(self):
        if self.mnemonic:
            return f'{self.name} ({self.mnemonic})'
        return self.name

    @property
    def has_enums(self):
        return self.enums.exists()


class TelemetryEnum(models.Model):
    telemetry = models.ForeignKey(
        TelemetryDefinition,
        on_delete=models.CASCADE,
        related_name='enums',
    )
    value = models.CharField(
        max_length=80,
        help_text='Raw numeric or coded value',
    )
    label = models.CharField(
        max_length=200,
        help_text='Human-readable meaning',
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['telemetry', 'value']
        indexes = [
            models.Index(fields=['telemetry']),
        ]

    def __str__(self):
        return f'{self.telemetry.mnemonic or self.telemetry.name}: {self.value} = {self.label}'
