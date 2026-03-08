from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from .models import AuditEntry

User = get_user_model()


def audit_log(request, mission_slug):
    qs = AuditEntry.objects.select_related('user')
    if request.mission:
        qs = qs.filter(mission=request.mission)

    user_id = request.GET.get('user', '')
    action = request.GET.get('action', '')
    model = request.GET.get('model', '')
    q = request.GET.get('q', '').strip()
    date_from = request.GET.get('from', '').strip()
    date_to = request.GET.get('to', '').strip()
    sort = request.GET.get('sort', '-timestamp')
    if sort not in ('timestamp', '-timestamp'):
        sort = '-timestamp'

    if user_id:
        try:
            qs = qs.filter(user_id=int(user_id))
        except (ValueError, TypeError):
            pass
    if action:
        qs = qs.filter(action=action)
    if model:
        qs = qs.filter(model_name=model)
    if q:
        qs = qs.filter(Q(object_repr__icontains=q) | Q(detail__icontains=q))
    if date_from:
        try:
            from datetime import date as date_type
            qs = qs.filter(timestamp__date__gte=date_type.fromisoformat(date_from[:10]))
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            from datetime import date as date_type
            qs = qs.filter(timestamp__date__lte=date_type.fromisoformat(date_to[:10]))
        except (ValueError, TypeError):
            pass

    qs = qs.order_by(sort)
    total_count = qs.count()

    paginator = Paginator(qs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    mission_users = User.objects.filter(
        audit_entries__mission=request.mission,
    ).distinct().order_by('username') if request.mission else User.objects.none()

    model_names = (
        AuditEntry.objects
        .filter(mission=request.mission)
        .values_list('model_name', flat=True)
        .distinct()
        .order_by('model_name')
    ) if request.mission else []

    return render(request, 'auditlog/audit_log.html', {
        'page_obj': page_obj,
        'total_count': total_count,
        'action_choices': AuditEntry.ACTION_CHOICES,
        'users': mission_users,
        'model_names': model_names,
        'filter_user': user_id,
        'filter_action': action,
        'filter_model': model,
        'search_query': q,
        'filter_from': date_from,
        'filter_to': date_to,
        'sort': sort,
    })
