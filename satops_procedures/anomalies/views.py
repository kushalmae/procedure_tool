from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from procedures.models import Satellite
from .models import Subsystem, AnomalyType, Anomaly, AnomalyNote


def _int_or_none(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def registry(request):
    if request.GET.get('clear'):
        if 'anomaly_filters' in request.session:
            del request.session['anomaly_filters']
        return redirect('anomalies_registry')

    saved = request.session.get('anomaly_filters') or {}
    satellite_id = request.GET.get('satellite', saved.get('satellite', ''))
    subsystem_id = request.GET.get('subsystem', saved.get('subsystem', ''))
    severity = request.GET.get('severity', saved.get('severity', ''))
    status = request.GET.get('status', saved.get('status', ''))
    q = (request.GET.get('q') or saved.get('q') or '').strip()

    has_filters = any([satellite_id, subsystem_id, severity, status, q])
    if has_filters:
        request.session['anomaly_filters'] = {
            'satellite': satellite_id or '',
            'subsystem': subsystem_id or '',
            'severity': severity or '',
            'status': status or '',
            'q': q or '',
        }

    anomalies = (
        Anomaly.objects
        .select_related('satellite', 'subsystem', 'anomaly_type', 'reported_by')
        .order_by('-detection_time')
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
    return {
        'satellites': Satellite.objects.all(),
        'subsystems': Subsystem.objects.all(),
        'anomaly_types': AnomalyType.objects.all(),
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
    }


def anomaly_detail(request, anomaly_id):
    anomaly = get_object_or_404(
        Anomaly.objects.select_related('satellite', 'subsystem', 'anomaly_type', 'reported_by'),
        pk=anomaly_id,
    )
    notes = anomaly.notes.select_related('created_by').order_by('-created_at')

    if request.method == 'POST' and request.user.is_authenticated:
        new_status = request.POST.get('status')
        note_body = (request.POST.get('note_body') or '').strip()
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
        return redirect(reverse('anomalies_detail', kwargs={'anomaly_id': anomaly.pk}))

    context = {
        'anomaly': anomaly,
        'notes': notes,
        'status_choices': Anomaly.STATUS_CHOICES,
    }
    return render(request, 'anomalies/anomaly_detail.html', context)
