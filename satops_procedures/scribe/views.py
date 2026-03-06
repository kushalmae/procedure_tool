from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from procedures.models import Satellite
from .models import Role, EventCategory, ScribeTag, Shift, MissionLogEntry, EntryTemplate


def _create_log_entry_from_post(request):
    """Create a MissionLogEntry from request.POST. Returns (True, None) on success, (False, error_msg) on validation error."""
    ts_str = (request.POST.get('timestamp') or '').strip()
    ts = parse_datetime(ts_str) if ts_str else timezone.now()
    if not ts:
        ts = timezone.now()
    role_id = request.POST.get('role')
    category_id = request.POST.get('category')
    description = (request.POST.get('description') or '').strip()
    if not role_id or not category_id or not description:
        return False, 'Role, category, and description are required.'
    role = get_object_or_404(Role, pk=role_id)
    category = get_object_or_404(EventCategory, pk=category_id)
    satellite_id = request.POST.get('satellite') or None
    satellite = get_object_or_404(Satellite, pk=satellite_id) if satellite_id else None
    severity = request.POST.get('severity') or MissionLogEntry.SEVERITY_INFO
    shift_id = request.POST.get('shift') or None
    shift = get_object_or_404(Shift, pk=shift_id) if shift_id else None
    tag_ids = request.POST.getlist('tags')
    entry = MissionLogEntry.objects.create(
        timestamp=ts,
        created_by=request.user,
        role=role,
        satellite=satellite,
        category=category,
        severity=severity,
        description=description,
        shift=shift,
    )
    for tid in tag_ids:
        try:
            entry.tags.add(ScribeTag.objects.get(pk=tid))
        except (ValueError, ScribeTag.DoesNotExist):
            pass
    return True, None


def timeline(request):
    # Handle add-entry form POST (form on timeline page)
    if request.method == 'POST' and request.user.is_authenticated and request.POST.get('description') is not None:
        ok, err = _create_log_entry_from_post(request)
        if ok:
            messages.success(request, 'Log entry added.')
        else:
            messages.error(request, err)
        return redirect('scribe_timeline')

    # Persist filters in session: if no GET params but session has saved filters, redirect with them
    if request.GET.get('clear'):
        if 'scribe_filters' in request.session:
            del request.session['scribe_filters']
        return redirect('scribe_timeline')

    saved = request.session.get('scribe_filters') or {}
    role_id = request.GET.get('role', saved.get('role', ''))
    satellite_id = request.GET.get('satellite', saved.get('satellite', ''))
    category_id = request.GET.get('category', saved.get('category', ''))
    severity = request.GET.get('severity', saved.get('severity', ''))
    shift_id = request.GET.get('shift', saved.get('shift', ''))
    tag_id = request.GET.get('tag', saved.get('tag', ''))
    q = (request.GET.get('q') or saved.get('q') or '').strip()

    # Save current filter state to session when any filter or search is set (so they persist on next visit)
    sort_param = request.GET.get('sort', saved.get('sort', '-timestamp'))
    if sort_param not in ('-timestamp', 'timestamp'):
        sort_param = '-timestamp'
    has_filters = any([role_id, satellite_id, category_id, severity, shift_id, tag_id, q])
    if has_filters or sort_param != '-timestamp':
        request.session['scribe_filters'] = {
            'role': role_id or '',
            'satellite': satellite_id or '',
            'category': category_id or '',
            'severity': severity or '',
            'shift': shift_id or '',
            'tag': tag_id or '',
            'q': q or '',
            'sort': sort_param,
        }

    entries = (
        MissionLogEntry.objects
        .select_related('role', 'satellite', 'category', 'shift', 'created_by')
        .prefetch_related('tags')
        .order_by(sort_param)
    )

    if role_id:
        try:
            entries = entries.filter(role_id=int(role_id))
        except ValueError:
            pass
    if satellite_id:
        try:
            entries = entries.filter(satellite_id=int(satellite_id))
        except ValueError:
            pass
    if category_id:
        try:
            entries = entries.filter(category_id=int(category_id))
        except ValueError:
            pass
    if severity:
        entries = entries.filter(severity=severity)
    if shift_id:
        try:
            entries = entries.filter(shift_id=int(shift_id))
        except ValueError:
            pass
    if tag_id:
        try:
            entries = entries.filter(tags__id=int(tag_id)).distinct()
        except ValueError:
            pass
    if q:
        entries = entries.filter(description__icontains=q)

    entries = entries[:200]

    def _int_or_none(val):
        try:
            return int(val) if val else None
        except (ValueError, TypeError):
            return None

    context = {
        'entries': entries,
        'roles': Role.objects.all(),
        'satellites': Satellite.objects.all(),
        'categories': EventCategory.objects.all(),
        'shifts': Shift.objects.all()[:50],
        'scribe_tags': ScribeTag.objects.all(),
        'entry_templates': EntryTemplate.objects.all(),
        'filter_role_id': _int_or_none(role_id),
        'filter_satellite_id': _int_or_none(satellite_id),
        'filter_category_id': _int_or_none(category_id),
        'filter_severity': severity or None,
        'filter_shift_id': _int_or_none(shift_id),
        'filter_tag_id': _int_or_none(tag_id),
        'search_query': q,
        'sort': sort_param,
        'severity_choices': MissionLogEntry.SEVERITY_CHOICES,
    }
    # Form defaults for add-entry form (left column) when user is authenticated
    if request.user.is_authenticated:
        now = timezone.now()
        context['timestamp_default'] = now.strftime('%Y-%m-%dT%H:%M')
        context['default_description'] = ''
        template_id = request.GET.get('template')
        selected_template = None
        if template_id:
            try:
                selected_template = EntryTemplate.objects.get(pk=int(template_id))
            except (ValueError, EntryTemplate.DoesNotExist):
                pass
        if selected_template:
            context['default_role_id'] = selected_template.role_id
            context['default_satellite_id'] = None
            context['default_category_id'] = selected_template.category_id
            context['default_shift_id'] = None
            context['default_severity'] = selected_template.default_severity
            context['default_description'] = selected_template.default_description or ''
            context['selected_template'] = selected_template
        else:
            last = (
                MissionLogEntry.objects.filter(created_by=request.user)
                .order_by('-timestamp')
                .first()
            )
            context['default_role_id'] = last.role_id if last else None
            context['default_satellite_id'] = last.satellite_id if last else None
            context['default_category_id'] = last.category_id if last else None
            context['default_shift_id'] = last.shift_id if last else None
            context['default_severity'] = last.severity if last else MissionLogEntry.SEVERITY_INFO
            context['selected_template'] = None
    return render(request, 'scribe/timeline.html', context)


@login_required
def add_entry(request):
    if request.method == 'POST':
        ts_str = (request.POST.get('timestamp') or '').strip()
        ts = parse_datetime(ts_str) if ts_str else timezone.now()
        if not ts:
            ts = timezone.now()
        role_id = request.POST.get('role')
        category_id = request.POST.get('category')
        description = (request.POST.get('description') or '').strip()
        if not role_id or not category_id or not description:
            messages.error(request, 'Role, category, and description are required.')
        else:
            role = get_object_or_404(Role, pk=role_id)
            category = get_object_or_404(EventCategory, pk=category_id)
            satellite_id = request.POST.get('satellite') or None
            if satellite_id:
                satellite = get_object_or_404(Satellite, pk=satellite_id)
            else:
                satellite = None
            severity = request.POST.get('severity') or MissionLogEntry.SEVERITY_INFO
            shift_id = request.POST.get('shift') or None
            shift = get_object_or_404(Shift, pk=shift_id) if shift_id else None
            tag_ids = request.POST.getlist('tags')

            entry = MissionLogEntry.objects.create(
                timestamp=ts,
                created_by=request.user,
                role=role,
                satellite=satellite,
                category=category,
                severity=severity,
                description=description,
                shift=shift,
            )
            for tid in tag_ids:
                try:
                    entry.tags.add(ScribeTag.objects.get(pk=tid))
                except (ValueError, ScribeTag.DoesNotExist):
                    pass
            messages.success(request, 'Log entry added.')
            if request.POST.get('add_another'):
                return redirect(reverse('scribe_add_entry'))
            return redirect('scribe_timeline')

    # GET: default timestamp to now; auto-populate from template=id or from last entry by this user
    now = timezone.now()
    ts_default = now.strftime('%Y-%m-%dT%H:%M')
    default_description = ''
    template_id = request.GET.get('template')
    template = None
    if template_id:
        try:
            template = EntryTemplate.objects.get(pk=int(template_id))
        except (ValueError, EntryTemplate.DoesNotExist):
            pass
    if template:
        default_role_id = template.role_id
        default_category_id = template.category_id
        default_severity = template.default_severity
        default_description = template.default_description or ''
        default_satellite_id = None
        default_shift_id = None
    else:
        last = (
            MissionLogEntry.objects.filter(created_by=request.user)
            .order_by('-timestamp')
            .first()
        )
        default_role_id = last.role_id if last else None
        default_satellite_id = last.satellite_id if last else None
        default_category_id = last.category_id if last else None
        default_shift_id = last.shift_id if last else None
        default_severity = last.severity if last else MissionLogEntry.SEVERITY_INFO

    context = {
        'roles': Role.objects.all(),
        'satellites': Satellite.objects.all(),
        'categories': EventCategory.objects.all(),
        'shifts': Shift.objects.all(),
        'scribe_tags': ScribeTag.objects.all(),
        'entry_templates': EntryTemplate.objects.all(),
        'timestamp_default': ts_default,
        'severity_choices': MissionLogEntry.SEVERITY_CHOICES,
        'default_role_id': default_role_id,
        'default_satellite_id': default_satellite_id,
        'default_category_id': default_category_id,
        'default_shift_id': default_shift_id,
        'default_severity': default_severity,
        'default_description': default_description,
        'selected_template': template,
    }
    return render(request, 'scribe/entry_form.html', context)


def shift_list(request):
    shifts = Shift.objects.all()[:100]
    return render(request, 'scribe/shift_list.html', {'shifts': shifts})


def shift_create(request):
    if request.method == 'POST':
        start_str = (request.POST.get('start_time') or '').strip()
        end_str = (request.POST.get('end_time') or '').strip()
        handoff_notes = (request.POST.get('handoff_notes') or '').strip()
        start_time = parse_datetime(start_str) if start_str else None
        end_time = parse_datetime(end_str) if end_str else None
        if not start_time or not end_time:
            messages.error(request, 'Start time and end time are required.')
            return render(request, 'scribe/shift_form.html', {
                'start_time_default': start_str or timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'end_time_default': end_str or timezone.now().strftime('%Y-%m-%dT%H:%M'),
                'handoff_notes': handoff_notes,
            })
        shift = Shift.objects.create(
            start_time=start_time,
            end_time=end_time,
            handoff_notes=handoff_notes,
        )
        messages.success(request, 'Shift created.')
        return redirect(reverse('scribe_shift_detail', kwargs={'shift_id': shift.pk}))
    now = timezone.now()
    context = {
        'start_time_default': now.strftime('%Y-%m-%dT%H:%M'),
        'end_time_default': now.strftime('%Y-%m-%dT%H:%M'),
        'handoff_notes': '',
    }
    return render(request, 'scribe/shift_form.html', context)


def shift_detail(request, shift_id):
    shift = get_object_or_404(Shift, pk=shift_id)
    if request.method == 'POST' and 'handoff_notes' in request.POST:
        shift.handoff_notes = (request.POST.get('handoff_notes') or '').strip()
        shift.save()
        messages.success(request, 'Handoff notes updated.')
        return redirect(reverse('scribe_shift_detail', kwargs={'shift_id': shift.pk}))
    entries = shift.entries.select_related('role', 'satellite', 'category', 'created_by').prefetch_related('tags').order_by('timestamp')
    return render(request, 'scribe/shift_detail.html', {'shift': shift, 'entries': entries})
