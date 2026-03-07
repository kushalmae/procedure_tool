import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import CommandDefinition, CommandInput, TelemetryDefinition, TelemetryEnum

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def command_list(request):
    if request.GET.get('clear'):
        if 'cmdtlm_cmd_filters' in request.session:
            del request.session['cmdtlm_cmd_filters']
        return redirect('cmdtlm_command_list')

    SORT_OPTIONS = [
        'subsystem',
        'name',
        '-name',
        'command_id',
        'category',
        '-updated_at',
    ]
    saved = request.session.get('cmdtlm_cmd_filters') or {}
    subsystem = request.GET.get('subsystem', saved.get('subsystem', ''))
    category = request.GET.get('category', saved.get('category', ''))
    q = (request.GET.get('q') or saved.get('q') or '').strip()
    sort = request.GET.get('sort', saved.get('sort', 'subsystem'))
    if sort not in SORT_OPTIONS:
        sort = 'subsystem'

    has_filters = any([subsystem, category, q])
    if has_filters or sort != 'subsystem':
        request.session['cmdtlm_cmd_filters'] = {
            'subsystem': subsystem or '',
            'category': category or '',
            'q': q or '',
            'sort': sort,
        }

    commands = (
        CommandDefinition.objects
        .annotate(num_inputs=Count('inputs'))
        .order_by(sort, 'name')
    )
    if subsystem:
        commands = commands.filter(subsystem=subsystem)
    if category:
        commands = commands.filter(category=category)
    if q:
        commands = commands.filter(
            Q(name__icontains=q)
            | Q(command_id__icontains=q)
            | Q(subsystem__icontains=q)
            | Q(description__icontains=q)
            | Q(category__icontains=q)
        )

    commands = commands[:500]

    subsystems = (
        CommandDefinition.objects
        .values_list('subsystem', flat=True)
        .exclude(subsystem='')
        .distinct()
        .order_by('subsystem')
    )
    categories = (
        CommandDefinition.objects
        .values_list('category', flat=True)
        .exclude(category='')
        .distinct()
        .order_by('category')
    )

    context = {
        'commands': commands,
        'subsystems': subsystems,
        'categories': categories,
        'filter_subsystem': subsystem or None,
        'filter_category': category or None,
        'search_query': q,
        'sort': sort,
    }
    return render(request, 'cmdtlm/command_list.html', context)


def command_detail(request, command_id):
    command = get_object_or_404(CommandDefinition, pk=command_id)
    inputs = command.inputs.all()
    return render(request, 'cmdtlm/command_detail.html', {
        'command': command,
        'inputs': inputs,
    })


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

def telemetry_list(request):
    if request.GET.get('clear'):
        if 'cmdtlm_tlm_filters' in request.session:
            del request.session['cmdtlm_tlm_filters']
        return redirect('cmdtlm_telemetry_list')

    SORT_OPTIONS = [
        'subsystem',
        'name',
        '-name',
        'mnemonic',
        'data_type',
        '-updated_at',
    ]
    saved = request.session.get('cmdtlm_tlm_filters') or {}
    subsystem = request.GET.get('subsystem', saved.get('subsystem', ''))
    data_type = request.GET.get('data_type', saved.get('data_type', ''))
    q = (request.GET.get('q') or saved.get('q') or '').strip()
    sort = request.GET.get('sort', saved.get('sort', 'subsystem'))
    if sort not in SORT_OPTIONS:
        sort = 'subsystem'

    has_filters = any([subsystem, data_type, q])
    if has_filters or sort != 'subsystem':
        request.session['cmdtlm_tlm_filters'] = {
            'subsystem': subsystem or '',
            'data_type': data_type or '',
            'q': q or '',
            'sort': sort,
        }

    telemetry = (
        TelemetryDefinition.objects
        .annotate(num_enums=Count('enums'))
        .order_by(sort, 'name')
    )
    if subsystem:
        telemetry = telemetry.filter(subsystem=subsystem)
    if data_type:
        telemetry = telemetry.filter(data_type=data_type)
    if q:
        telemetry = telemetry.filter(
            Q(name__icontains=q)
            | Q(mnemonic__icontains=q)
            | Q(apid__icontains=q)
            | Q(subsystem__icontains=q)
            | Q(description__icontains=q)
        )

    telemetry = telemetry[:500]

    subsystems = (
        TelemetryDefinition.objects
        .values_list('subsystem', flat=True)
        .exclude(subsystem='')
        .distinct()
        .order_by('subsystem')
    )
    data_types = (
        TelemetryDefinition.objects
        .values_list('data_type', flat=True)
        .exclude(data_type='')
        .distinct()
        .order_by('data_type')
    )

    context = {
        'telemetry': telemetry,
        'subsystems': subsystems,
        'data_types': data_types,
        'filter_subsystem': subsystem or None,
        'filter_data_type': data_type or None,
        'search_query': q,
        'sort': sort,
    }
    return render(request, 'cmdtlm/telemetry_list.html', context)


def telemetry_detail(request, telemetry_id):
    tlm = get_object_or_404(TelemetryDefinition, pk=telemetry_id)
    enums = tlm.enums.all()
    return render(request, 'cmdtlm/telemetry_detail.html', {
        'tlm': tlm,
        'enums': enums,
    })


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------

def _decode_file(uploaded):
    """Read an uploaded file and return text content."""
    raw = uploaded.read()
    try:
        return raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        return raw.decode('latin-1')


def _normalize_header(header):
    """Lowercase and strip whitespace from header name."""
    return header.strip().lower().replace(' ', '_')


def _get(row, *keys, default=''):
    """Return the first non-empty value found for any of the given keys."""
    for key in keys:
        val = row.get(key, '').strip()
        if val:
            return val
    return default


@login_required
def csv_import(request):
    if request.method == 'POST':
        action = request.POST.get('action', '')
        uploaded = request.FILES.get('csv_file')

        if not uploaded:
            messages.error(request, 'Please select a CSV file to import.')
            return redirect('cmdtlm_csv_import')

        try:
            text = _decode_file(uploaded)
            reader = csv.DictReader(io.StringIO(text))
            reader.fieldnames = [_normalize_header(h) for h in reader.fieldnames]
        except Exception as e:
            messages.error(request, f'Could not read CSV: {e}')
            return redirect('cmdtlm_csv_import')

        rows = list(reader)
        if not rows:
            messages.warning(request, 'CSV file is empty.')
            return redirect('cmdtlm_csv_import')

        count = 0
        if action == 'commands':
            count = _import_commands(rows)
            messages.success(request, f'Imported {count} command definition(s).')
        elif action == 'command_inputs':
            count = _import_command_inputs(rows)
            messages.success(request, f'Imported {count} command input(s).')
        elif action == 'telemetry':
            count = _import_telemetry(rows)
            messages.success(request, f'Imported {count} telemetry definition(s).')
        elif action == 'telemetry_enums':
            count = _import_telemetry_enums(rows)
            messages.success(request, f'Imported {count} telemetry enum(s).')
        else:
            messages.error(request, 'Unknown import type.')

        return redirect('cmdtlm_csv_import')

    return render(request, 'cmdtlm/csv_import.html')


def _import_commands(rows):
    count = 0
    for row in rows:
        name = _get(row, 'name', 'command_name', 'command')
        if not name:
            continue
        CommandDefinition.objects.update_or_create(
            name=name,
            defaults={
                'command_id': _get(row, 'command_id', 'opcode', 'id'),
                'subsystem': _get(row, 'subsystem'),
                'description': _get(row, 'description'),
                'category': _get(row, 'category', 'group', 'command_group'),
                'notes': _get(row, 'notes'),
            },
        )
        count += 1
    return count


def _import_command_inputs(rows):
    count = 0
    for row in rows:
        cmd_name = _get(row, 'command_name', 'command', 'name')
        input_name = _get(row, 'input_name', 'input', 'argument', 'parameter')
        if not cmd_name or not input_name:
            continue
        try:
            cmd = CommandDefinition.objects.get(name=cmd_name)
        except CommandDefinition.DoesNotExist:
            continue

        order_str = _get(row, 'order', 'position', 'index', default='0')
        try:
            order_val = int(order_str)
        except ValueError:
            order_val = 0

        CommandInput.objects.update_or_create(
            command=cmd,
            name=input_name,
            defaults={
                'order': order_val,
                'data_type': _get(row, 'data_type', 'type'),
                'description': _get(row, 'description'),
                'default_value': _get(row, 'default_value', 'default'),
                'constraints': _get(row, 'constraints', 'range', 'valid_range'),
            },
        )
        count += 1
    return count


def _import_telemetry(rows):
    count = 0
    for row in rows:
        name = _get(row, 'name', 'telemetry_name', 'parameter')
        if not name:
            continue
        TelemetryDefinition.objects.update_or_create(
            name=name,
            defaults={
                'mnemonic': _get(row, 'mnemonic'),
                'apid': _get(row, 'apid', 'packet', 'packet_reference'),
                'subsystem': _get(row, 'subsystem'),
                'description': _get(row, 'description'),
                'data_type': _get(row, 'data_type', 'type', 'format'),
                'units': _get(row, 'units', 'unit'),
                'notes': _get(row, 'notes'),
            },
        )
        count += 1
    return count


def _import_telemetry_enums(rows):
    count = 0
    for row in rows:
        tlm_name = _get(row, 'telemetry_name', 'telemetry', 'parameter', 'name')
        mnemonic = _get(row, 'mnemonic')
        value = _get(row, 'value', 'enum_value', 'raw_value')
        label = _get(row, 'label', 'enum_label', 'meaning')
        if not value or not label:
            continue

        tlm = None
        if mnemonic:
            tlm = TelemetryDefinition.objects.filter(mnemonic=mnemonic).first()
        if not tlm and tlm_name:
            tlm = TelemetryDefinition.objects.filter(name=tlm_name).first()
        if not tlm:
            continue

        TelemetryEnum.objects.update_or_create(
            telemetry=tlm,
            value=value,
            defaults={
                'label': label,
                'description': _get(row, 'description'),
            },
        )
        count += 1
    return count
