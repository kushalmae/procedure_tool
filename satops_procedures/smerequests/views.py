from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_datetime

from procedures.models import Satellite, Subsystem
from scribe.models import MissionLogEntry

from .models import RequestNote, RequestType, SMERequest


def _int_or_none(val):
    try:
        return int(val) if val else None
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Request queue / list
# ---------------------------------------------------------------------------

def request_list(request):
    if request.GET.get('clear'):
        if 'sme_filters' in request.session:
            del request.session['sme_filters']
        return redirect('sme_request_list')

    SORT_OPTIONS = [
        '-created_at', 'created_at', 'priority', '-priority', 'status', '-status',
    ]
    saved = request.session.get('sme_filters') or {}

    satellite_id = request.GET.get('satellite', saved.get('satellite', ''))
    request_type_id = request.GET.get('request_type', saved.get('request_type', ''))
    status = request.GET.get('status', saved.get('status', ''))
    priority = request.GET.get('priority', saved.get('priority', ''))
    q = (request.GET.get('q') or saved.get('q') or '').strip()
    sort = request.GET.get('sort', saved.get('sort', '-created_at'))
    if sort not in SORT_OPTIONS:
        sort = '-created_at'

    has_filters = any([satellite_id, request_type_id, status, priority, q])
    if has_filters or sort != '-created_at':
        request.session['sme_filters'] = {
            'satellite': satellite_id or '',
            'request_type': request_type_id or '',
            'status': status or '',
            'priority': priority or '',
            'q': q or '',
            'sort': sort,
        }

    qs = (
        SMERequest.objects
        .select_related('satellite', 'subsystem', 'request_type', 'requested_by', 'assigned_to')
        .order_by(sort)
    )

    if satellite_id:
        try:
            qs = qs.filter(satellite_id=int(satellite_id))
        except ValueError:
            pass
    if request_type_id:
        try:
            qs = qs.filter(request_type_id=int(request_type_id))
        except ValueError:
            pass
    if status:
        qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)
    if q:
        qs = qs.filter(title__icontains=q)

    qs = qs[:200]

    context = {
        'requests': qs,
        'satellites': Satellite.objects.all(),
        'request_types': RequestType.objects.all(),
        'filter_satellite_id': _int_or_none(satellite_id),
        'filter_request_type_id': _int_or_none(request_type_id),
        'filter_status': status or None,
        'filter_priority': priority or None,
        'search_query': q,
        'sort': sort,
        'status_choices': SMERequest.STATUS_CHOICES,
        'priority_choices': SMERequest.PRIORITY_CHOICES,
    }
    return render(request, 'smerequests/request_list.html', context)


# ---------------------------------------------------------------------------
# Operations queue (approved / queued / in-progress only)
# ---------------------------------------------------------------------------

def ops_queue(request):
    active_statuses = [
        SMERequest.STATUS_APPROVED,
        SMERequest.STATUS_QUEUED,
        SMERequest.STATUS_IN_PROGRESS,
    ]
    qs = (
        SMERequest.objects
        .filter(status__in=active_statuses)
        .select_related('satellite', 'subsystem', 'request_type', 'requested_by', 'assigned_to')
        .order_by('priority', 'created_at')
    )
    context = {
        'requests': qs[:200],
        'priority_choices': SMERequest.PRIORITY_CHOICES,
    }
    return render(request, 'smerequests/ops_queue.html', context)


# ---------------------------------------------------------------------------
# Create request
# ---------------------------------------------------------------------------

@login_required
def create_request(request):
    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()
        description = (request.POST.get('description') or '').strip()
        if not title or not description:
            messages.error(request, 'Title and description are required.')
            return render(request, 'smerequests/request_form.html', _create_context(request))

        satellite_id = request.POST.get('satellite') or None
        satellite = get_object_or_404(Satellite, pk=satellite_id) if satellite_id else None
        subsystem_id = request.POST.get('subsystem') or None
        subsystem = get_object_or_404(Subsystem, pk=subsystem_id) if subsystem_id else None
        request_type_id = request.POST.get('request_type') or None
        request_type = get_object_or_404(RequestType, pk=request_type_id) if request_type_id else None
        priority = request.POST.get('priority') or SMERequest.PRIORITY_NORMAL
        tr_start_str = (request.POST.get('time_range_start') or '').strip()
        tr_end_str = (request.POST.get('time_range_end') or '').strip()
        time_range_start = parse_datetime(tr_start_str) if tr_start_str else None
        time_range_end = parse_datetime(tr_end_str) if tr_end_str else None
        linked_event_id = request.POST.get('linked_event') or None
        linked_event = get_object_or_404(MissionLogEntry, pk=linked_event_id) if linked_event_id else None

        sme_req = SMERequest.objects.create(
            title=title,
            satellite=satellite,
            subsystem=subsystem,
            request_type=request_type,
            priority=priority,
            status=SMERequest.STATUS_SUBMITTED,
            description=description,
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            requested_by=request.user,
            linked_event=linked_event,
        )
        messages.success(request, f'Request #{sme_req.pk} created.')
        return redirect(reverse('sme_request_detail', kwargs={'request_id': sme_req.pk}))

    return render(request, 'smerequests/request_form.html', _create_context(request))


def _create_context(request):
    recent_events = (
        MissionLogEntry.objects
        .select_related('role', 'satellite', 'category')
        .order_by('-timestamp')[:30]
    )
    return {
        'satellites': Satellite.objects.all(),
        'subsystems': Subsystem.objects.all(),
        'request_types': RequestType.objects.all(),
        'priority_choices': SMERequest.PRIORITY_CHOICES,
        'recent_events': recent_events,
    }


# ---------------------------------------------------------------------------
# Request detail (view, update status, add notes, claim, approve/reject)
# ---------------------------------------------------------------------------

def request_detail(request, request_id):
    sme_req = get_object_or_404(
        SMERequest.objects.select_related(
            'satellite', 'subsystem', 'request_type',
            'requested_by', 'assigned_to', 'approved_by', 'linked_event',
        ),
        pk=request_id,
    )
    notes = sme_req.notes.select_related('created_by').order_by('-created_at')
    operators = User.objects.filter(is_active=True).order_by('username')

    if request.method == 'POST' and request.user.is_authenticated:
        action = request.POST.get('action', '')

        if action == 'add_note':
            body = (request.POST.get('note_body') or '').strip()
            if body:
                RequestNote.objects.create(request=sme_req, body=body, created_by=request.user)
                messages.success(request, 'Note added.')

        elif action == 'update_status':
            new_status = request.POST.get('status')
            if new_status and new_status in dict(SMERequest.STATUS_CHOICES):
                sme_req.status = new_status
                sme_req.save(update_fields=['status', 'updated_at'])
                messages.success(request, f'Status updated to {sme_req.get_status_display()}.')

        elif action == 'approve':
            sme_req.status = SMERequest.STATUS_APPROVED
            sme_req.approved_by = request.user
            sme_req.save(update_fields=['status', 'approved_by', 'updated_at'])
            messages.success(request, 'Request approved.')

        elif action == 'reject':
            reason = (request.POST.get('rejection_reason') or '').strip()
            sme_req.status = SMERequest.STATUS_REJECTED
            sme_req.approved_by = request.user
            if reason:
                sme_req.rejection_reason = reason
            sme_req.save(update_fields=['status', 'approved_by', 'rejection_reason', 'updated_at'])
            messages.success(request, 'Request rejected.')

        elif action == 'needs_clarification':
            reason = (request.POST.get('rejection_reason') or '').strip()
            sme_req.status = SMERequest.STATUS_NEEDS_CLARIFICATION
            if reason:
                sme_req.rejection_reason = reason
            sme_req.save(update_fields=['status', 'rejection_reason', 'updated_at'])
            messages.success(request, 'Clarification requested.')

        elif action == 'claim':
            sme_req.assigned_to = request.user
            if sme_req.status == SMERequest.STATUS_QUEUED:
                sme_req.status = SMERequest.STATUS_IN_PROGRESS
            sme_req.save(update_fields=['assigned_to', 'status', 'updated_at'])
            messages.success(request, 'Request claimed.')

        elif action == 'assign':
            assignee_id = request.POST.get('assigned_to') or None
            if assignee_id:
                assignee = get_object_or_404(User, pk=assignee_id, is_active=True)
                sme_req.assigned_to = assignee
                sme_req.save(update_fields=['assigned_to', 'updated_at'])
                messages.success(request, f'Assigned to {assignee.get_username()}.')

        elif action == 'complete':
            result_notes = (request.POST.get('result_notes') or '').strip()
            sme_req.status = SMERequest.STATUS_COMPLETED
            if result_notes:
                sme_req.result_notes = result_notes
            sme_req.save(update_fields=['status', 'result_notes', 'updated_at'])
            messages.success(request, 'Request marked complete.')

        elif action == 'close':
            sme_req.status = SMERequest.STATUS_CLOSED
            sme_req.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Request closed.')

        elif action == 'queue':
            sme_req.status = SMERequest.STATUS_QUEUED
            sme_req.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Request moved to queue.')

        elif action == 'send_for_approval':
            sme_req.status = SMERequest.STATUS_PENDING_APPROVAL
            sme_req.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Request sent for approval.')

        return redirect(reverse('sme_request_detail', kwargs={'request_id': sme_req.pk}))

    context = {
        'sme_req': sme_req,
        'notes': notes,
        'operators': operators,
        'status_choices': SMERequest.STATUS_CHOICES,
        'priority_choices': SMERequest.PRIORITY_CHOICES,
    }
    return render(request, 'smerequests/request_detail.html', context)
