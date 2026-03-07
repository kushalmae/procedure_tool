from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from procedures.models import Procedure

from .models import FDIREntry, Subsystem


def _int_or_none(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def entry_list(request):
    """List FDIR entries with search and filters (subsystem, severity, fault_type)."""
    if request.GET.get('clear'):
        if 'fdir_filters' in request.session:
            del request.session['fdir_filters']
        return redirect('fdir_entry_list')

    FDIR_SORT_OPTIONS = [
        'subsystem__name',
        'name',
        '-name',
        '-updated_at',
        'severity',
        '-severity',
    ]
    saved = request.session.get('fdir_filters') or {}
    subsystem_id = request.GET.get('subsystem', saved.get('subsystem', ''))
    severity = request.GET.get('severity', saved.get('severity', ''))
    fault_type = request.GET.get('fault_type', saved.get('fault_type', ''))
    q = (request.GET.get('q') or saved.get('q') or '').strip()
    sort = request.GET.get('sort', saved.get('sort', 'subsystem__name'))
    if sort not in FDIR_SORT_OPTIONS:
        sort = 'subsystem__name'

    has_filters = any([subsystem_id, severity, fault_type, q])
    if has_filters or sort != 'subsystem__name':
        request.session['fdir_filters'] = {
            'subsystem': subsystem_id or '',
            'severity': severity or '',
            'fault_type': fault_type or '',
            'q': q or '',
            'sort': sort,
        }

    entries = (
        FDIREntry.objects
        .select_related('subsystem')
        .prefetch_related('operator_procedures')
        .order_by(sort)
    )

    if subsystem_id:
        sid = _int_or_none(subsystem_id)
        if sid is not None:
            entries = entries.filter(subsystem_id=sid)
    if severity:
        entries = entries.filter(severity=severity)
    if fault_type:
        entries = entries.filter(fault_type__iexact=fault_type)
    if q:
        entries = entries.filter(
            Q(name__icontains=q)
            | Q(triggering_conditions__icontains=q)
            | Q(detection_thresholds__icontains=q)
            | Q(onboard_automated_response__icontains=q)
            | Q(fault_code__icontains=q)
        )

    entries = entries[:200]

    # Distinct fault_type values for filter dropdown (from existing data)
    fault_types = (
        FDIREntry.objects.values_list('fault_type', flat=True)
        .distinct()
        .order_by('fault_type')
    )
    fault_types = [t for t in fault_types if t]

    context = {
        'entries': entries,
        'subsystems': Subsystem.objects.all(),
        'filter_subsystem_id': _int_or_none(subsystem_id),
        'filter_severity': severity or None,
        'filter_fault_type': fault_type or None,
        'fault_type_choices': fault_types,
        'search_query': q,
        'sort': sort,
        'severity_choices': FDIREntry.SEVERITY_CHOICES,
    }
    return render(request, 'fdir/entry_list.html', context)


def entry_detail(request, entry_id):
    """FDIR entry detail: all fields and linked operator procedures."""
    entry = get_object_or_404(
        FDIREntry.objects.select_related('subsystem').prefetch_related('operator_procedures'),
        pk=entry_id,
    )
    return render(request, 'fdir/entry_detail.html', {'entry': entry})


@login_required
def entry_create(request):
    """Create FDIR entry (login required)."""
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        subsystem_id = request.POST.get('subsystem')
        if not name or not subsystem_id:
            messages.error(request, 'Name and subsystem are required.')
        else:
            subsystem = get_object_or_404(Subsystem, pk=subsystem_id)
            entry = FDIREntry(
                name=name,
                fault_code=(request.POST.get('fault_code') or '').strip(),
                subsystem=subsystem,
                severity=request.POST.get('severity') or FDIREntry.SEVERITY_INFO,
                fault_type=(request.POST.get('fault_type') or '').strip(),
                triggering_conditions=request.POST.get('triggering_conditions') or '',
                detection_thresholds=request.POST.get('detection_thresholds') or '',
                onboard_automated_response=request.POST.get('onboard_automated_response') or '',
                version=(request.POST.get('version') or '').strip(),
            )
            entry.save()
            procedure_ids = request.POST.getlist('operator_procedures')
            for pid in procedure_ids:
                try:
                    entry.operator_procedures.add(Procedure.objects.get(pk=pid))
                except (ValueError, Procedure.DoesNotExist):
                    pass
            messages.success(request, 'FDIR entry saved.')
            return redirect('fdir_entry_detail', entry_id=entry.pk)

    context = {
        'subsystems': Subsystem.objects.all(),
        'procedures': Procedure.objects.order_by('name'),
        'severity_choices': FDIREntry.SEVERITY_CHOICES,
        'entry': None,
        'selected_procedure_ids': set(),
    }
    return render(request, 'fdir/entry_form.html', context)


@login_required
def entry_edit(request, entry_id):
    """Edit FDIR entry (login required)."""
    entry = get_object_or_404(FDIREntry, pk=entry_id)

    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        subsystem_id = request.POST.get('subsystem')
        if not name or not subsystem_id:
            messages.error(request, 'Name and subsystem are required.')
        else:
            subsystem = get_object_or_404(Subsystem, pk=subsystem_id)
            entry.name = name
            entry.fault_code = (request.POST.get('fault_code') or '').strip()
            entry.subsystem = subsystem
            entry.severity = request.POST.get('severity') or FDIREntry.SEVERITY_INFO
            entry.fault_type = (request.POST.get('fault_type') or '').strip()
            entry.triggering_conditions = request.POST.get('triggering_conditions') or ''
            entry.detection_thresholds = request.POST.get('detection_thresholds') or ''
            entry.onboard_automated_response = request.POST.get('onboard_automated_response') or ''
            entry.version = (request.POST.get('version') or '').strip()
            entry.save()
            entry.operator_procedures.clear()
            procedure_ids = request.POST.getlist('operator_procedures')
            for pid in procedure_ids:
                try:
                    entry.operator_procedures.add(Procedure.objects.get(pk=pid))
                except (ValueError, Procedure.DoesNotExist):
                    pass
            messages.success(request, 'FDIR entry saved.')
            return redirect('fdir_entry_detail', entry_id=entry.pk)

    selected_procedure_ids = set(entry.operator_procedures.values_list('id', flat=True))
    context = {
        'entry': entry,
        'subsystems': Subsystem.objects.all(),
        'procedures': Procedure.objects.order_by('name'),
        'severity_choices': FDIREntry.SEVERITY_CHOICES,
        'selected_procedure_ids': selected_procedure_ids,
    }
    return render(request, 'fdir/entry_form.html', context)
