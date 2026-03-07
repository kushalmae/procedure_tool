from django.contrib import admin

from .models import CommandDefinition, CommandInput, TelemetryDefinition, TelemetryEnum


class CommandInputInline(admin.TabularInline):
    model = CommandInput
    extra = 1


@admin.register(CommandDefinition)
class CommandDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'command_id', 'subsystem', 'category', 'updated_at']
    list_filter = ['subsystem', 'category']
    search_fields = ['name', 'command_id', 'subsystem', 'description']
    inlines = [CommandInputInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CommandInput)
class CommandInputAdmin(admin.ModelAdmin):
    list_display = ['name', 'command', 'order', 'data_type']
    list_filter = ['data_type']
    search_fields = ['name', 'command__name']
    raw_id_fields = ['command']


class TelemetryEnumInline(admin.TabularInline):
    model = TelemetryEnum
    extra = 1


@admin.register(TelemetryDefinition)
class TelemetryDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'mnemonic', 'apid', 'subsystem', 'data_type', 'updated_at']
    list_filter = ['subsystem', 'data_type']
    search_fields = ['name', 'mnemonic', 'apid', 'subsystem', 'description']
    inlines = [TelemetryEnumInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TelemetryEnum)
class TelemetryEnumAdmin(admin.ModelAdmin):
    list_display = ['telemetry', 'value', 'label']
    search_fields = ['value', 'label', 'telemetry__name', 'telemetry__mnemonic']
    raw_id_fields = ['telemetry']
