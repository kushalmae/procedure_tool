from .models import AuditEntry


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_action(request, action, model_name, object_id='', object_repr='', detail=''):
    """Create an audit log entry from a request context."""
    AuditEntry.objects.create(
        mission=getattr(request, 'mission', None),
        user=request.user if request.user.is_authenticated else None,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id else '',
        object_repr=str(object_repr)[:200],
        detail=str(detail)[:2000] if detail else '',
        ip_address=_get_client_ip(request),
    )


def log_create(request, obj, detail=''):
    log_action(
        request,
        AuditEntry.ACTION_CREATE,
        obj.__class__.__name__,
        object_id=obj.pk,
        object_repr=str(obj),
        detail=detail,
    )


def log_update(request, obj, detail=''):
    log_action(
        request,
        AuditEntry.ACTION_UPDATE,
        obj.__class__.__name__,
        object_id=obj.pk,
        object_repr=str(obj),
        detail=detail,
    )


def log_delete(request, obj, detail=''):
    log_action(
        request,
        AuditEntry.ACTION_DELETE,
        obj.__class__.__name__,
        object_id=obj.pk,
        object_repr=str(obj),
        detail=detail,
    )
