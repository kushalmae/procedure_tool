import csv
import io

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from auditlog.services import log_action, log_create, log_update
from missions.decorators import mission_role_required
from procedures.models import Satellite, Subsystem

from .models import Anomaly, AnomalyTimelineEntry


def _int_or_none(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def _mission_filter(qs, request):
    if request.mission:
        return qs.filter(mission=request.mission)
    return qs


def anomaly_list(request, mission_slug):
    if request.GET.get('clear'):
        if 'anomaly_filters' in request.session:
            del request.session['anomaly_filters']
        return redirect('anomalies_list', mission_slug=mission_slug)

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
    qs = _mission_filter(qs, request)

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
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    anomalies = qs[:200]

    satellites = _mission_filter(Satellite.objects.all(), request)
    subsystems = _mission_filter(Subsystem.objects.all(), request)

    context = {
        'anomalies': anomalies,
        'satellites': satellites,
        'subsystems': subsystems,
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


@mission_role_required('OPERATOR', 'ADMIN')
def anomaly_create(request, mission_slug):
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

        satellite_qs = _mission_filter(Satellite.objects.all(), request)
        satellite = get_object_or_404(satellite_qs, pk=satellite_id)
        subsystem_id = request.POST.get('subsystem') or None
        subsystem = None
        if subsystem_id:
            subsystem_qs = _mission_filter(Subsystem.objects.all(), request)
            subsystem = get_object_or_404(subsystem_qs, pk=subsystem_id)
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
            mission=request.mission,
        )

        sub_display = subsystem.name if subsystem else '—'
        AnomalyTimelineEntry.objects.create(
            anomaly=anomaly,
            entry_type=AnomalyTimelineEntry.ENTRY_NOTE,
            body=f'Anomaly created with severity {anomaly.get_severity_display()} — {sub_display}',
            created_by=request.user,
        )

        log_create(request, anomaly)
        messages.success(request, f'Anomaly ANOM-{anomaly.pk} created.')
        return redirect(reverse('anomalies_detail', kwargs={'mission_slug': mission_slug, 'anomaly_id': anomaly.pk}))

    return render(request, 'anomalies/anomaly_form.html', _create_context(request))


def _create_context(request):
    now = timezone.now()
    return {
        'satellites': _mission_filter(Satellite.objects.all(), request),
        'subsystems': _mission_filter(Subsystem.objects.all(), request),
        'severity_choices': Anomaly.SEVERITY_CHOICES,
        'form_title': '',
        'form_satellite_id': None,
        'form_subsystem_id': None,
        'form_severity': Anomaly.SEVERITY_L2,
        'form_detected_time': now.strftime('%Y-%m-%dT%H:%M'),
        'form_description': '',
    }


def anomaly_detail(request, mission_slug, anomaly_id):
    qs = _mission_filter(
        Anomaly.objects.select_related('satellite', 'subsystem', 'created_by'),
        request,
    )
    anomaly = get_object_or_404(qs, pk=anomaly_id)
    timeline = anomaly.timeline_entries.select_related('created_by').order_by('created_at')

    context = {
        'anomaly': anomaly,
        'timeline': timeline,
        'status_choices': Anomaly.STATUS_CHOICES,
        'severity_choices': Anomaly.SEVERITY_CHOICES,
    }
    return render(request, 'anomalies/anomaly_detail.html', context)


@mission_role_required('OPERATOR', 'ADMIN')
def anomaly_add_note(request, mission_slug, anomaly_id):
    """Add a standalone note to any anomaly (including closed)."""
    qs = _mission_filter(Anomaly.objects.all(), request)
    anomaly = get_object_or_404(qs, pk=anomaly_id)

    if request.method == 'POST':
        note_body = (request.POST.get('note_body') or '').strip()
        if note_body:
            AnomalyTimelineEntry.objects.create(
                anomaly=anomaly,
                entry_type=AnomalyTimelineEntry.ENTRY_NOTE,
                body=note_body,
                created_by=request.user,
            )
            messages.success(request, 'Note added.')
        return redirect(reverse('anomalies_detail', kwargs={'mission_slug': mission_slug, 'anomaly_id': anomaly.pk}))

    return redirect(reverse('anomalies_detail', kwargs={'mission_slug': mission_slug, 'anomaly_id': anomaly.pk}))


@mission_role_required('OPERATOR', 'ADMIN')
def anomaly_update(request, mission_slug, anomaly_id):
    qs = _mission_filter(Anomaly.objects.all(), request)
    anomaly = get_object_or_404(qs, pk=anomaly_id)

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
            log_update(request, anomaly, f'Status changed from {old_status} to {new_display}')
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
            log_update(request, anomaly, f'Severity changed from {old_severity} to {new_sev_display}')
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

        return redirect(reverse('anomalies_detail', kwargs={'mission_slug': mission_slug, 'anomaly_id': anomaly.pk}))

    return redirect(reverse('anomalies_detail', kwargs={'mission_slug': mission_slug, 'anomaly_id': anomaly.pk}))


@mission_role_required('OPERATOR', 'ADMIN')
def anomaly_close(request, mission_slug, anomaly_id):
    qs = _mission_filter(Anomaly.objects.all(), request)
    anomaly = get_object_or_404(qs, pk=anomaly_id)

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
        log_action(request, 'STATUS_CHANGE', 'Anomaly', anomaly.pk, str(anomaly), 'Closed')

        messages.success(request, f'Anomaly ANOM-{anomaly.pk} closed.')
        return redirect(reverse('anomalies_detail', kwargs={'mission_slug': mission_slug, 'anomaly_id': anomaly.pk}))

    context = {
        'anomaly': anomaly,
    }
    return render(request, 'anomalies/anomaly_close.html', context)


# ---------------------------------------------------------------------------
# CSV Import / Export
# ---------------------------------------------------------------------------


def anomaly_csv_export(request, mission_slug):
    """Export anomalies as CSV, respecting current list filters."""
    qs = (
        Anomaly.objects
        .select_related('satellite', 'subsystem', 'created_by')
        .order_by('-detected_time')
    )
    qs = _mission_filter(qs, request)
    satellite_id = request.GET.get('satellite')
    subsystem_id = request.GET.get('subsystem')
    severity = request.GET.get('severity')
    status = request.GET.get('status')
    q = (request.GET.get('q') or '').strip()
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
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="anomalies.csv"'
    response['X-Content-Type-Options'] = 'nosniff'
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Title', 'Satellite', 'Subsystem', 'Severity', 'Status',
        'Detected Time', 'Description', 'Root Cause', 'Resolution Actions',
        'Recommendations', 'Created At', 'Created By',
    ])
    for a in qs:
        writer.writerow([
            a.pk,
            a.title,
            a.satellite.name,
            a.subsystem.name if a.subsystem else '',
            a.severity,
            a.status,
            a.detected_time.strftime('%Y-%m-%d %H:%M') if a.detected_time else '',
            a.description,
            a.root_cause,
            a.resolution_actions,
            a.recommendations,
            a.created_at.strftime('%Y-%m-%d %H:%M') if a.created_at else '',
            a.created_by.username if a.created_by else '',
        ])
    return response


@mission_role_required('OPERATOR', 'ADMIN')
def anomaly_csv_import(request, mission_slug):
    """Import anomalies from CSV."""
    if request.method != 'POST':
        return redirect('anomalies_list', mission_slug=mission_slug)

    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        messages.error(request, 'Please select a CSV file.')
        return redirect('anomalies_list', mission_slug=mission_slug)
    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'File must be a CSV.')
        return redirect('anomalies_list', mission_slug=mission_slug)

    try:
        decoded = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))
    except Exception:
        messages.error(request, 'Could not read the CSV file. Check encoding and format.')
        return redirect('anomalies_list', mission_slug=mission_slug)

    fieldnames = [h.strip() for h in (reader.fieldnames or []) if h]
    fieldnames_lower = [h.lower() for h in fieldnames]
    has_title = any('title' in k for k in fieldnames_lower)
    has_satellite = any('satellite' in k for k in fieldnames_lower)
    has_detected = any('detected' in k for k in fieldnames_lower)
    if not (has_title and has_satellite and has_detected):
        messages.error(
            request,
            'CSV must contain: Title, Satellite, Detected Time (or similar). '
            f'Found: {", ".join(fieldnames)}',
        )
        return redirect('anomalies_list', mission_slug=mission_slug)

    def get(row, *keys):
        for k in keys:
            val = (row.get(k) or '').strip()
            if val:
                return val
        return ''

    created = 0
    skipped = 0
    satellites_qs = _mission_filter(Satellite.objects.all(), request)
    subsystems_qs = _mission_filter(Subsystem.objects.all(), request)
    satellites_by_name = {s.name: s for s in satellites_qs}
    subsystems_by_name = {s.name: s for s in subsystems_qs}

    for row in reader:
        title = get(row, 'Title', 'title')
        sat_name = get(row, 'Satellite', 'satellite')
        detected_str = get(row, 'Detected Time', 'detected_time', 'detected')
        if not title or not sat_name or not detected_str:
            skipped += 1
            continue
        satellite = satellites_by_name.get(sat_name)
        if not satellite:
            satellite = satellites_qs.filter(name=sat_name).first()
        if not satellite:
            satellite = Satellite.objects.create(name=sat_name, mission=request.mission)
            satellites_by_name[satellite.name] = satellite

        detected_time = parse_datetime(detected_str) if detected_str else timezone.now()
        if not detected_time:
            detected_time = timezone.now()

        sub_name = get(row, 'Subsystem', 'subsystem')
        subsystem = None
        if sub_name:
            subsystem = subsystems_by_name.get(sub_name) or subsystems_qs.filter(name=sub_name).first()
            if subsystem:
                subsystems_by_name[subsystem.name] = subsystem

        severity = get(row, 'Severity', 'severity') or Anomaly.SEVERITY_L2
        if severity not in dict(Anomaly.SEVERITY_CHOICES):
            severity = Anomaly.SEVERITY_L2
        status = get(row, 'Status', 'status') or Anomaly.STATUS_NEW
        if status not in dict(Anomaly.STATUS_CHOICES):
            status = Anomaly.STATUS_NEW

        Anomaly.objects.create(
            title=title,
            satellite=satellite,
            subsystem=subsystem,
            severity=severity,
            status=status,
            description=get(row, 'Description', 'description'),
            detected_time=detected_time,
            root_cause=get(row, 'Root Cause', 'root_cause'),
            resolution_actions=get(row, 'Resolution Actions', 'resolution_actions'),
            recommendations=get(row, 'Recommendations', 'recommendations'),
            created_by=request.user,
            mission=request.mission,
        )
        created += 1

    msg = f'Imported {created} anomal{"y" if created == 1 else "ies"}.'
    if skipped:
        msg += f' Skipped {skipped} row(s) with missing required fields.'
    messages.success(request, msg)
    return redirect('anomalies_list', mission_slug=mission_slug)
