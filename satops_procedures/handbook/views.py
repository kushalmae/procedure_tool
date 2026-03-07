import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from procedures.models import Procedure

from .models import AlertDefinition, Subsystem


def _int_or_none(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def alert_list(request):
    if request.GET.get('clear'):
        if 'handbook_filters' in request.session:
            del request.session['handbook_filters']
        return redirect('handbook_alert_list')

    HANDBOOK_SORT_OPTIONS = [
        'subsystem__name',
        'parameter',
        '-parameter',
        '-updated_at',
        'severity',
        '-severity',
    ]
    saved = request.session.get('handbook_filters') or {}
    subsystem_id = request.GET.get('subsystem', saved.get('subsystem', ''))
    severity = request.GET.get('severity', saved.get('severity', ''))
    q = (request.GET.get('q') or saved.get('q') or '').strip()
    sort = request.GET.get('sort', saved.get('sort', 'subsystem__name'))
    if sort not in HANDBOOK_SORT_OPTIONS:
        sort = 'subsystem__name'

    has_filters = any([subsystem_id, severity, q])
    if has_filters or sort != 'subsystem__name':
        request.session['handbook_filters'] = {
            'subsystem': subsystem_id or '',
            'severity': severity or '',
            'q': q or '',
            'sort': sort,
        }

    alerts = (
        AlertDefinition.objects
        .select_related('subsystem', 'procedure')
        .order_by(sort)
    )

    if subsystem_id:
        sid = _int_or_none(subsystem_id)
        if sid is not None:
            alerts = alerts.filter(subsystem_id=sid)
    if severity:
        alerts = alerts.filter(severity=severity)
    if q:
        alerts = alerts.filter(
            Q(parameter__icontains=q)
            | Q(description__icontains=q)
            | Q(mnemonic__icontains=q)
            | Q(apids__icontains=q)
        )

    alerts = alerts[:200]

    context = {
        'alerts': alerts,
        'subsystems': Subsystem.objects.all(),
        'filter_subsystem_id': _int_or_none(subsystem_id),
        'filter_severity': severity or None,
        'search_query': q,
        'sort': sort,
        'severity_choices': AlertDefinition.SEVERITY_CHOICES,
    }
    return render(request, 'handbook/alert_list.html', context)


def alert_detail(request, alert_id):
    alert = get_object_or_404(
        AlertDefinition.objects.select_related('subsystem', 'procedure'),
        pk=alert_id,
    )
    return render(request, 'handbook/alert_detail.html', {'alert': alert})


@login_required
def alert_create(request):
    if request.method == 'POST':
        parameter = (request.POST.get('parameter') or '').strip()
        mnemonic = (request.POST.get('mnemonic') or '').strip()
        mnemonic_description = (request.POST.get('mnemonic_description') or '').strip()
        user_notes = (request.POST.get('user_notes') or '').strip()
        apids = (request.POST.get('apids') or '').strip()
        subsystem_id = request.POST.get('subsystem')
        description = (request.POST.get('description') or '').strip()
        alert_conditions = (request.POST.get('alert_conditions') or '').strip()
        warning_threshold = (request.POST.get('warning_threshold') or '').strip()
        critical_threshold = (request.POST.get('critical_threshold') or '').strip()
        recommended_response = (request.POST.get('recommended_response') or '').strip()
        procedure_id = request.POST.get('procedure') or None
        severity = request.POST.get('severity') or AlertDefinition.SEVERITY_WARNING

        if not parameter or not subsystem_id or not description:
            messages.error(request, 'Parameter, subsystem, and description are required.')
            return render(request, 'handbook/alert_form.html', {
                'subsystems': Subsystem.objects.all(),
                'procedures': Procedure.objects.all(),
                'severity_choices': AlertDefinition.SEVERITY_CHOICES,
                'form': {
                    'parameter': parameter,
                    'mnemonic': mnemonic,
                    'mnemonic_description': mnemonic_description,
                    'user_notes': user_notes,
                    'apids': apids,
                    'subsystem_id': _int_or_none(subsystem_id),
                    'description': description,
                    'alert_conditions': alert_conditions,
                    'warning_threshold': warning_threshold,
                    'critical_threshold': critical_threshold,
                    'recommended_response': recommended_response,
                    'procedure_id': _int_or_none(procedure_id),
                    'severity': severity,
                },
            })

        subsystem = get_object_or_404(Subsystem, pk=subsystem_id)
        procedure = get_object_or_404(Procedure, pk=procedure_id) if procedure_id else None

        alert = AlertDefinition.objects.create(
            parameter=parameter,
            mnemonic=mnemonic,
            mnemonic_description=mnemonic_description,
            user_notes=user_notes,
            apids=apids,
            subsystem=subsystem,
            description=description,
            alert_conditions=alert_conditions,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            recommended_response=recommended_response,
            procedure=procedure,
            severity=severity,
        )
        messages.success(request, f'Alert "{alert.parameter}" created.')
        return redirect('handbook_alert_detail', alert_id=alert.pk)

    context = {
        'subsystems': Subsystem.objects.all(),
        'procedures': Procedure.objects.all(),
        'severity_choices': AlertDefinition.SEVERITY_CHOICES,
        'form': {
            'parameter': '',
            'mnemonic': '',
            'mnemonic_description': '',
            'user_notes': '',
            'apids': '',
            'subsystem_id': None,
            'description': '',
            'alert_conditions': '',
            'warning_threshold': '',
            'critical_threshold': '',
            'recommended_response': '',
            'procedure_id': None,
            'severity': AlertDefinition.SEVERITY_WARNING,
        },
    }
    return render(request, 'handbook/alert_form.html', context)


@login_required
def alert_edit(request, alert_id):
    alert = get_object_or_404(AlertDefinition, pk=alert_id)
    if request.method == 'POST':
        parameter = (request.POST.get('parameter') or '').strip()
        mnemonic = (request.POST.get('mnemonic') or '').strip()
        mnemonic_description = (request.POST.get('mnemonic_description') or '').strip()
        user_notes = (request.POST.get('user_notes') or '').strip()
        apids = (request.POST.get('apids') or '').strip()
        subsystem_id = request.POST.get('subsystem')
        description = (request.POST.get('description') or '').strip()
        alert_conditions = (request.POST.get('alert_conditions') or '').strip()
        warning_threshold = (request.POST.get('warning_threshold') or '').strip()
        critical_threshold = (request.POST.get('critical_threshold') or '').strip()
        recommended_response = (request.POST.get('recommended_response') or '').strip()
        procedure_id = request.POST.get('procedure') or None
        severity = request.POST.get('severity') or AlertDefinition.SEVERITY_WARNING

        if not parameter or not subsystem_id or not description:
            messages.error(request, 'Parameter, subsystem, and description are required.')
            return render(request, 'handbook/alert_form.html', {
                'alert': alert,
                'subsystems': Subsystem.objects.all(),
                'procedures': Procedure.objects.all(),
                'severity_choices': AlertDefinition.SEVERITY_CHOICES,
                'form': {
                    'parameter': parameter,
                    'mnemonic': mnemonic,
                    'mnemonic_description': mnemonic_description,
                    'user_notes': user_notes,
                    'apids': apids,
                    'subsystem_id': _int_or_none(subsystem_id),
                    'description': description,
                    'alert_conditions': alert_conditions,
                    'warning_threshold': warning_threshold,
                    'critical_threshold': critical_threshold,
                    'recommended_response': recommended_response,
                    'procedure_id': _int_or_none(procedure_id),
                    'severity': severity,
                },
            })

        subsystem = get_object_or_404(Subsystem, pk=subsystem_id)
        procedure = get_object_or_404(Procedure, pk=procedure_id) if procedure_id else None

        alert.parameter = parameter
        alert.mnemonic = mnemonic
        alert.mnemonic_description = mnemonic_description
        alert.user_notes = user_notes
        alert.apids = apids
        alert.subsystem = subsystem
        alert.description = description
        alert.alert_conditions = alert_conditions
        alert.warning_threshold = warning_threshold
        alert.critical_threshold = critical_threshold
        alert.recommended_response = recommended_response
        alert.procedure = procedure
        alert.severity = severity
        alert.save()
        messages.success(request, f'Alert "{alert.parameter}" updated (version {alert.version}).')
        return redirect('handbook_alert_detail', alert_id=alert.pk)

    context = {
        'alert': alert,
        'subsystems': Subsystem.objects.all(),
        'procedures': Procedure.objects.all(),
        'severity_choices': AlertDefinition.SEVERITY_CHOICES,
        'form': {
            'parameter': alert.parameter,
            'mnemonic': alert.mnemonic,
            'mnemonic_description': alert.mnemonic_description,
            'user_notes': alert.user_notes,
            'apids': alert.apids,
            'subsystem_id': alert.subsystem_id,
            'description': alert.description,
            'alert_conditions': alert.alert_conditions,
            'warning_threshold': alert.warning_threshold,
            'critical_threshold': alert.critical_threshold,
            'recommended_response': alert.recommended_response,
            'procedure_id': alert.procedure_id,
            'severity': alert.severity,
        },
    }
    return render(request, 'handbook/alert_form.html', context)


@login_required
def alert_delete(request, alert_id):
    alert = get_object_or_404(AlertDefinition, pk=alert_id)
    if request.method == 'POST':
        name = alert.parameter
        alert.delete()
        messages.success(request, f'Alert "{name}" has been deleted.')
        return redirect('handbook_alert_list')
    return render(request, 'handbook/alert_confirm_delete.html', {'alert': alert})


# ---------------------------------------------------------------------------
# CSV Import / Export
# ---------------------------------------------------------------------------


def alert_csv_export(request):
    """Export alert definitions as CSV with current filters."""
    qs = (
        AlertDefinition.objects
        .select_related('subsystem', 'procedure')
        .order_by('subsystem__name', 'parameter')
    )
    subsystem_id = request.GET.get('subsystem')
    severity = request.GET.get('severity')
    q = (request.GET.get('q') or '').strip()
    if subsystem_id:
        sid = _int_or_none(subsystem_id)
        if sid is not None:
            qs = qs.filter(subsystem_id=sid)
    if severity:
        qs = qs.filter(severity=severity)
    if q:
        qs = qs.filter(
            Q(parameter__icontains=q)
            | Q(description__icontains=q)
            | Q(mnemonic__icontains=q)
            | Q(apids__icontains=q)
        )

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="handbook_alerts.csv"'
    response['X-Content-Type-Options'] = 'nosniff'
    writer = csv.writer(response)
    writer.writerow([
        'Parameter', 'Mnemonic', 'Mnemonic Description', 'User Notes', 'APIDs', 'Subsystem',
        'Description', 'Alert Conditions', 'Warning Threshold', 'Critical Threshold',
        'Recommended Response', 'Procedure', 'Severity', 'Version', 'Updated At',
    ])
    for a in qs:
        writer.writerow([
            a.parameter,
            a.mnemonic,
            a.mnemonic_description,
            a.user_notes,
            a.apids,
            a.subsystem.name,
            a.description,
            a.alert_conditions,
            a.warning_threshold,
            a.critical_threshold,
            a.recommended_response,
            a.procedure.name if a.procedure else '',
            a.severity,
            a.version,
            a.updated_at.strftime('%Y-%m-%d %H:%M') if a.updated_at else '',
        ])
    return response


@login_required
def alert_csv_import(request):
    """Import alert definitions from CSV (POST with csv_file)."""
    if request.method != 'POST':
        return redirect('handbook_alert_list')

    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        messages.error(request, 'Please select a CSV file.')
        return redirect('handbook_alert_list')
    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'File must be a CSV.')
        return redirect('handbook_alert_list')

    try:
        decoded = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))
    except Exception:
        messages.error(request, 'Could not read the CSV file.')
        return redirect('handbook_alert_list')

    def get(row, *keys):
        for k in keys:
            val = (row.get(k) or '').strip()
            if val:
                return val
        return ''

    fieldnames = [h.strip().lower() for h in (reader.fieldnames or []) if h]
    has_param = any('parameter' in k for k in fieldnames)
    has_subsystem = any('subsystem' in k for k in fieldnames)
    has_desc = any('description' in k for k in fieldnames)
    if not (has_param and has_subsystem and has_desc):
        messages.error(request, 'CSV must contain: Parameter, Subsystem, Description.')
        return redirect('handbook_alert_list')

    subsystems = {s.name: s for s in Subsystem.objects.all()}
    procedures = {p.name: p for p in Procedure.objects.all()}
    created = 0
    skipped = 0

    for row in reader:
        parameter = get(row, 'Parameter', 'parameter')
        sub_name = get(row, 'Subsystem', 'subsystem')
        description = get(row, 'Description', 'description')
        if not parameter or not sub_name or not description:
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

        proc_name = get(row, 'Procedure', 'procedure')
        procedure = procedures.get(proc_name) if proc_name else None
        if proc_name and not procedure:
            procedure = Procedure.objects.filter(name=proc_name).first()
            if procedure:
                procedures[procedure.name] = procedure

        severity = get(row, 'Severity', 'severity') or AlertDefinition.SEVERITY_WARNING
        if severity not in dict(AlertDefinition.SEVERITY_CHOICES):
            severity = AlertDefinition.SEVERITY_WARNING

        AlertDefinition.objects.create(
            parameter=parameter,
            mnemonic=get(row, 'Mnemonic', 'mnemonic'),
            mnemonic_description=get(row, 'Mnemonic Description', 'mnemonic_description'),
            user_notes=get(row, 'User Notes', 'user_notes'),
            apids=get(row, 'APIDs', 'apids', 'apid'),
            subsystem=subsystem,
            description=description,
            alert_conditions=get(row, 'Alert Conditions', 'alert_conditions'),
            warning_threshold=get(row, 'Warning Threshold', 'warning_threshold'),
            critical_threshold=get(row, 'Critical Threshold', 'critical_threshold'),
            recommended_response=get(row, 'Recommended Response', 'recommended_response'),
            procedure=procedure,
            severity=severity,
        )
        created += 1

    msg = f'Imported {created} alert(s).'
    if skipped:
        msg += f' Skipped {skipped} row(s).'
    messages.success(request, msg)
    return redirect('handbook_alert_list')
