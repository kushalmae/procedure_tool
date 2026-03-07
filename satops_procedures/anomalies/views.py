from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from procedures.models import Satellite, Subsystem

from .models import Anomaly, AnomalyTimelineEntry


def _int_or_none(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def anomaly_list(request):
    if request.GET.get('clear'):
        if 'anomaly_filters' in request.session:
            del request.session['anomaly_filters']
        return redirect('anomalies_list')

    SORT_OPTIONS = [
        '-detected_time',
        'detected_time',
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
    sort = request.GET.get('sort', saved.get('sort', '-detected_time'))
    if sort not in SORT_OPTIONS:
        sort = '-detected_time'

    has_filters = any([satellite_id, subsystem_id, severity, status, q])
    if has_filters or sort != '-detected_time':
        request.session['anomaly_filters'] = {
            'satellite': satellite_id or '',
            'subsystem': subsystem_id or '',
            'severity': severity or '',
            'status': status or '',
            'q': q or '',
            'sort': sort,
        }

    qs = (
        Anomaly.objects
        .select_related('satellite', 'subsystem', 'created_by')
        .order_by(sort)
    )

    if satellite_id:
        try:
            qs = qs.filter(satellite_id=int(satellite_id))
        except ValueError:
            pass
    if subsystem_id:
        try:
            qs = qs.filter(subsystem_id=int(subsystem_id))
        except ValueError:
            pass
    if severity:
        qs = qs.filter(severity=severity)
    if status:
        qs = qs.filter(status=status)
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    anomalies = qs[:200]

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
    return render(request, 'anomalies/anomaly_list.html', context)


@login_required
def anomaly_create(request):
    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()
        satellite_id = request.POST.get('satellite')

        if not title or not satellite_id:
            messages.error(request, 'Title and satellite are required.')
            ctx = _create_context(request)
            ctx.update({
                'form_title': title,
                'form_satellite_id': _int_or_none(satellite_id),
                'form_subsystem_id': _int_or_none(request.POST.get('subsystem')),
                'form_severity': request.POST.get('severity', Anomaly.SEVERITY_L2),
                'form_detected_time': request.POST.get('detected_time', ''),
                'form_description': request.POST.get('description', ''),
            })
            return render(request, 'anomalies/anomaly_form.html', ctx)

        satellite = get_object_or_404(Satellite, pk=satellite_id)
        subsystem_id = request.POST.get('subsystem') or None
        subsystem = get_object_or_404(Subsystem, pk=subsystem_id) if subsystem_id else None
        severity = request.POST.get('severity') or Anomaly.SEVERITY_L2
        ts_str = (request.POST.get('detected_time') or '').strip()
        detected_time = parse_datetime(ts_str) if ts_str else timezone.now()
        if not detected_time:
            detected_time = timezone.now()
        description = (request.POST.get('description') or '').strip()

        anomaly = Anomaly.objects.create(
            title=title,
            satellite=satellite,
            subsystem=subsystem,
            severity=severity,
            status=Anomaly.STATUS_NEW,
            description=description,
            detected_time=detected_time,
            created_by=request.user,
        )

        sub_display = subsystem.name if subsystem else '—'
        AnomalyTimelineEntry.objects.create(
            anomaly=anomaly,
            entry_type=AnomalyTimelineEntry.ENTRY_NOTE,
            body=f'Anomaly created with severity {anomaly.get_severity_display()} — {sub_display}',
            created_by=request.user,
        )

        messages.success(request, f'Anomaly ANOM-{anomaly.pk} created.')
        return redirect(reverse('anomalies_detail', kwargs={'anomaly_id': anomaly.pk}))

    return render(request, 'anomalies/anomaly_form.html', _create_context(request))


def _create_context(request):
    now = timezone.now()
    return {
        'satellites': Satellite.objects.all(),
        'subsystems': Subsystem.objects.all(),
        'severity_choices': Anomaly.SEVERITY_CHOICES,
        'form_title': '',
        'form_satellite_id': None,
        'form_subsystem_id': None,
        'form_severity': Anomaly.SEVERITY_L2,
        'form_detected_time': now.strftime('%Y-%m-%dT%H:%M'),
        'form_description': '',
    }


def anomaly_detail(request, anomaly_id):
    anomaly = get_object_or_404(
        Anomaly.objects.select_related('satellite', 'subsystem', 'created_by'),
        pk=anomaly_id,
    )
    timeline = anomaly.timeline_entries.select_related('created_by').order_by('created_at')

    context = {
        'anomaly': anomaly,
        'timeline': timeline,
        'status_choices': Anomaly.STATUS_CHOICES,
        'severity_choices': Anomaly.SEVERITY_CHOICES,
    }
    return render(request, 'anomalies/anomaly_detail.html', context)


@login_required
def anomaly_update(request, anomaly_id):
    anomaly = get_object_or_404(Anomaly, pk=anomaly_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        new_severity = request.POST.get('severity')
        note_body = (request.POST.get('note_body') or '').strip()
        action_body = (request.POST.get('action_body') or '').strip()

        if new_status and new_status in dict(Anomaly.STATUS_CHOICES) and new_status != anomaly.status:
            old_status = anomaly.get_status_display()
            anomaly.status = new_status
            anomaly.save(update_fields=['status', 'updated_at'])
            new_display = anomaly.get_status_display()
            AnomalyTimelineEntry.objects.create(
                anomaly=anomaly,
                entry_type=AnomalyTimelineEntry.ENTRY_STATUS_CHANGE,
                body=f'Status changed from {old_status} to {new_display}',
                old_value=old_status,
                new_value=new_display,
                created_by=request.user,
            )
            messages.success(request, f'Status updated to {new_display}.')

        if new_severity and new_severity in dict(Anomaly.SEVERITY_CHOICES) and new_severity != anomaly.severity:
            old_severity = anomaly.get_severity_display()
            anomaly.severity = new_severity
            anomaly.save(update_fields=['severity', 'updated_at'])
            new_sev_display = anomaly.get_severity_display()
            AnomalyTimelineEntry.objects.create(
                anomaly=anomaly,
                entry_type=AnomalyTimelineEntry.ENTRY_SEVERITY_CHANGE,
                body=f'Severity changed from {old_severity} to {new_sev_display}',
                old_value=old_severity,
                new_value=new_sev_display,
                created_by=request.user,
            )
            messages.success(request, f'Severity updated to {new_sev_display}.')

        if note_body:
            AnomalyTimelineEntry.objects.create(
                anomaly=anomaly,
                entry_type=AnomalyTimelineEntry.ENTRY_NOTE,
                body=note_body,
                created_by=request.user,
            )
            messages.success(request, 'Investigation note added.')

        if action_body:
            AnomalyTimelineEntry.objects.create(
                anomaly=anomaly,
                entry_type=AnomalyTimelineEntry.ENTRY_ACTION,
                body=action_body,
                created_by=request.user,
            )
            messages.success(request, 'Action documented.')

        return redirect(reverse('anomalies_detail', kwargs={'anomaly_id': anomaly.pk}))

    return redirect(reverse('anomalies_detail', kwargs={'anomaly_id': anomaly.pk}))


@login_required
def anomaly_close(request, anomaly_id):
    anomaly = get_object_or_404(Anomaly, pk=anomaly_id)

    if request.method == 'POST':
        root_cause = (request.POST.get('root_cause') or '').strip()
        resolution_actions = (request.POST.get('resolution_actions') or '').strip()
        recommendations = (request.POST.get('recommendations') or '').strip()

        anomaly.root_cause = root_cause
        anomaly.resolution_actions = resolution_actions
        anomaly.recommendations = recommendations
        anomaly.status = Anomaly.STATUS_CLOSED
        anomaly.save(update_fields=[
            'root_cause', 'resolution_actions', 'recommendations',
            'status', 'updated_at',
        ])

        resolution_summary_parts = []
        if root_cause:
            resolution_summary_parts.append(f'Root cause: {root_cause}')
        if resolution_actions:
            resolution_summary_parts.append(f'Actions: {resolution_actions}')
        if recommendations:
            resolution_summary_parts.append(f'Recommendations: {recommendations}')
        summary = '\n'.join(resolution_summary_parts) or 'Anomaly closed.'

        AnomalyTimelineEntry.objects.create(
            anomaly=anomaly,
            entry_type=AnomalyTimelineEntry.ENTRY_STATUS_CHANGE,
            body=summary,
            old_value=anomaly.get_status_display(),
            new_value='Closed',
            created_by=request.user,
        )

        messages.success(request, f'Anomaly ANOM-{anomaly.pk} closed.')
        return redirect(reverse('anomalies_detail', kwargs={'anomaly_id': anomaly.pk}))

    context = {
        'anomaly': anomaly,
    }
    return render(request, 'anomalies/anomaly_close.html', context)
