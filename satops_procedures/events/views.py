from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from procedures.models import Satellite

from .models import Event, EventTimelineEntry


def _int_or_none(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


def event_list(request):
    if request.GET.get('clear'):
        if 'event_filters' in request.session:
            del request.session['event_filters']
        return redirect('events_list')

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
    saved = request.session.get('event_filters') or {}
    satellite_id = request.GET.get('satellite', saved.get('satellite', ''))
    subsystem = request.GET.get('subsystem', saved.get('subsystem', ''))
    severity = request.GET.get('severity', saved.get('severity', ''))
    status = request.GET.get('status', saved.get('status', ''))
    q = (request.GET.get('q') or saved.get('q') or '').strip()
    sort = request.GET.get('sort', saved.get('sort', '-detected_time'))
    if sort not in SORT_OPTIONS:
        sort = '-detected_time'

    has_filters = any([satellite_id, subsystem, severity, status, q])
    if has_filters or sort != '-detected_time':
        request.session['event_filters'] = {
            'satellite': satellite_id or '',
            'subsystem': subsystem or '',
            'severity': severity or '',
            'status': status or '',
            'q': q or '',
            'sort': sort,
        }

    qs = (
        Event.objects
        .select_related('satellite', 'created_by')
        .order_by(sort)
    )

    if satellite_id:
        try:
            qs = qs.filter(satellite_id=int(satellite_id))
        except ValueError:
            pass
    if subsystem:
        qs = qs.filter(subsystem=subsystem)
    if severity:
        qs = qs.filter(severity=severity)
    if status:
        qs = qs.filter(status=status)
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))

    events = qs[:200]

    context = {
        'events': events,
        'satellites': Satellite.objects.all(),
        'filter_satellite_id': _int_or_none(satellite_id),
        'filter_subsystem': subsystem or None,
        'filter_severity': severity or None,
        'filter_status': status or None,
        'search_query': q,
        'sort': sort,
        'severity_choices': Event.SEVERITY_CHOICES,
        'status_choices': Event.STATUS_CHOICES,
        'subsystem_choices': Event.SUBSYSTEM_CHOICES,
    }
    return render(request, 'events/event_list.html', context)


@login_required
def event_create(request):
    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()
        satellite_id = request.POST.get('satellite')

        if not title or not satellite_id:
            messages.error(request, 'Title and satellite are required.')
            ctx = _create_context(request)
            ctx.update({
                'form_title': title,
                'form_satellite_id': _int_or_none(satellite_id),
                'form_subsystem': request.POST.get('subsystem', Event.SUBSYSTEM_OTHER),
                'form_severity': request.POST.get('severity', Event.SEVERITY_L2),
                'form_detected_time': request.POST.get('detected_time', ''),
                'form_description': request.POST.get('description', ''),
            })
            return render(request, 'events/event_form.html', ctx)

        satellite = get_object_or_404(Satellite, pk=satellite_id)
        subsystem = request.POST.get('subsystem') or Event.SUBSYSTEM_OTHER
        severity = request.POST.get('severity') or Event.SEVERITY_L2
        ts_str = (request.POST.get('detected_time') or '').strip()
        detected_time = parse_datetime(ts_str) if ts_str else timezone.now()
        if not detected_time:
            detected_time = timezone.now()
        description = (request.POST.get('description') or '').strip()

        event = Event.objects.create(
            title=title,
            satellite=satellite,
            subsystem=subsystem,
            severity=severity,
            status=Event.STATUS_NEW,
            description=description,
            detected_time=detected_time,
            created_by=request.user,
        )

        EventTimelineEntry.objects.create(
            event=event,
            entry_type=EventTimelineEntry.ENTRY_NOTE,
            body=f'Event created with severity {event.get_severity_display()} — {event.get_subsystem_display()}',
            created_by=request.user,
        )

        messages.success(request, f'Event EVT-{event.pk} created.')
        return redirect(reverse('events_detail', kwargs={'event_id': event.pk}))

    return render(request, 'events/event_form.html', _create_context(request))


def _create_context(request):
    now = timezone.now()
    return {
        'satellites': Satellite.objects.all(),
        'severity_choices': Event.SEVERITY_CHOICES,
        'subsystem_choices': Event.SUBSYSTEM_CHOICES,
        'form_title': '',
        'form_satellite_id': None,
        'form_subsystem': Event.SUBSYSTEM_OTHER,
        'form_severity': Event.SEVERITY_L2,
        'form_detected_time': now.strftime('%Y-%m-%dT%H:%M'),
        'form_description': '',
    }


def event_detail(request, event_id):
    event = get_object_or_404(
        Event.objects.select_related('satellite', 'created_by'),
        pk=event_id,
    )
    timeline = event.timeline_entries.select_related('created_by').order_by('created_at')

    context = {
        'event': event,
        'timeline': timeline,
        'status_choices': Event.STATUS_CHOICES,
        'severity_choices': Event.SEVERITY_CHOICES,
    }
    return render(request, 'events/event_detail.html', context)


@login_required
def event_update(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        new_severity = request.POST.get('severity')
        note_body = (request.POST.get('note_body') or '').strip()
        action_body = (request.POST.get('action_body') or '').strip()

        if new_status and new_status in dict(Event.STATUS_CHOICES) and new_status != event.status:
            old_status = event.get_status_display()
            event.status = new_status
            event.save(update_fields=['status', 'updated_at'])
            new_display = event.get_status_display()
            EventTimelineEntry.objects.create(
                event=event,
                entry_type=EventTimelineEntry.ENTRY_STATUS_CHANGE,
                body=f'Status changed from {old_status} to {new_display}',
                old_value=old_status,
                new_value=new_display,
                created_by=request.user,
            )
            messages.success(request, f'Status updated to {new_display}.')

        if new_severity and new_severity in dict(Event.SEVERITY_CHOICES) and new_severity != event.severity:
            old_severity = event.get_severity_display()
            event.severity = new_severity
            event.save(update_fields=['severity', 'updated_at'])
            new_sev_display = event.get_severity_display()
            EventTimelineEntry.objects.create(
                event=event,
                entry_type=EventTimelineEntry.ENTRY_SEVERITY_CHANGE,
                body=f'Severity changed from {old_severity} to {new_sev_display}',
                old_value=old_severity,
                new_value=new_sev_display,
                created_by=request.user,
            )
            messages.success(request, f'Severity updated to {new_sev_display}.')

        if note_body:
            EventTimelineEntry.objects.create(
                event=event,
                entry_type=EventTimelineEntry.ENTRY_NOTE,
                body=note_body,
                created_by=request.user,
            )
            messages.success(request, 'Investigation note added.')

        if action_body:
            EventTimelineEntry.objects.create(
                event=event,
                entry_type=EventTimelineEntry.ENTRY_ACTION,
                body=action_body,
                created_by=request.user,
            )
            messages.success(request, 'Action documented.')

        return redirect(reverse('events_detail', kwargs={'event_id': event.pk}))

    return redirect(reverse('events_detail', kwargs={'event_id': event.pk}))


@login_required
def event_close(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    if request.method == 'POST':
        root_cause = (request.POST.get('root_cause') or '').strip()
        resolution_actions = (request.POST.get('resolution_actions') or '').strip()
        recommendations = (request.POST.get('recommendations') or '').strip()

        event.root_cause = root_cause
        event.resolution_actions = resolution_actions
        event.recommendations = recommendations
        event.status = Event.STATUS_CLOSED
        event.save(update_fields=[
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
        summary = '\n'.join(resolution_summary_parts) or 'Event closed.'

        EventTimelineEntry.objects.create(
            event=event,
            entry_type=EventTimelineEntry.ENTRY_STATUS_CHANGE,
            body=summary,
            old_value=event.get_status_display(),
            new_value='Closed',
            created_by=request.user,
        )

        messages.success(request, f'Event EVT-{event.pk} closed.')
        return redirect(reverse('events_detail', kwargs={'event_id': event.pk}))

    context = {
        'event': event,
    }
    return render(request, 'events/event_close.html', context)
