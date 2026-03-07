import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
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


# ---------------------------------------------------------------------------
# CSV Import / Export
# ---------------------------------------------------------------------------


def entry_csv_export(request):
    """Export FDIR entries as CSV with current filters."""
    qs = (
        FDIREntry.objects
        .select_related('subsystem')
        .prefetch_related('operator_procedures')
        .order_by('subsystem__name', 'name')
    )
    subsystem_id = request.GET.get('subsystem')
    severity = request.GET.get('severity')
    fault_type = request.GET.get('fault_type')
    q = (request.GET.get('q') or '').strip()
    if subsystem_id:
        sid = _int_or_none(subsystem_id)
        if sid is not None:
            qs = qs.filter(subsystem_id=sid)
    if severity:
        qs = qs.filter(severity=severity)
    if fault_type:
        qs = qs.filter(fault_type__iexact=fault_type)
    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(triggering_conditions__icontains=q)
            | Q(detection_thresholds__icontains=q)
            | Q(onboard_automated_response__icontains=q)
            | Q(fault_code__icontains=q)
        )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="fdir_entries.csv"'
    response['X-Content-Type-Options'] = 'nosniff'
    writer = csv.writer(response)
    writer.writerow([
        'Name', 'Fault Code', 'Subsystem', 'Severity', 'Fault Type',
        'Triggering Conditions', 'Detection Thresholds', 'Onboard Automated Response',
        'Operator Procedures', 'Version', 'Updated At',
    ])
    for e in qs:
        proc_names = ', '.join(p.name for p in e.operator_procedures.all())
        writer.writerow([
            e.name,
            e.fault_code,
            e.subsystem.name,
            e.severity,
            e.fault_type,
            e.triggering_conditions,
            e.detection_thresholds,
            e.onboard_automated_response,
            proc_names,
            e.version,
            e.updated_at.strftime('%Y-%m-%d %H:%M') if e.updated_at else '',
        ])
    return response


@login_required
def entry_csv_import(request):
    """Import FDIR entries from CSV (POST with csv_file)."""
    if request.method != 'POST':
        return redirect('fdir_entry_list')

    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        messages.error(request, 'Please select a CSV file.')
        return redirect('fdir_entry_list')
    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'File must be a CSV.')
        return redirect('fdir_entry_list')

    try:
        decoded = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))
    except Exception:
        messages.error(request, 'Could not read the CSV file.')
        return redirect('fdir_entry_list')

    def get(row, *keys):
        for k in keys:
            val = (row.get(k) or '').strip()
            if val:
                return val
        return ''

    fieldnames = [h.strip().lower() for h in (reader.fieldnames or []) if h]
    has_name = any('name' in k for k in fieldnames)
    has_subsystem = any('subsystem' in k for k in fieldnames)
    if not (has_name and has_subsystem):
        messages.error(request, 'CSV must contain Name and Subsystem columns.')
        return redirect('fdir_entry_list')

    subsystems = {s.name: s for s in Subsystem.objects.all()}
    procedures = {p.name: p for p in Procedure.objects.all()}
    created = 0
    skipped = 0

    for row in reader:
        name = get(row, 'Name', 'name')
        sub_name = get(row, 'Subsystem', 'subsystem')
        if not name or not sub_name:
            skipped += 1
            continue

        subsystem = subsystems.get(sub_name)
        if not subsystem:
            subsystem = Subsystem.objects.filter(name=sub_name).first()
            if subsystem:
                subsystems[subsystem.name] = subsystem
            else:
                subsystem = Subsystem.objects.create(name=sub_name)
                subsystems[subsystem.name] = subsystem

        severity = get(row, 'Severity', 'severity') or FDIREntry.SEVERITY_INFO
        if severity not in dict(FDIREntry.SEVERITY_CHOICES):
            severity = FDIREntry.SEVERITY_INFO

        entry = FDIREntry.objects.create(
            name=name,
            fault_code=get(row, 'Fault Code', 'fault_code'),
            subsystem=subsystem,
            severity=severity,
            fault_type=get(row, 'Fault Type', 'fault_type'),
            triggering_conditions=get(row, 'Triggering Conditions', 'triggering_conditions'),
            detection_thresholds=get(row, 'Detection Thresholds', 'detection_thresholds'),
            onboard_automated_response=get(row, 'Onboard Automated Response', 'onboard_automated_response'),
            version=get(row, 'Version', 'version'),
        )
        proc_names_str = get(row, 'Operator Procedures', 'operator_procedures', 'procedures')
        if proc_names_str:
            for pname in [n.strip() for n in proc_names_str.split(',') if n.strip()]:
                proc = procedures.get(pname)
                if not proc:
                    proc = Procedure.objects.filter(name=pname).first()
                    if proc:
                        procedures[proc.name] = proc
                if proc:
                    entry.operator_procedures.add(proc)
        created += 1

    msg = f'Imported {created} FDIR entr{"y" if created == 1 else "ies"}.'
    if skipped:
        msg += f' Skipped {skipped} row(s).'
    messages.success(request, msg)
    return redirect('fdir_entry_list')
