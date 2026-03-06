from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from procedures.models import Satellite, ProcedureRun, Procedure
from .models import Subsystem, AnomalyType, Anomaly, AnomalyNote


def _int_or_none(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def get_suggested_procedures(subsystem_id=None, subsystem_name=None, anomaly_type_id=None):
    """Return list of (Procedure, source_label) for anomaly resolution suggestions.
    Uses FDIR (by subsystem name), Handbook (by subsystem name), and past anomalies (by type/subsystem).
    """
    from django.db.models import Q
    seen_ids = set()
    result = []
    subs_name = subsystem_name
    if not subs_name and subsystem_id:
        sub = Subsystem.objects.filter(pk=subsystem_id).first()
        if sub:
            subs_name = sub.name

    # FDIR: procedures linked from FDIR entries whose subsystem name matches
    if subs_name:
        try:
            FDIREntry = __import__('fdir.models', fromlist=['FDIREntry']).FDIREntry
            for proc in Procedure.objects.filter(
                fdir_entries__subsystem__name__iexact=subs_name
            ).distinct():
                if proc.id not in seen_ids:
                    seen_ids.add(proc.id)
                    result.append((proc, 'FDIR'))
        except Exception:
            pass

    # Handbook: procedures linked from alert definitions whose subsystem name matches
    if subs_name:
        try:
            AlertDefinition = __import__('handbook.models', fromlist=['AlertDefinition']).AlertDefinition
            for proc in Procedure.objects.filter(
                handbook_alerts__subsystem__name__iexact=subs_name
            ).filter(handbook_alerts__procedure__isnull=False).distinct():
                if proc.id not in seen_ids:
                    seen_ids.add(proc.id)
                    result.append((proc, 'Handbook'))
        except Exception:
            pass

    # Past anomalies: procedures from runs that were linked to similar anomalies
    past = Anomaly.objects.filter(procedure_run__isnull=False).exclude(procedure_run__procedure_id__isnull=True)
    if anomaly_type_id:
        past = past.filter(anomaly_type_id=anomaly_type_id)
    if subsystem_id:
        past = past.filter(subsystem_id=subsystem_id)
    if not anomaly_type_id and not subsystem_id:
        past = past.none()
    for proc in Procedure.objects.filter(
        procedurerun__linked_anomalies__in=past
    ).distinct()[:10]:
        if proc.id not in seen_ids:
            seen_ids.add(proc.id)
            result.append((proc, 'Past resolution'))

    return result


def registry(request):
    if request.GET.get('clear'):
        if 'anomaly_filters' in request.session:
            del request.session['anomaly_filters']
        return redirect('anomalies_registry')

    ANOMALY_SORT_OPTIONS = [
        '-detection_time',
        'detection_time',
        'satellite__name',
        '-satellite__name',
        'severity',
        '-severity',
        'status',
        '-status',
    ]
    saved = request.session.get('anomaly_filters') or {}
    satellite_id = request.GET.get('satellite', saved.get('satellite', ''))
    subsystem_id = request.GET.get('subsystem', saved.get('subsystem', ''))
    severity = request.GET.get('severity', saved.get('severity', ''))
    status = request.GET.get('status', saved.get('status', ''))
    q = (request.GET.get('q') or saved.get('q') or '').strip()
    sort = request.GET.get('sort', saved.get('sort', '-detection_time'))
    if sort not in ANOMALY_SORT_OPTIONS:
        sort = '-detection_time'

    has_filters = any([satellite_id, subsystem_id, severity, status, q])
    if has_filters or sort != '-detection_time':
        request.session['anomaly_filters'] = {
            'satellite': satellite_id or '',
            'subsystem': subsystem_id or '',
            'severity': severity or '',
            'status': status or '',
            'q': q or '',
            'sort': sort,
        }

    anomalies = (
        Anomaly.objects
        .select_related('satellite', 'subsystem', 'anomaly_type', 'reported_by')
        .order_by(sort)
    )

    if satellite_id:
        try:
            anomalies = anomalies.filter(satellite_id=int(satellite_id))
        except ValueError:
            pass
    if subsystem_id:
        try:
            anomalies = anomalies.filter(subsystem_id=int(subsystem_id))
        except ValueError:
            pass
    if severity:
        anomalies = anomalies.filter(severity=severity)
    if status:
        anomalies = anomalies.filter(status=status)
    if q:
        anomalies = anomalies.filter(description__icontains=q)

    anomalies = anomalies[:200]

    context = {
        'anomalies': anomalies,
        'satellites': Satellite.objects.all(),
        'subsystems': Subsystem.objects.all(),
        'filter_satellite_id': _int_or_none(satellite_id),
        'filter_subsystem_id': _int_or_none(subsystem_id),
        'filter_severity': severity or None,
        'filter_status': status or None,
        'search_query': q,
        'sort': sort,
        'severity_choices': Anomaly.SEVERITY_CHOICES,
        'status_choices': Anomaly.STATUS_CHOICES,
    }
    return render(request, 'anomalies/registry.html', context)


@login_required
def add_anomaly(request):
    if request.method == 'POST':
        satellite_id = request.POST.get('satellite')
        if not satellite_id:
            messages.error(request, 'Satellite is required.')
            ctx = _add_anomaly_get_context(request)
            ctx['form_satellite_id'] = _int_or_none(satellite_id)
            ctx['form_subsystem_id'] = _int_or_none(request.POST.get('subsystem'))
            ctx['form_anomaly_type_id'] = _int_or_none(request.POST.get('anomaly_type'))
            ctx['form_severity'] = request.POST.get('severity') or Anomaly.SEVERITY_MEDIUM
            ctx['form_detection_time'] = request.POST.get('detection_time') or ''
            ctx['form_impact'] = request.POST.get('operational_impact') or Anomaly.IMPACT_NONE
            ctx['form_description'] = request.POST.get('description', '')
            ctx['form_procedure_run_id'] = _int_or_none(request.POST.get('procedure_run'))
            ctx['suggested_procedures'] = get_suggested_procedures(
                subsystem_id=ctx['form_subsystem_id'],
                anomaly_type_id=ctx['form_anomaly_type_id'],
            )
            return render(request, 'anomalies/anomaly_form.html', ctx)

        satellite = get_object_or_404(Satellite, pk=satellite_id)
        subsystem_id = request.POST.get('subsystem') or None
        subsystem = get_object_or_404(Subsystem, pk=subsystem_id) if subsystem_id else None
        anomaly_type_id = request.POST.get('anomaly_type') or None
        anomaly_type = get_object_or_404(AnomalyType, pk=anomaly_type_id) if anomaly_type_id else None
        severity = request.POST.get('severity') or Anomaly.SEVERITY_MEDIUM
        ts_str = (request.POST.get('detection_time') or '').strip()
        detection_time = parse_datetime(ts_str) if ts_str else timezone.now()
        if not detection_time:
            detection_time = timezone.now()
        operational_impact = request.POST.get('operational_impact') or Anomaly.IMPACT_NONE
        description = (request.POST.get('description') or '').strip()
        procedure_run_id = _int_or_none(request.POST.get('procedure_run'))
        procedure_run = None
        if procedure_run_id:
            procedure_run = ProcedureRun.objects.filter(pk=procedure_run_id).first()

        anomaly = Anomaly.objects.create(
            satellite=satellite,
            subsystem=subsystem,
            anomaly_type=anomaly_type,
            severity=severity,
            detection_time=detection_time,
            operational_impact=operational_impact,
            status=Anomaly.STATUS_NEW,
            description=description,
            reported_by=request.user,
            procedure_run=procedure_run,
        )
        messages.success(request, 'Anomaly reported.')
        if request.POST.get('add_another'):
            return redirect(reverse('anomalies_add'))
        return redirect(reverse('anomalies_detail', kwargs={'anomaly_id': anomaly.pk}))

    return render(request, 'anomalies/anomaly_form.html', _add_anomaly_get_context(request))


def _add_anomaly_get_context(request):
    now = timezone.now()
    last = (
        Anomaly.objects.filter(reported_by=request.user)
        .order_by('-created_at')
        .first()
    ) if request.user.is_authenticated else None
    default_satellite_id = last.satellite_id if last else None
    default_subsystem_id = last.subsystem_id if last else None
    default_anomaly_type_id = last.anomaly_type_id if last else None
    default_severity = last.severity if last else Anomaly.SEVERITY_MEDIUM
    default_impact = last.operational_impact if last else Anomaly.IMPACT_NONE
    default_procedure_run_id = last.procedure_run_id if last else None
    recent_runs = (
        ProcedureRun.objects.select_related('satellite', 'procedure')
        .order_by('-start_time')[:30]
    )
    suggested = get_suggested_procedures(
        subsystem_id=default_subsystem_id,
        anomaly_type_id=default_anomaly_type_id,
    )
    return {
        'satellites': Satellite.objects.all(),
        'subsystems': Subsystem.objects.all(),
        'anomaly_types': AnomalyType.objects.all(),
        'recent_runs': recent_runs,
        'suggested_procedures': suggested,
        'detection_time_default': now.strftime('%Y-%m-%dT%H:%M'),
        'severity_choices': Anomaly.SEVERITY_CHOICES,
        'impact_choices': Anomaly.IMPACT_CHOICES,
        'form_satellite_id': default_satellite_id,
        'form_subsystem_id': default_subsystem_id,
        'form_anomaly_type_id': default_anomaly_type_id,
        'form_severity': default_severity,
        'form_detection_time': now.strftime('%Y-%m-%dT%H:%M'),
        'form_impact': default_impact,
        'form_description': '',
        'form_procedure_run_id': default_procedure_run_id,
    }


def anomaly_detail(request, anomaly_id):
    anomaly = get_object_or_404(
        Anomaly.objects.select_related(
            'satellite', 'subsystem', 'anomaly_type', 'reported_by', 'procedure_run',
            'resolution_procedure',
        ).select_related('procedure_run__satellite', 'procedure_run__procedure'),
        pk=anomaly_id,
    )
    notes = anomaly.notes.select_related('created_by').order_by('-created_at')
    suggested_procedures = get_suggested_procedures(
        subsystem_id=anomaly.subsystem_id,
        subsystem_name=anomaly.subsystem.name if anomaly.subsystem else None,
        anomaly_type_id=anomaly.anomaly_type_id,
    )
    all_procedures = list(Procedure.objects.order_by('name'))

    if request.method == 'POST' and request.user.is_authenticated:
        new_status = request.POST.get('status')
        note_body = (request.POST.get('note_body') or '').strip()
        resolution_procedure_id = _int_or_none(request.POST.get('resolution_procedure'))
        if new_status and new_status in dict(Anomaly.STATUS_CHOICES):
            anomaly.status = new_status
            anomaly.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Status updated.')
        if note_body:
            AnomalyNote.objects.create(
                anomaly=anomaly,
                body=note_body,
                created_by=request.user,
            )
            messages.success(request, 'Note added.')
        if resolution_procedure_id is not None:
            if resolution_procedure_id:
                procedure = Procedure.objects.filter(pk=resolution_procedure_id).first()
                if procedure:
                    anomaly.resolution_procedure = procedure
                    anomaly.save(update_fields=['resolution_procedure', 'updated_at'])
                    messages.success(request, 'Resolution procedure recorded.')
            else:
                anomaly.resolution_procedure = None
                anomaly.save(update_fields=['resolution_procedure', 'updated_at'])
        return redirect(reverse('anomalies_detail', kwargs={'anomaly_id': anomaly.pk}))

    context = {
        'anomaly': anomaly,
        'notes': notes,
        'status_choices': Anomaly.STATUS_CHOICES,
        'suggested_procedures': suggested_procedures,
        'all_procedures': all_procedures,
    }
    return render(request, 'anomalies/anomaly_detail.html', context)
